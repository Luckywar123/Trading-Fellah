"""
Deteksi struktur market: swing high/low, order block, dan zona
support/resistance besar — plus validasi breakout. Ini "mata" dari sistem,
murni technical/quant (bukan LLM), karena analisa harga butuh presisi
angka, bukan generative text. AI berbasis LLM (lihat ai_agent.py) dipakai
terpisah buat baca berita & kebiasaan trading, BUKAN buat baca candlestick.

Definisi yang dipakai (gaya Smart Money Concept, disederhanakan):
- Swing high/low   : fractal pivot — titik lebih tinggi/rendah dari N bar
                      kiri & kanan.
- Order block       : candle berlawanan warna terakhir sebelum impulsive
                      move yang berhasil break swing sebelumnya (BOS).
- Support/Resistance: cluster dari swing points yang berdekatan harganya,
                      "besar" = banyak sentuhan (touches) & sering dites.
- Breakout tervalidasi: close menembus level + candle konfirmasi (bukan cuma
                      wick), dengan body candle minimal sekian % dari ATR
                      biar gak kena fakeout tipis.
"""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Zone:
    low: float
    high: float
    touches: int
    kind: str          # "support" | "resistance"
    strength: float     # 0..1


@dataclass
class OrderBlock:
    index: int
    direction: str       # LONG (bullish OB) | SHORT (bearish OB)
    zone_low: float
    zone_high: float
    formed_at: str


@dataclass
class SwingResult:
    swing_highs: list = field(default_factory=list)   # [{index, price, time}]
    swing_lows: list = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    order_blocks: list[OrderBlock] = field(default_factory=list)
    trend: str = "RANGE"                                # UPTREND | DOWNTREND | RANGE
    trend_strength: float = 0.5


class SwingDetector:
    def __init__(self, pivot_window: int = 5, zone_tolerance_pct: float = 0.06,
                 min_touches_for_major: int = 2, breakout_body_atr_mult: float = 0.6):
        self.pivot_window = pivot_window
        self.zone_tolerance_pct = zone_tolerance_pct        # toleransi cluster, % dari harga
        self.min_touches_for_major = min_touches_for_major
        self.breakout_body_atr_mult = breakout_body_atr_mult

    # ------------------------------------------------------------------ #
    def analyze(self, candles: list[Candle]) -> SwingResult:
        n = len(candles)
        w = self.pivot_window
        if n < w * 2 + 5:
            return SwingResult()

        highs = np.array([c.high for c in candles])
        lows = np.array([c.low for c in candles])
        closes = np.array([c.close for c in candles])

        swing_highs, swing_lows = [], []
        for i in range(w, n - w):
            window_h = highs[i - w:i + w + 1]
            if highs[i] == window_h.max() and np.argmax(window_h) == w:
                swing_highs.append({"index": i, "price": float(highs[i]), "time": candles[i].time})
            window_l = lows[i - w:i + w + 1]
            if lows[i] == window_l.min() and np.argmin(window_l) == w:
                swing_lows.append({"index": i, "price": float(lows[i]), "time": candles[i].time})

        zones = self._cluster_zones(swing_highs, swing_lows, closes[-1])
        order_blocks = self._find_order_blocks(candles, swing_highs, swing_lows)
        trend, strength = self._trend(swing_highs, swing_lows)

        return SwingResult(
            swing_highs=swing_highs[-15:],
            swing_lows=swing_lows[-15:],
            zones=zones,
            order_blocks=order_blocks[-10:],
            trend=trend,
            trend_strength=strength,
        )

    # ------------------------------------------------------------------ #
    def _cluster_zones(self, swing_highs, swing_lows, last_price: float) -> list[Zone]:
        points = [(p["price"], "resistance") for p in swing_highs] + \
                 [(p["price"], "support") for p in swing_lows]
        points.sort(key=lambda x: x[0])

        clusters: list[list[tuple]] = []
        for price, kind in points:
            placed = False
            for cluster in clusters:
                center = np.mean([p[0] for p in cluster])
                if abs(price - center) / max(center, 1e-9) <= self.zone_tolerance_pct / 100:
                    cluster.append((price, kind))
                    placed = True
                    break
            if not placed:
                clusters.append([(price, kind)])

        zones = []
        for cluster in clusters:
            prices = [p[0] for p in cluster]
            kinds = [p[1] for p in cluster]
            kind = max(set(kinds), key=kinds.count)
            touches = len(cluster)
            strength = min(1.0, touches / 5)
            zones.append(Zone(
                low=float(min(prices)), high=float(max(prices)),
                touches=touches, kind=kind, strength=round(strength, 2),
            ))

        # "support/resistance besar" = touches >= threshold, urut dari yg terkuat
        major = [z for z in zones if z.touches >= self.min_touches_for_major]
        major.sort(key=lambda z: (-z.strength, abs((z.low + z.high) / 2 - last_price)))
        return major

    # ------------------------------------------------------------------ #
    def _find_order_blocks(self, candles: list[Candle], swing_highs, swing_lows) -> list[OrderBlock]:
        obs = []
        sh_idx = {p["index"] for p in swing_highs}
        sl_idx = {p["index"] for p in swing_lows}

        for i in range(2, len(candles) - 1):
            c = candles[i]
            prev = candles[i - 1]
            is_bull_impulse = c.close > c.open and (c.close - c.open) > (c.high - c.low) * 0.5
            is_bear_impulse = c.close < c.open and (c.open - c.close) > (c.high - c.low) * 0.5

            # Bullish OB: candle turun terakhir sebelum impulsive naik yang break swing high sebelumnya
            if is_bull_impulse and prev.close < prev.open:
                recent_highs = [p["price"] for p in swing_highs if p["index"] < i]
                if recent_highs and c.close > recent_highs[-1]:
                    obs.append(OrderBlock(
                        index=i - 1, direction="LONG",
                        zone_low=prev.low, zone_high=prev.open, formed_at=prev.time,
                    ))

            # Bearish OB: candle naik terakhir sebelum impulsive turun yang break swing low sebelumnya
            if is_bear_impulse and prev.close > prev.open:
                recent_lows = [p["price"] for p in swing_lows if p["index"] < i]
                if recent_lows and c.close < recent_lows[-1]:
                    obs.append(OrderBlock(
                        index=i - 1, direction="SHORT",
                        zone_low=prev.open, zone_high=prev.high, formed_at=prev.time,
                    ))
        return obs

    # ------------------------------------------------------------------ #
    def _trend(self, swing_highs, swing_lows) -> tuple[str, float]:
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return "RANGE", 0.5
        hh = swing_highs[-1]["price"] > swing_highs[-2]["price"]
        hl = swing_lows[-1]["price"] > swing_lows[-2]["price"]
        lh = swing_highs[-1]["price"] < swing_highs[-2]["price"]
        ll = swing_lows[-1]["price"] < swing_lows[-2]["price"]

        if hh and hl:
            return "UPTREND", 0.8
        if lh and ll:
            return "DOWNTREND", 0.8
        return "RANGE", 0.5

    # ------------------------------------------------------------------ #
    def validate_breakout(self, candles: list[Candle], level: float, direction: str, atr: float) -> dict:
        """
        Cek apakah breakout di suatu level (swing high/low, order block, atau
        S/R besar) VALID — bukan cuma wick sesaat. Syarat:
          1. Candle terakhir CLOSE menembus level (bukan cuma high/low-nya).
          2. Body candle minimal `breakout_body_atr_mult` x ATR (momentum cukup kuat).
          3. Candle sebelumnya juga searah / tidak langsung reversal penuh.
        """
        if len(candles) < 2 or atr <= 0:
            return {"validated": False, "reason": "data tidak cukup"}

        last = candles[-1]
        prev = candles[-2]
        body = abs(last.close - last.open)

        if direction.upper() == "LONG":
            close_breaks = last.close > level
            momentum_ok = body >= atr * self.breakout_body_atr_mult and last.close > last.open
        else:
            close_breaks = last.close < level
            momentum_ok = body >= atr * self.breakout_body_atr_mult and last.close < last.open

        not_pure_fakeout = not (
            (direction.upper() == "LONG" and prev.close < prev.open and last.high > level and last.close < level)
            or
            (direction.upper() == "SHORT" and prev.close > prev.open and last.low < level and last.close > level)
        )

        validated = close_breaks and momentum_ok and not_pure_fakeout
        confidence = 0.0
        if validated:
            confidence = min(1.0, 0.5 + (body / atr) * 0.15)

        return {
            "validated": validated,
            "confidence": round(confidence, 2),
            "level": level,
            "direction": direction,
            "close_breaks": close_breaks,
            "momentum_ok": momentum_ok,
        }
