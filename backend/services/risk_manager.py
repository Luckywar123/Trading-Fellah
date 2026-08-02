"""
Position sizing & risk gate. Ini yang jaga akun user gak langsung wipeout
di trade pertama, walaupun "full margin mode" dinyalain.

CATATAN PENTING (bukan nasihat finansial, cuma fakta matematika leverage):
"Full margin" secara harfiah = pakai semua free margin yang ada di satu
posisi. Di leverage tinggi itu artinya SL sedikit aja kena -> margin call.
Makanya `max_margin_pct_per_trade` selalu ada sebagai CEILING yang bisa
user atur sendiri (lihat risk_settings.full_margin_mode +
max_margin_pct_per_trade) — bukan Claude yang menentukan angka "benar",
user yang pegang kendali penuh lewat toggle di halaman Risk Settings.
"""
from dataclasses import dataclass


PRESETS = {
    "conservative": dict(
        max_margin_pct_per_trade=5.0, max_risk_pct_per_trade=0.5,
        max_open_positions=3, max_daily_trades=8,
        sl_atr_multiplier=1.5, trailing_trigger_pips=40, trail_distance_pips=15,
        full_margin_mode=False, ai_confidence_threshold=0.80,
    ),
    "balanced": dict(
        max_margin_pct_per_trade=20.0, max_risk_pct_per_trade=2.0,
        max_open_positions=5, max_daily_trades=25,
        sl_atr_multiplier=1.2, trailing_trigger_pips=50, trail_distance_pips=10,
        full_margin_mode=False, ai_confidence_threshold=0.70,
    ),
    "aggressive": dict(
        max_margin_pct_per_trade=50.0, max_risk_pct_per_trade=5.0,
        max_open_positions=6, max_daily_trades=40,
        sl_atr_multiplier=1.0, trailing_trigger_pips=50, trail_distance_pips=10,
        full_margin_mode=False, ai_confidence_threshold=0.65,
    ),
    "full_send": dict(
        max_margin_pct_per_trade=90.0, max_risk_pct_per_trade=10.0,
        max_open_positions=3, max_daily_trades=15,
        sl_atr_multiplier=0.8, trailing_trigger_pips=50, trail_distance_pips=10,
        full_margin_mode=True, ai_confidence_threshold=0.75,
    ),
}


@dataclass
class SizingResult:
    volume_lots: float
    margin_required: float
    risk_amount_usd: float
    capped_by: str | None  # None | "margin_ceiling" | "risk_pct" | "min_lot"


def resolve_preset(preset: str) -> dict:
    return dict(PRESETS.get(preset, PRESETS["balanced"]))


def calculate_position_size(
    *, equity: float, free_margin: float, entry_price: float, stop_loss: float,
    leverage: int, contract_size: float, pip_value_per_lot: float,
    risk_cfg: dict, full_margin_override: bool | None = None, pip_size: float = 0.0001,
) -> SizingResult:
    """
    Dua batasan dipakai bersamaan, lot final = MIN dari keduanya:
      1. Risk-based sizing klasik: risiko = max_risk_pct_per_trade% dari equity,
         lot dihitung dari jarak SL (dalam PIPS, bukan raw price diff — makanya
         di-bagi `pip_size` dulu; default 0.0001 buat mayoritas pair, PAKAI
         0.01 buat pair yang ada JPY-nya, contoh USDJPY, GBPJPY).
      2. Margin ceiling: margin yang dipakai gak boleh lebih dari
         max_margin_pct_per_trade% dari free margin (INI yang jadi limit utama
         kalau full_margin_mode nyala, karena SL sniper bot ini emang tight
         jadi (1) sering ngasih lot gede banget — ceiling di (2) yang nahan).
    """
    use_full_margin = full_margin_override if full_margin_override is not None else risk_cfg.get("full_margin_mode", False)
    sl_distance = abs(entry_price - stop_loss)
    if sl_distance <= 0 or entry_price <= 0:
        return SizingResult(0.0, 0.0, 0.0, "invalid_sl")

    sl_distance_pips = sl_distance / pip_size

    # (1) risk-based
    risk_amount = equity * (risk_cfg["max_risk_pct_per_trade"] / 100)
    lots_by_risk = risk_amount / (sl_distance_pips * pip_value_per_lot) if pip_value_per_lot > 0 else 0

    # (2) margin ceiling — ini yang dipakai kalau full_margin_mode true
    margin_budget = free_margin * (risk_cfg["max_margin_pct_per_trade"] / 100)
    lots_by_margin = (margin_budget * leverage) / (entry_price * contract_size) if entry_price > 0 else 0

    if use_full_margin:
        # full margin mode: pakai margin ceiling sebagai target utama,
        # TAPI tetap gak boleh lewat dari lots_by_margin (itu sendiri sudah
        # capped oleh max_margin_pct_per_trade yang user set)
        final_lots = lots_by_margin
        capped_by = "margin_ceiling"
    else:
        final_lots = min(lots_by_risk, lots_by_margin)
        capped_by = "risk_pct" if lots_by_risk <= lots_by_margin else "margin_ceiling"

    final_lots = max(0.01, round(final_lots, 2))  # broker minimum lot lazim 0.01
    margin_required = (final_lots * contract_size * entry_price) / leverage if leverage > 0 else 0
    risk_amount_usd = final_lots * sl_distance_pips * pip_value_per_lot

    return SizingResult(
        volume_lots=final_lots,
        margin_required=round(margin_required, 2),
        risk_amount_usd=round(risk_amount_usd, 2),
        capped_by=capped_by,
    )


def can_open_trade(*, daily_trades: int, open_positions: int, consecutive_losses: int,
                    equity: float, initial_equity: float, risk_cfg: dict) -> tuple[bool, str]:
    if daily_trades >= risk_cfg["max_daily_trades"]:
        return False, "Sudah kena limit max trade harian."
    if open_positions >= risk_cfg["max_open_positions"]:
        return False, "Sudah kena limit max posisi terbuka."
    if consecutive_losses >= 5:
        return False, "5 loss beruntun — circuit breaker aktif, cooldown dulu."
    drawdown_pct = ((initial_equity - equity) / initial_equity * 100) if initial_equity > 0 else 0
    if drawdown_pct >= 20:
        return False, "Drawdown sudah 20%+ dari modal awal — kill switch aktif."
    return True, "ok"
