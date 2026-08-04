"""
Entry point backend. PENTING: dijalankan dari ROOT project (folder yang berisi
`backend/` dan `frontend/`), BUKAN dari dalam folder backend/ itu sendiri —
karena semua import internal pakai path absolut `backend.xxx`.

    pip install -r backend/requirements.txt
    uvicorn backend.main:app --reload --port 8000

Swagger docs otomatis di http://localhost:8000/docs — enak buat ngetes
semua endpoint sebelum frontend selesai.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.supabase_client import get_supabase
from backend.routers import (
    ai_routes, auth_routes, backtest_routes, mt5_routes,
    risk_routes, subscription_routes, trading_routes,
)
from backend.services import news_service
from backend.services.forward_test import run_forward_test_cycle
from backend.services.live_autotrader import run_live_autotrade_cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trading-fellah")

app = FastAPI(title="Trading Fellah API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(mt5_routes.router)
app.include_router(trading_routes.router)
app.include_router(risk_routes.router)
app.include_router(backtest_routes.router)
app.include_router(ai_routes.router)
app.include_router(subscription_routes.router)


@app.get("/api/health")
async def health():
    return {"status": "online", "app": settings.APP_NAME, "env": settings.ENV}


# ---------------------------------------------------------------------- #
# Scheduler: job berkala buat news refresh + forward test cycles.
# Ini jalan DI DALAM proses backend yang sama (cukup buat skala awal).
# Kalau user sudah banyak/live, pisahin ke worker process terpisah
# (celery/rq/dramatiq) biar gak numpuk beban di proses API yang sama.
# ---------------------------------------------------------------------- #
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("interval", minutes=10)
async def scheduled_news_refresh():
    try:
        await news_service.fetch_and_score_news()
        logger.info("News refresh cycle done.")
    except Exception as e:
        logger.error(f"News refresh gagal: {e}")


@scheduler.scheduled_job("interval", minutes=5)
async def scheduled_forward_test():
    try:
        sb = get_supabase()
        configs = sb.table("forward_test_configs").select("*").eq("enabled", True).execute().data
        for cfg in configs:
            account_res = sb.table("mt5_accounts").select("*").eq("id", cfg["mt5_account_id"]).execute()
            risk_res = sb.table("risk_settings").select("*") \
                .eq("mt5_account_id", cfg["mt5_account_id"]).execute()
            if not account_res.data or not risk_res.data:
                continue
            account = account_res.data[0]
            if not account.get("metaapi_account_id"):
                continue
            result = await run_forward_test_cycle(
                cfg["mt5_account_id"], account["metaapi_account_id"], cfg["symbol"], cfg["timeframe"], risk_res.data[0]
            )
            logger.info(f"Forward test {cfg['symbol']}: {result}")
    except Exception as e:
        logger.error(f"Forward test cycle gagal: {e}")


@scheduler.scheduled_job("interval", minutes=5)
async def scheduled_live_autotrade():
    """
    LAPIS 1 (query filter): cuma ambil config yang enabled=true DAN akun yang
    risk_settings.live_autotrade_enabled=true. LAPIS 2 (di dalam
    run_live_autotrade_cycle): dicek ulang sebelum kirim order — jaga-jaga
    kalau ada race condition antara scheduler baca config vs user matiin
    switch di tengah siklus.
    """
    try:
        sb = get_supabase()
        configs = sb.table("live_autotrade_configs").select("*").eq("enabled", True).execute().data
        for cfg in configs:
            account_res = sb.table("mt5_accounts").select("*").eq("id", cfg["mt5_account_id"]).execute()
            risk_res = sb.table("risk_settings").select("*").eq("mt5_account_id", cfg["mt5_account_id"]).execute()
            if not account_res.data or not risk_res.data:
                continue
            account = account_res.data[0]
            risk_cfg = risk_res.data[0]
            if not risk_cfg.get("live_autotrade_enabled") or not account.get("metaapi_account_id"):
                continue
            result = await run_live_autotrade_cycle(
                cfg["mt5_account_id"], account["metaapi_account_id"], cfg["symbol"], cfg["timeframe"], risk_cfg,
            )
            logger.info(f"Live autotrade {cfg['symbol']} (akun {cfg['mt5_account_id']}): {result}")
    except Exception as e:
        logger.error(f"Live autotrade cycle gagal: {e}")


@scheduler.scheduled_job("interval", hours=1)
async def scheduled_subscription_expiry():
    try:
        sb = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        expired = sb.table("subscriptions").select("id").eq("status", "active").lt("current_period_end", now).execute()
        for row in expired.data or []:
            sb.table("subscriptions").update({"status": "expired"}).eq("id", row["id"]).execute()
        if expired.data:
            logger.info(f"{len(expired.data)} subscription di-expire-kan.")
    except Exception as e:
        logger.error(f"Subscription expiry check gagal: {e}")


@app.on_event("startup")
async def start_scheduler():
    if settings.ENV != "test":
        scheduler.start()
        logger.info("Scheduler jalan: news refresh tiap 10 menit, forward test tiap 5 menit.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
