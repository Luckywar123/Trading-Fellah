"""Momentum Scanner v3.0"""
import logging
import numpy as np
from typing import Dict, List

logger = logging.getLogger(__name__)

class MomentumScanner:
    def __init__(self):
        self.min_score = 0.65
        self.lookback = 20

    async def scan(self, market_data: Dict) -> List[Dict]:
        signals = []
        for symbol, data in market_data.items():
            try:
                m = self.analyze(symbol, data)
                if m and m["strength"] >= self.min_score:
                    signals.append(m)
            except Exception as e:
                logger.debug(f"Scan error {symbol}: {e}")
        
        signals.sort(key=lambda x: x["strength"], reverse=True)
        return signals

    def analyze(self, symbol, data) -> Dict:
        prices = data.get("prices", [])
        volumes = data.get("volumes", [])

        if len(prices) < self.lookback:
            return None

        recent = prices[-self.lookback:]
        price_change = (recent[-1] - recent[0]) / recent[0]
        
        avg_vol = np.mean(volumes[:-3]) if len(volumes) > 3 else 1
        vol_spike = volumes[-1] / avg_vol if volumes and avg_vol > 0 else 1

        direction = "LONG" if price_change > 0 else "SHORT"
        score = min(1.0, abs(price_change) / 0.003) * 0.3 +                 min(1.0, (vol_spike - 1) / 1.0) * 0.3 if vol_spike > 1 else 0

        return {
            "symbol": symbol,
            "price": recent[-1],
            "direction": direction,
            "strength": score,
            "price_change_pct": price_change * 100,
            "timestamp": data.get("timestamp"),
        }
