from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.siwe import get_current_user
from backend.db.supabase_client import get_supabase
from backend.models.schemas import KnowledgeItemRequest
from backend.services.ownership import get_owned_account as _get_owned_account
from backend.services import news_service
from backend.services.ai_agent import agent

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/news")
async def latest_news(limit: int = 30, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("ai_news_events").select("*").order("created_at", desc=True).limit(limit).execute()
    return res.data


@router.post("/news/refresh")
async def refresh_news(symbols: str = "EURUSD,GBPUSD,USDJPY,XAUUSD", user: dict = Depends(get_current_user)):
    """Trigger manual buat narik berita terbaru + kasih skor sentiment AI.
    Idealnya ini dijadwalin (lihat main.py scheduler) tiap beberapa menit."""
    saved = await news_service.fetch_and_score_news(symbols.split(","))
    return {"fetched": len(saved), "items": saved}


@router.get("/news/blackout-status")
async def blackout_status(minutes: int = 15):
    active, headline = news_service.is_news_blackout_active(minutes)
    return {"blackout_active": active, "headline": headline}


@router.post("/behavior/accounts/{account_id}/generate")
async def generate_behavior_profile(account_id: str, user: dict = Depends(get_current_user)):
    """
    AI baca histori trade user (bukan cuma teknikal, tapi POLA KEBIASAAN-nya:
    jam paling sering loss, overtrading, revenge trading setelah loss beruntun,
    disiplin ikutin SL, dst) dan kasih ringkasan + saran.
    """
    _get_owned_account(account_id, user)
    sb = get_supabase()
    trades = sb.table("trades").select("*").eq("mt5_account_id", account_id) \
        .not_.is_("closed_at", "null").order("opened_at", desc=True).limit(200).execute().data

    if len(trades) < 5:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                             "Butuh minimal 5 trade histori dulu buat bikin profil kebiasaan yang berarti.")

    result = agent.analyze_trading_behavior(trades)
    row = sb.table("ai_behavior_profiles").insert({
        "user_id": user["id"], "trades_analyzed": result.get("trades_analyzed", len(trades)),
        "summary": result.get("summary"), "tendencies": result.get("tendencies"),
        "recommendations": result.get("recommendations"),
    }).execute().data[0]
    return row


@router.get("/behavior/latest")
async def latest_behavior_profile(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("ai_behavior_profiles").select("*").eq("user_id", user["id"]) \
        .order("generated_at", desc=True).limit(1).execute()
    return res.data[0] if res.data else None


@router.get("/knowledge")
async def list_knowledge(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    return sb.table("ai_knowledge_base").select("id, title, tags, created_at").execute().data


@router.post("/knowledge")
async def add_knowledge(body: KnowledgeItemRequest, user: dict = Depends(get_current_user)):
    """Suapin materi financial (artikel, catatan strategi, dsb) yang dipakai
    AI sebagai konteks tambahan pas generate trade rationale."""
    sb = get_supabase()
    row = sb.table("ai_knowledge_base").insert({
        "title": body.title, "content": body.content, "tags": body.tags, "added_by": user["id"],
    }).execute().data[0]
    return row
