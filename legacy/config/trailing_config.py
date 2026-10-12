"""
Trailing Stop Config v3.0
SETALAH 50 PIKS PROFIT → TRAIL 10 PIKS DARI HARGA SEKARANG
"""

ACTIVE_MODE = "FIXED_DISTANCE_10PIPS"

# ===== FIXED DISTANCE MODE =====
TRAILING_RULES = {
    "crypto": {
        "activation_pips": 50,
        "trail_distance_pips": 10,
        "breakeven_at_pips": 15,
    },
    "forex": {
        "activation_pips": 50,
        "trail_distance_pips": 10,
        "breakeven_at_pips": 15,
    },
    "stock": {
        "activation_pct": 0.5,
        "trail_distance_pct": 0.1,
        "breakeven_at_pct": 0.2,
    },
}

SMART_AI_TRAILING = {
    "enabled": False,
    "model_path": "ml_models/weights/trailing_ai.pkl",
}

PROGRESSIVE_MODE = {
    "enabled": False,
    "schedule": [
        {"at_pips": 50, "trail_distance": 10},
        {"at_pips": 100, "trail_distance": 8},
        {"at_pips": 150, "trail_distance": 5},
    ],
}
