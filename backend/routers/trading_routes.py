from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.siwe import get_current_user, require_active_subscription
from backend.db.supabase_client import get_supabase
from backend.models.schemas import OpenOrderRequest
from backend.services.ownership import get_owned_account as _get_owned_account
from backend.services import mt5_service, news_service
from backend.services.risk_manager import calculate_position_size, can_open_trade

router = APIRouter(prefix="/api/trading", tags=["trading"])


def _get_risk_cfg(sb, account_id: str) -> dict:
    res = sb.table("risk_settings").select("*").eq("mt5_account_id", account_id).execute()
    if not res.data:
        raise HTTPException(status.HTTP_409_CONFLICT, "Risk settings belum ada buat akun ini.")
    return res.data[0]


@router.post("/accounts/{account_id}/open")
async def open_order(account_id: str, body: OpenOrderRequest,
                      user: dict = Depends(require_active_subscription)):
    account = _get_owned_account(account_id, user)
    if not account.get("metaapi_account_id"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Akun belum selesai konek ke MT5.")

    sb = get_supabase()
    risk_cfg = _get_risk_cfg(sb, account_id)

    # --- news blackout net (safety, deterministik, gak butuh AI) ---
    if risk_cfg["news_blackout_enabled"]:
        blackout, headline = news_service.is_news_blackout_active(risk_cfg["news_blackout_minutes"])
        if blackout:
            raise HTTPException(
                status.HTTP_423_LOCKED,
                f"Order diblokir — dalam window news blackout ({headline}). "
                f"Bisa dimatikan di Risk Settings kalau mau tetap trading saat news.",
            )

    # --- gate harian/posisi ---
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    daily_trades = sb.table("trades").select("id", count="exact") \
        .eq("mt5_account_id", account_id).gte("opened_at", today_start).execute().count or 0
    open_positions = await mt5_service.get_open_positions(account["metaapi_account_id"])
    account_info = await mt5_service.get_account_info(account["metaapi_account_id"])

    ok, reason = can_open_trade(
        daily_trades=daily_trades, open_positions=len(open_positions), consecutive_losses=0,
        equity=account_info["equity"], initial_equity=account_info["balance"], risk_cfg=risk_cfg,
    )
    if not ok:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, reason)

    # NOTE: harga eksekusi market order ditentukan broker saat fill (MetaApi return
    # harga fill di `result["price"]`). stop_loss/take_profit di bawah dipakai sebagai
    # acuan hitung lot & dikirim langsung ke order, kecuali user isi manual di form.
    volume = body.volume_lots
    stop_loss = body.stop_loss
    take_profit = body.take_profit

    if volume is None:
        # auto-size: butuh estimasi entry price -> pakai quote dari posisi terakhir kalau ada,
        # fallback: user WAJIB isi stop_loss manual dulu kalau mau auto-size (butuh jarak SL).
        if stop_loss is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Isi stop_loss (atau volume_lots manual) supaya sistem bisa hitung ukuran lot otomatis.",
            )
        sizing = calculate_position_size(
            equity=account_info["equity"], free_margin=account_info["free_margin"],
            entry_price=stop_loss, stop_loss=stop_loss, leverage=account_info.get("leverage", 100),
            contract_size=100_000, pip_value_per_lot=10.0, risk_cfg=risk_cfg,
        )
        volume = sizing.volume_lots

    result = await mt5_service.open_market_order(
        account["metaapi_account_id"], body.symbol, body.direction, volume,
        stop_loss, take_profit, body.comment,
    )

    sb.table("trades").insert({
        "mt5_account_id": account_id, "mt5_ticket": str(result.get("ticket")),
        "symbol": body.symbol, "direction": body.direction, "volume_lots": volume,
        "entry_price": result.get("price") or stop_loss, "stop_loss": stop_loss,
        "take_profit": take_profit, "source": "manual", "reason_open": body.comment,
        "is_forward_test": False, "opened_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {"success": True, "order": result}


@router.post("/accounts/{account_id}/close/{ticket}")
async def close_order(account_id: str, ticket: str, user: dict = Depends(get_current_user)):
    account = _get_owned_account(account_id, user)
    result = await mt5_service.close_position(account["metaapi_account_id"], ticket)

    sb = get_supabase()
    sb.table("trades").update({"closed_at": datetime.now(timezone.utc).isoformat(),
                                "reason_close": "MANUAL"}) \
        .eq("mt5_account_id", account_id).eq("mt5_ticket", ticket).execute()
    return {"success": True, "result": result}


@router.get("/accounts/{account_id}/history")
async def trade_history(account_id: str, limit: int = 100, user: dict = Depends(get_current_user)):
    _get_owned_account(account_id, user)
    sb = get_supabase()
    res = sb.table("trades").select("*").eq("mt5_account_id", account_id) \
        .order("opened_at", desc=True).limit(limit).execute()
    return res.data
