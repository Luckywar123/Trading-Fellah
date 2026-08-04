"""
Forward test = jalanin logic yang PERSIS SAMA dengan live trading, pakai
harga real-time dari MT5 (lewat MetaApi), TAPI order-nya cuma dicatat ke
database (trades.is_forward_test = true, mt5_ticket = null) — gak pernah
kirim order asli ke broker. Ini "simulasi jujur" sebelum user nyalain mode
live beneran, karena datanya bukan random kayak connector lama, tapi harga
pasar sungguhan.

Dipanggil berkala (lihat main.py -> APScheduler job tiap N menit per
akun+simbol yang forward_test-nya aktif), bukan infinite loop dalam
request HTTP.
"""
from datetime import datetime, timezone

from backend.db.supabase_client import get_supabase
from backend.services import mt5_service, news_service
from backend.services.risk_manager import calculate_position_size
from backend.services.signal_engine import find_validated_signal
from backend.services.swing_detector import Candle, SwingDetector

detector = SwingDetector()


def _to_candles(raw: list[dict]) -> list[Candle]:
    return [Candle(time=c.get("time"), open=c["open"], high=c["high"],
                    low=c["low"], close=c["close"], volume=c.get("tickVolume", 0)) for c in raw]


async def run_forward_test_cycle(mt5_account_id: str, metaapi_account_id: str,
                                  symbol: str, timeframe: str, risk_cfg: dict):
    """
    PENTING: `mt5_account_id` (row id di tabel Supabase kita) dan
    `metaapi_account_id` (id akun di sisi MetaApi) itu DUA HAL BEDA — yang
    pertama buat baca/tulis database kita, yang kedua buat manggil API
    MetaApi. Versi awal fungsi ini sempat ketuker (cuma nerima satu id dan
    dipakai buat dua-duanya), ketauan pas ditelusuri ulang bareng
    live_autotrader.py yang emang dari awal nerima dua parameter terpisah.
    """
    blackout, headline = news_service.is_news_blackout_active(risk_cfg.get("news_blackout_minutes", 15))
    if blackout and risk_cfg.get("news_blackout_enabled", True):
        return {"skipped": True, "reason": f"News blackout aktif: {headline}"}

    raw_candles = await mt5_service.get_historical_candles(metaapi_account_id, symbol, timeframe, None, limit=200)
    candles = _to_candles(raw_candles)
    if len(candles) < 60:
        return {"skipped": True, "reason": "data candle belum cukup"}

    account_info = await mt5_service.get_account_info(metaapi_account_id)
    sb = get_supabase()

    # cek posisi forward-test yang masih terbuka buat simbol ini
    open_rows = sb.table("trades").select("*") \
        .eq("mt5_account_id", mt5_account_id).eq("symbol", symbol) \
        .eq("is_forward_test", True).is_("closed_at", "null").execute()

    last = candles[-1]
    if open_rows.data:
        return await _manage_open_forward_trade(metaapi_account_id, open_rows.data[0], last, risk_cfg)

    signal = find_validated_signal(detector, candles, risk_cfg)
    if not signal:
        return {"skipped": True, "reason": "belum ada breakout tervalidasi"}

    entry_price = last.close
    atr = signal["atr"]
    sl = entry_price - atr * risk_cfg["sl_atr_multiplier"] if signal["direction"] == "LONG" \
        else entry_price + atr * risk_cfg["sl_atr_multiplier"]

    spec = await mt5_service.get_symbol_spec(metaapi_account_id, symbol)
    sizing = calculate_position_size(
        equity=account_info["equity"], free_margin=account_info["free_margin"],
        entry_price=entry_price, stop_loss=sl, leverage=account_info.get("leverage", 100),
        contract_size=spec["contract_size"], pip_value_per_lot=spec["pip_value_per_lot"],
        pip_size=spec["pip_size"], risk_cfg=risk_cfg,
    )

    row = {
        "mt5_account_id": mt5_account_id, "mt5_ticket": None, "symbol": symbol,
        "direction": signal["direction"], "volume_lots": sizing.volume_lots,
        "entry_price": entry_price, "stop_loss": sl,
        "source": f"forward_test_{signal['type']}", "confidence_score": signal["confidence"],
        "reason_open": f"{signal['type']} breakout tervalidasi @ {entry_price}",
        "is_forward_test": True, "opened_at": datetime.now(timezone.utc).isoformat(),
    }
    sb.table("trades").insert(row).execute()
    return {"opened": True, "trade": row}


async def _manage_open_forward_trade(metaapi_account_id: str, trade: dict, last: Candle, risk_cfg: dict):
    sb = get_supabase()
    hit_sl = (last.low <= trade["stop_loss"]) if trade["direction"] == "LONG" else (last.high >= trade["stop_loss"])
    if hit_sl:
        exit_price = trade["stop_loss"]
        pnl = await _pnl(metaapi_account_id, trade, exit_price)
        sb.table("trades").update({
            "exit_price": exit_price, "pnl_usd": pnl, "reason_close": "SL_HIT",
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", trade["id"]).execute()
        return {"closed": True, "pnl": pnl}

    spec = await mt5_service.get_symbol_spec(metaapi_account_id, trade["symbol"])
    pip = spec["pip_size"]
    profit_pips = (last.close - trade["entry_price"]) / pip if trade["direction"] == "LONG" \
        else (trade["entry_price"] - last.close) / pip
    if profit_pips >= risk_cfg["trailing_trigger_pips"]:
        trail = risk_cfg["trail_distance_pips"] * pip
        new_sl = last.close - trail if trade["direction"] == "LONG" else last.close + trail
        if (trade["direction"] == "LONG" and new_sl > trade["stop_loss"]) or \
           (trade["direction"] == "SHORT" and new_sl < trade["stop_loss"]):
            sb.table("trades").update({"stop_loss": new_sl}).eq("id", trade["id"]).execute()
            return {"trailing_updated": True, "new_sl": new_sl}

    return {"holding": True, "profit_pips": round(profit_pips, 1)}


async def _pnl(metaapi_account_id: str, trade: dict, exit_price: float) -> float:
    spec = await mt5_service.get_symbol_spec(metaapi_account_id, trade["symbol"])
    diff = (exit_price - trade["entry_price"]) if trade["direction"] == "LONG" \
        else (trade["entry_price"] - exit_price)
    pips = diff / spec["pip_size"]
    return round(pips * spec["pip_value_per_lot"] * trade["volume_lots"], 2)
