"""
AI Agent — otak "bahasa" di sistem ini (beda dari swing_detector.py yang
otak "angka"). Provider LLM-nya PLUGGABLE: ganti AI_PROVIDER di .env buat
pindah antara Anthropic Claude / OpenAI, tanpa ubah kode di router manapun.

Tiga tugas utama:
  1. analyze_news_sentiment  -> baca 1 berita, klasifikasi buy/sell/neutral
     + seberapa besar impact-nya (dipakai buat news blackout filter & sinyal).
  2. generate_trade_rationale -> narasi "kenapa" AI mau entry di suatu level
     (swing/order block/S&R), gabungin technical + news + knowledge base.
  3. analyze_trading_behavior -> baca histori trade user, cari pola kebiasaan
     (overtrading, revenge trading, jam paling profitable, dst) — buat halaman
     AI Insights / trading journal psikologis.

Semua fungsi minta output JSON terstruktur dari LLM biar gampang dipakai
program (bukan free text yang harus di-parse manual).
"""
import json
import re
from typing import Optional

from backend.config import settings
from backend.db.supabase_client import get_supabase


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


class AIAgent:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.AI_PROVIDER

    # ------------------------------------------------------------------ #
    def _complete(self, system: str, user: str, max_tokens: int = 800) -> str:
        if self.provider == "anthropic":
            return self._complete_anthropic(system, user, max_tokens)
        elif self.provider == "openai":
            return self._complete_openai(system, user, max_tokens)
        raise ValueError(f"AI_PROVIDER tidak dikenal: {self.provider}")

    def _complete_anthropic(self, system: str, user: str, max_tokens: int) -> str:
        import anthropic
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY belum di-set di .env.")
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def _complete_openai(self, system: str, user: str, max_tokens: int) -> str:
        from openai import OpenAI
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY belum di-set di .env.")
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content

    # ------------------------------------------------------------------ #
    def _knowledge_context(self, query_tags: list[str], limit: int = 4) -> str:
        """Retrieval sederhana (keyword match on tags) dari materi yang di-upload admin."""
        sb = get_supabase()
        q = sb.table("ai_knowledge_base").select("title, content, tags")
        res = q.execute()
        rows = res.data or []
        if query_tags:
            rows = [r for r in rows if set(r.get("tags") or []) & set(query_tags)] or rows
        rows = rows[:limit]
        if not rows:
            return "(belum ada materi knowledge base yang relevan)"
        return "\n\n".join(f"### {r['title']}\n{r['content'][:800]}" for r in rows)

    # ------------------------------------------------------------------ #
    def analyze_news_sentiment(self, headline: str, body: str = "", symbols: list[str] | None = None) -> dict:
        system = (
            "Kamu analis makro forex/crypto. Balas HANYA JSON valid, tanpa teks lain, "
            "format persis: {\"sentiment\": \"buy|sell|neutral\", \"sentiment_score\": <-1..1>, "
            "\"impact_level\": \"low|medium|high\", \"currency_impact\": [\"USD\",...], "
            "\"summary\": \"<1-2 kalimat kenapa>\"}"
        )
        user = f"Headline: {headline}\nIsi: {body}\nSimbol relevan: {symbols or 'auto-deteksi'}"
        raw = self._complete(system, user, max_tokens=400)
        return _extract_json(raw)

    def generate_trade_rationale(self, *, symbol: str, direction: str, signal_type: str,
                                  price: float, zone: dict, technical_summary: dict,
                                  recent_news: list[dict] | None = None) -> dict:
        system = (
            "Kamu trading analyst yang jelasin alasan entry secara ringkas dan jujur "
            "(termasuk risikonya, bukan cuma alasan pro). Balas HANYA JSON: "
            "{\"rationale\": \"<paragraf singkat>\", \"risk_note\": \"<1 kalimat risiko utama>\", "
            "\"confidence_adjustment\": <-0.2..0.2>}"
        )
        knowledge = self._knowledge_context([symbol, signal_type])
        user = (
            f"Symbol: {symbol} | Arah: {direction} | Tipe sinyal: {signal_type} | Harga: {price}\n"
            f"Zona: {zone}\nRingkasan teknikal: {technical_summary}\n"
            f"Berita terbaru relevan: {recent_news or 'tidak ada'}\n"
            f"Materi referensi:\n{knowledge}"
        )
        raw = self._complete(system, user, max_tokens=500)
        return _extract_json(raw)

    def analyze_trading_behavior(self, trades: list[dict]) -> dict:
        system = (
            "Kamu trading psychologist + quant. Analisa histori trade user, cari pola "
            "kebiasaan (overtrading, revenge trading setelah loss, jam/simbol paling "
            "profitable, disiplin ikutin SL/TP, dst). Balas HANYA JSON: "
            "{\"summary\": \"<paragraf>\", \"tendencies\": {\"overtrading_score\": 0..1, "
            "\"revenge_trading_flag\": true|false, \"best_session\": \"...\", "
            "\"best_symbol\": \"...\", \"discipline_score\": 0..1}, "
            "\"recommendations\": \"<saran actionable, 2-3 kalimat>\"}"
        )
        # kirim ringkasan aja biar hemat token kalau trade-nya ratusan
        sample = trades[-150:]
        user = f"Total trade dianalisa: {len(sample)}\nData: {json.dumps(sample, default=str)}"
        raw = self._complete(system, user, max_tokens=700)
        result = _extract_json(raw)
        result["trades_analyzed"] = len(sample)
        return result


agent = AIAgent()
