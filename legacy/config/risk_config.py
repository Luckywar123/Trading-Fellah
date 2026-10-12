"""
Risk Config v3.0 - SL TIGHT + TRAILING
Tidak pakai RR sacrifice anymore - momentum AI jaga reversal
"""

RISK_PROFILE = "AGGRESSIVE_MOMENTUM"

# ===== POSITION SIZING =====
MAX_RISK_PER_TRADE_PCT = 2.0
MAX_OPEN_POSITIONS = 5
MAX_DAILY_TRADES = 25

# ===== SL TEPAT =====
SL_MODE = "ATR_TIGHT"
SL_ATR_MULTIPLIER = 1.2
SL_MIN_PIPS_CRYPTO = 10
SL_MIN_PIPS_FOREX = 6

# ===== TRADING RULES =====
BREAKEVEN_TRIGGER_PIPS = 15
BREAKEVEN_BUFFER_PIPS = 1

# ===== TRAILING STOP CONFIG =====
TRAILING_ENABLED = True
TRAILING_TRIGGER_PIPS = 50   # Aktif setelah 50 pips profit
TRAIL_DISTANCE_PIPS = 10     # Jarak trail 10 pips dari harga

PROGRESSIVE_TRAILING = False

# ===== TARGET METRICS =====
TARGET_WIN_RATE = 80.0
MIN_WIN_RATE_TO_STAY_ACTIVE = 65.0
TARGET_MONTHLY_RETURN_PCT = 30.0

# ===== CIRCUIT BREAKER =====
CIRCUIT_BREAKER = {
    "max_drawdown_pct": 15.0,
    "max_daily_loss_pct": 5.0,
    "max_consecutive_losses": 5,
    "cooldown_minutes": 30,
    "emergency_kill_switch": True,
}

# ===== AGGRESSIVE FLAGS =====
AGGRESSIVE_FLAGS = {
    "scale_in_allowed": False,
    "scale_out_enabled": True,
    "partial_close_rules": [
        {"at_pips": 25, "close_pct": 30},
        {"at_pips": 50, "close_pct": 30},
    ],
    "news_blackout_minutes": 5,
    "min_momentum_score": 0.65,
    "ai_confidence_threshold": 0.70,
    "exhaustion_exit_enabled": True,
    "exhaustion_confidence_threshold": 0.75,
}
