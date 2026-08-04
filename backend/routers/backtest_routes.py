from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth.siwe import get_current_user
from backend.db.supabase_client import get_supabase
from backend.models.schemas import BacktestRequest
from backend.services.ownership import get_owned_account as _get_owned_account
from backend.services import mt5_service
from backend.services.backtest_engine import BacktestEngine
from backend.services.risk_manager import resolve_preset
from backend.services.swing_detector import Candle

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


async def _execute_backtest(run_id: str, account_id: str, body: BacktestRequest):
    sb = get_supabase()
    sb.table("backtest_runs").update({"status": "running"}).eq("id", run_id).execute()
    try:
        account = sb.table("mt5_accounts").select("*").eq("id", account_id).execute().data[0]
        raw = await mt5_service.get_historical_candles(
            account["metaapi_account_id"], body.symbol, body.timeframe, body.date_from, limit=5000
        )
        candles = [Candle(time=c.get("time"), open=c["open"], high=c["high"],
                           low=c["low"], close=c["close"], volume=c.get("tickVolume", 0)) for c in raw]

        risk_cfg = resolve_preset(body.risk_preset)
        spec = await mt5_service.get_symbol_spec(account["metaapi_account_id"], body.symbol)
        engine = BacktestEngine(
            risk_cfg, pip_value_per_lot=spec["pip_value_per_lot"],
            contract_size=spec["contract_size"],
        )
        result = engine.run(body.symbol, candles, body.starting_equity)

        sb.table("backtest_runs").update({
            "status": "done",
            "result_summary": {
                "win_rate": result.win_rate, "total_trades": result.total_trades,
                "net_pnl": result.net_pnl, "max_drawdown_pct": result.max_drawdown_pct,
                "profit_factor": result.profit_factor, "final_equity": result.final_equity,
            },
            "equity_curve": result.equity_curve,
        }).eq("id", run_id).execute()
    except Exception as e:
        sb.table("backtest_runs").update({"status": "failed", "result_summary": {"error": str(e)}}) \
            .eq("id", run_id).execute()


@router.post("/run")
async def run_backtest(body: BacktestRequest, background_tasks: BackgroundTasks,
                        user: dict = Depends(get_current_user)):
    _get_owned_account(body.mt5_account_id, user)
    sb = get_supabase()
    run = sb.table("backtest_runs").insert({
        "user_id": user["id"], "symbol": body.symbol, "timeframe": body.timeframe,
        "date_from": body.date_from, "date_to": body.date_to, "risk_preset": body.risk_preset,
        "params": body.model_dump(), "status": "queued",
    }).execute().data[0]

    background_tasks.add_task(_execute_backtest, run["id"], body.mt5_account_id, body)
    return {"run_id": run["id"], "status": "queued"}


@router.get("/{run_id}")
async def get_backtest(run_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("backtest_runs").select("*").eq("id", run_id).eq("user_id", user["id"]).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backtest run tidak ditemukan.")
    return res.data[0]


@router.get("")
async def list_backtests(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("backtest_runs").select("id, symbol, timeframe, status, risk_preset, created_at, result_summary") \
        .eq("user_id", user["id"]).order("created_at", desc=True).limit(50).execute()
    return res.data


class ForwardTestToggle(BaseModel):
    symbol: str
    timeframe: str = "15m"
    enabled: bool = True


@router.post("/forward-test/accounts/{account_id}/toggle")
async def toggle_forward_test(account_id: str, body: ForwardTestToggle, user: dict = Depends(get_current_user)):
    """Nyala/matiin forward test buat 1 simbol di akun ini. Job scheduler (main.py)
    yang bakal jalanin siklusnya tiap beberapa menit untuk semua config enabled=true."""
    _get_owned_account(account_id, user)
    sb = get_supabase()
    res = sb.table("forward_test_configs").upsert({
        "mt5_account_id": account_id, "symbol": body.symbol,
        "timeframe": body.timeframe, "enabled": body.enabled,
    }, on_conflict="mt5_account_id,symbol,timeframe").execute()
    return res.data[0]


@router.get("/forward-test/accounts/{account_id}/trades")
async def forward_test_trades(account_id: str, limit: int = 100, user: dict = Depends(get_current_user)):
    _get_owned_account(account_id, user)
    sb = get_supabase()
    res = sb.table("trades").select("*").eq("mt5_account_id", account_id) \
        .eq("is_forward_test", True).order("opened_at", desc=True).limit(limit).execute()
    return res.data
