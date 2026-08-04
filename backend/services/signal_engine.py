"""
Logic "cari sinyal yang tervalidasi" — dipakai SAMA PERSIS oleh tiga tempat:
backtest_engine.py, forward_test.py, dan live_autotrader.py. Sebelumnya versi
awal proyek ini nulis ulang logic yang mirip di masing-masing file (rawan
diam-diam melenceng kalau salah satu diubah tapi yang lain lupa). Sekarang
satu sumber kebenaran di sini.
"""
from backend.services.swing_detector import Candle, SwingDetector


def compute_atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period


def find_validated_signal(detector: SwingDetector, candles: list[Candle], risk_cfg: dict) -> dict | None:
    """Return sinyal paling confident yang lolos threshold, atau None kalau gak ada."""
    atr = compute_atr(candles)
    if atr <= 0:
        return None

    analysis = detector.analyze(candles)
    candidates = []

    for ob in analysis.order_blocks:
        level = ob.zone_high if ob.direction == "LONG" else ob.zone_low
        v = detector.validate_breakout(candles, level, ob.direction, atr)
        if v["validated"] and v["confidence"] >= risk_cfg["ai_confidence_threshold"]:
            candidates.append({"direction": ob.direction, "type": "order_block", "confidence": v["confidence"], "level": level})

    for zone in analysis.zones:
        level = zone.high if zone.kind == "resistance" else zone.low
        direction = "LONG" if zone.kind == "resistance" else "SHORT"
        v = detector.validate_breakout(candles, level, direction, atr)
        if v["validated"] and v["confidence"] >= risk_cfg["ai_confidence_threshold"]:
            candidates.append({"direction": direction, "type": "support_resistance", "confidence": v["confidence"], "level": level})

    if not candidates:
        return None
    best = max(candidates, key=lambda c: c["confidence"])
    best["atr"] = atr
    return best
