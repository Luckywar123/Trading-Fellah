"""
Dua fungsi terpisah yang sering ketuker tapi beda tujuan:

1. `is_news_blackout_active()` — SAFETY NET murni (tidak butuh AI/LLM sama
   sekali). Ini yang dimaksud user sebagai "net dimana pas news gak masang
   order". Berdasarkan kalender ekonomi (jadwal rilis high-impact seperti
   NFP, CPI, rate decision), bukan opini AI. Default ON di risk_settings.

2. `fetch_and_score_news()` — pipeline AI. Ambil berita terbaru, minta
   ai_agent.analyze_news_sentiment buat tiap berita, simpan ke tabel
   ai_news_events. Ini yang dipakai buat "AI yang berita, ngasih tau buy/sell".

Provider berita default: Finnhub (ada free tier). Ganti NEWS_PROVIDER +
NEWS_API_KEY di .env kalau mau pakai provider lain — tinggal tambah cabang
di `_fetch_raw_news()`.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from backend.config import settings
from backend.db.supabase_client import get_supabase
from backend.services.ai_agent import agent

# Jadwal rilis high-impact yang di-hardcode sebagai fallback kalau API kalender
# berita belum dikonfigurasi. Idealnya ini ditarik live dari provider kalender
# ekonomi (Finnhub /calendar/economic, ForexFactory, dst).
HIGH_IMPACT_KEYWORDS = [
    "non-farm payroll", "nfp", "cpi", "interest rate decision", "fomc",
    "gdp", "unemployment rate", "ecb press conference", "boj policy",
]


async def _fetch_raw_news(symbols: list[str] | None = None) -> list[dict]:
    if settings.NEWS_PROVIDER == "finnhub" and settings.NEWS_API_KEY:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "forex", "token": settings.NEWS_API_KEY},
            )
            resp.raise_for_status()
            return resp.json()[:20]
    return []  # belum dikonfigurasi — biarkan kosong daripada nebak-nebak


async def fetch_and_score_news(symbols: list[str] | None = None) -> list[dict]:
    raw_items = await _fetch_raw_news(symbols)
    sb = get_supabase()
    saved = []

    for item in raw_items:
        headline = item.get("headline") or item.get("title", "")
        body = item.get("summary", "")
        if not headline:
            continue
        try:
            analysis = await asyncio.to_thread(agent.analyze_news_sentiment, headline, body, symbols)
        except Exception as e:
            analysis = {"sentiment": "neutral", "sentiment_score": 0, "impact_level": "low",
                        "currency_impact": [], "summary": f"AI gagal analisa: {e}"}

        row = {
            "headline": headline,
            "source": item.get("source", "unknown"),
            "currency_impact": analysis.get("currency_impact", []),
            "impact_level": analysis.get("impact_level", "low"),
            "sentiment": analysis.get("sentiment", "neutral"),
            "sentiment_score": analysis.get("sentiment_score", 0),
            "ai_summary": analysis.get("summary", ""),
            "event_time": datetime.now(timezone.utc).isoformat(),
        }
        res = sb.table("ai_news_events").insert(row).execute()
        saved.append(res.data[0] if res.data else row)

    return saved


def is_news_blackout_active(blackout_minutes: int = 15) -> tuple[bool, str | None]:
    """
    True kalau lagi dalam window blackout (X menit sebelum/sesudah rilis
    high-impact). Ini SENGAJA gak minta AI — harus deterministik & cepat
    karena dicek tiap kali sebelum eksekusi order.
    """
    sb = get_supabase()
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(minutes=blackout_minutes)).isoformat()
    window_end = (now + timedelta(minutes=blackout_minutes)).isoformat()

    res = (
        sb.table("ai_news_events")
        .select("headline, impact_level, event_time")
        .eq("impact_level", "high")
        .gte("event_time", window_start)
        .lte("event_time", window_end)
        .execute()
    )
    if res.data:
        return True, res.data[0]["headline"]
    return False, None


def latest_sentiment_for_symbol(symbol: str, currency_codes: list[str]) -> dict | None:
    sb = get_supabase()
    res = (
        sb.table("ai_news_events")
        .select("*")
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )
    for row in res.data or []:
        if set(row.get("currency_impact") or []) & set(currency_codes):
            return row
    return None
