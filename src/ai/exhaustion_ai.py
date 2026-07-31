"""Exhaustion AI - Deteksi Reversal Dini"""
import logging
import numpy as np
from typing import Dict

logger = logging.getLogger(__name__)

class ExhaustionDetector:
    def __init__(self):
        self.rsi_ob = 75
        self.rsi_os = 25

    async def analyze(self, data: Dict) -> Dict:
        prices = data.get("prices", [])

        if len(prices) < 30:
            return {"score": 0.5, "confidence": 0.0, "recommendation": "HOLD"}

        rsi = self._rsi(prices)
        score = min(1.0, (rsi - 50) / 25) if rsi > 50 else min(1.0, (50 - rsi) / 25)

        recommendation = "EXIT" if score >= 0.75 else "HOLD"

        return {
            "score": score,
            "confidence": score,
            "recommendation": recommendation,
            "rsi": rsi,
        }

    def _rsi(self, p, period=14):
        if len(p) < period + 1: return 50
        d = np.diff(p[-period-1:])
        g = np.where(d > 0, d, 0)
        l = np.where(d < 0, -d, 0)
        if np.mean(l) == 0: return 100
        return 100 - 100/(1 + np.mean(g)/np.mean(l))
