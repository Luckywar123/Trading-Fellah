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
from backend.services.swing_detector import Candle, SwingDetector
from backend.services.risk_manager import calculate_position_size

detector = SwingDetector()


def _to_candles(raw: list[dict]) -> list[Candle]:
    return [Candle(time=c.get("time"), open=c["open"], high=c["high"],
                    low=c["low"], close=c["close"], volume=c.get("tickVolume", 0)) for c in raw]


async def run_forward_test_cycle(mt5_account_id: str, symbol: str, timeframe: str, risk_cfg: dict):
    blackout, headline = news_service.is_news_blackout_active(risk_cfg.get("news_blackout_minutes", 15))
    if blackout and risk_cfg.get("news_blackout_enabled", True):
        return {"skipped": True, "reason": f"News blackout aktif: {headline}"}

    raw_candles = await mt5_service.get_historical_candles(mt5_account_id, symbol, timeframe, None, limit=200)
    candles = _to_candles(raw_candles)
    if len(candles) < 60:
        return {"skipped": True, "reason": "data candle belum cukup"}

    account_info = await mt5_service.get_account_info(mt5_account_id)
    sb = get_supabase()

    # cek posisi forward-test yang masih terbuka buat simbol ini
    open_rows = sb.table("trades").select("*") \
        .eq("mt5_account_id", mt5_account_id).eq("symbol", symbol) \
        .eq("is_forward_test", True).is_("closed_at", "null").execute()

    last = candles[-1]
    if open_rows.data:
        return await _manage_open_forward_trade(open_rows.data[0], last, risk_cfg)

    analysis = detector.analyze(candles)
    atr = _atr(candles)
    if atr <= 0:
        return {"skipped": True, "reason": "ATR 0"}

    signal = _best_signal(candles, analysis, atr, risk_cfg)
    if not signal:
        return {"skipped": True, "reason": "belum ada breakout tervalidasi"}

    entry_price = last.close
    sl = entry_price - atr * risk_cfg["sl_atr_multiplier"] if signal["direction"] == "LONG" \
        else entry_price + atr * risk_cfg["sl_atr_multiplier"]

    sizing = calculate_position_size(
        equity=account_info["equity"], free_margin=account_info["free_margin"],
        entry_price=entry_price, stop_loss=sl, leverage=account_info.get("leverage", 100),
        contract_size=100_000, pip_value_per_lot=10.0, risk_cfg=risk_cfg,
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


async def _manage_open_forward_trade(trade: dict, last: Candle, risk_cfg: dict):
    sb = get_supabase()
    hit_sl = (last.low <= trade["stop_loss"]) if trade["direction"] == "LONG" else (last.high >= trade["stop_loss"])
    if hit_sl:
        exit_price = trade["stop_loss"]
        pnl = _pnl(trade, exit_price)
        sb.table("trades").update({
            "exit_price": exit_price, "pnl_usd": pnl, "reason_close": "SL_HIT",
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", trade["id"]).execute()
        return {"closed": True, "pnl": pnl}

    pip = 0.0001
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


def _best_signal(candles, analysis, atr, risk_cfg):
    candidates = []
    for ob in analysis.order_blocks:
        level = ob.zone_high if ob.direction == "LONG" else ob.zone_low
        v = detector.validate_breakout(candles, level, ob.direction, atr)
        if v["validated"] and v["confidence"] >= risk_cfg["ai_confidence_threshold"]:
            candidates.append({"direction": ob.direction, "type": "order_block", "confidence": v["confidence"]})
    for zone in analysis.zones:
        level = zone.high if zone.kind == "resistance" else zone.low
        direction = "LONG" if zone.kind == "resistance" else "SHORT"
        v = detector.validate_breakout(candles, level, direction, atr)
        if v["validated"] and v["confidence"] >= risk_cfg["ai_confidence_threshold"]:
            candidates.append({"direction": direction, "type": "support_resistance", "confidence": v["confidence"]})
    return max(candidates, key=lambda c: c["confidence"]) if candidates else None


def _atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period


def _pnl(trade: dict, exit_price: float) -> float:
    diff = (exit_price - trade["entry_price"]) if trade["direction"] == "LONG" \
        else (trade["entry_price"] - exit_price)
    pips = diff / 0.0001
    return round(pips * 10.0 * trade["volume_lots"], 2)
