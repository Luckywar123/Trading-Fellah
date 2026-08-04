"""
Auto-trade LIVE — AI validasi sinyal lalu masang order ASLI ke MT5, tanpa
ada manusia yang klik. Ini yang paling sensitif di seluruh sistem, jadi
gate-nya sengaja berlapis:

  1. `risk_settings.live_autotrade_enabled` — MASTER SWITCH per akun,
     default FALSE. Harus user nyalain eksplisit dari halaman Automation.
  2. `live_autotrade_configs.enabled` — opt-in per simbol yang mau diawasi.
  3. News blackout gate (kalau nyala di risk settings).
  4. `can_open_trade()` — limit harian, limit posisi terbuka, circuit
     breaker 5-loss-beruntun, kill switch drawdown 20%.
  5. `ai_confidence_threshold` — sinyal harus lolos ambang confidence.

Kalau salah satu gagal, siklus itu di-skip (gak ada order dikirim) — bukan
error yang bikin scheduler berhenti, biar siklus berikutnya tetap jalan.

Trailing stop buat posisi yang lagi terbuka di-handle di sini juga (poll
tiap siklus scheduler, kirim `modify_position` beneran ke MT5 kalau syarat
trailing terpenuhi) — beda dari forward_test.py yang cuma update angka di
database (paper).
"""
import logging
from datetime import datetime, timezone

from backend.db.supabase_client import get_supabase
from backend.services import mt5_service, news_service, trade_stats
from backend.services.risk_manager import calculate_position_size, can_open_trade
from backend.services.signal_engine import find_validated_signal
from backend.services.swing_detector import Candle, SwingDetector

logger = logging.getLogger("trading-fellah.live_autotrade")
detector = SwingDetector()


def _to_candles(raw: list[dict]) -> list[Candle]:
    return [Candle(time=c.get("time"), open=c["open"], high=c["high"],
                    low=c["low"], close=c["close"], volume=c.get("tickVolume", 0)) for c in raw]


async def run_live_autotrade_cycle(mt5_account_id: str, metaapi_account_id: str,
                                    symbol: str, timeframe: str, risk_cfg: dict) -> dict:
    if not risk_cfg.get("live_autotrade_enabled"):
        return {"skipped": True, "reason": "master switch OFF"}

    if risk_cfg.get("news_blackout_enabled", True):
        blackout, headline = news_service.is_news_blackout_active(risk_cfg.get("news_blackout_minutes", 15))
        if blackout:
            return {"skipped": True, "reason": f"news blackout: {headline}"}

    sb = get_supabase()

    # --- kelola posisi ASLI yang lagi terbuka buat simbol ini (trailing) ---
    open_positions = await mt5_service.get_open_positions(metaapi_account_id)
    existing = next((p for p in open_positions if p["symbol"] == symbol), None)
    if existing:
        return await _manage_open_live_position(metaapi_account_id, existing, risk_cfg)

    # --- gate sebelum entry baru ---
    daily_trades = trade_stats.daily_trade_count(sb, mt5_account_id)
    losses_streak = trade_stats.consecutive_losses(sb, mt5_account_id)
    account_info = await mt5_service.get_account_info(metaapi_account_id)

    ok, reason = can_open_trade(
        daily_trades=daily_trades, open_positions=len(open_positions), consecutive_losses=losses_streak,
        equity=account_info["equity"], initial_equity=account_info["balance"], risk_cfg=risk_cfg,
    )
    if not ok:
        return {"skipped": True, "reason": reason}

    raw_candles = await mt5_service.get_historical_candles(metaapi_account_id, symbol, timeframe, None, limit=200)
    candles = _to_candles(raw_candles)
    if len(candles) < 60:
        return {"skipped": True, "reason": "data candle belum cukup"}

    signal = find_validated_signal(detector, candles, risk_cfg)
    if not signal:
        return {"skipped": True, "reason": "belum ada breakout tervalidasi"}

    last = candles[-1]
    atr = signal["atr"]
    stop_loss = last.close - atr * risk_cfg["sl_atr_multiplier"] if signal["direction"] == "LONG" \
        else last.close + atr * risk_cfg["sl_atr_multiplier"]

    spec = await mt5_service.get_symbol_spec(metaapi_account_id, symbol)
    sizing = calculate_position_size(
        equity=account_info["equity"], free_margin=account_info["free_margin"],
        entry_price=last.close, stop_loss=stop_loss, leverage=account_info.get("leverage", 100),
        contract_size=spec["contract_size"], pip_value_per_lot=spec["pip_value_per_lot"],
        pip_size=spec["pip_size"], risk_cfg=risk_cfg,
    )
    if sizing.volume_lots < spec.get("min_volume", 0.01):
        return {"skipped": True, "reason": "lot hasil hitung di bawah minimum broker"}

    comment = f"live-ai-{signal['type']}"[:26]
    result = await mt5_service.open_market_order(
        metaapi_account_id, symbol, signal["direction"], sizing.volume_lots, stop_loss, None, comment,
    )

    sb.table("trades").insert({
        "mt5_account_id": mt5_account_id, "mt5_ticket": str(result.get("ticket")),
        "symbol": symbol, "direction": signal["direction"], "volume_lots": sizing.volume_lots,
        "entry_price": result.get("price") or last.close, "stop_loss": stop_loss,
        "source": f"live_autotrade_{signal['type']}", "confidence_score": signal["confidence"],
        "reason_open": f"{signal['type']} breakout tervalidasi @ {last.close}, margin_cap={sizing.capped_by}",
        "is_forward_test": False, "opened_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    logger.warning(f"LIVE ORDER dibuka: {symbol} {signal['direction']} {sizing.volume_lots} lot @ akun {mt5_account_id}")
    return {"opened": True, "symbol": symbol, "direction": signal["direction"], "volume": sizing.volume_lots}


async def _manage_open_live_position(metaapi_account_id: str, position: dict, risk_cfg: dict) -> dict:
    if not risk_cfg.get("trailing_enabled", True):
        return {"holding": True, "trailing": "disabled"}

    spec = await mt5_service.get_symbol_spec(metaapi_account_id, position["symbol"])
    pip = spec["pip_size"]
    entry = position["open_price"]
    current = position["current_price"]
    profit_pips = (current - entry) / pip if position["direction"] == "LONG" else (entry - current) / pip

    if profit_pips < risk_cfg["trailing_trigger_pips"]:
        return {"holding": True, "profit_pips": round(profit_pips, 1)}

    trail = risk_cfg["trail_distance_pips"] * pip
    new_sl = current - trail if position["direction"] == "LONG" else current + trail
    existing_sl = position.get("stop_loss")

    should_update = existing_sl is None or (
        (position["direction"] == "LONG" and new_sl > existing_sl) or
        (position["direction"] == "SHORT" and new_sl < existing_sl)
    )
    if should_update:
        await mt5_service.modify_position(metaapi_account_id, position["ticket"], new_sl, position.get("take_profit"))
        return {"trailing_updated": True, "new_sl": new_sl}

    return {"holding": True, "profit_pips": round(profit_pips, 1)}
