"""Swing Detector"""
import numpy as np
from typing import Dict, List

class SwingDetector:
    def __init__(self):
        self.pivot_window = 5

    async def detect(self, data: Dict) -> Dict:
        highs = data.get("highs", [])
        lows = data.get("lows", [])

        if len(highs) < self.pivot_window * 2 + 1:
            return {"swings": [], "trend_alignment": 0.5, "recent_high": 0, "recent_low": 0}

        swings = []
        for i in range(self.pivot_window, len(highs) - self.pivot_window):
            left_max = max(highs[i - self.pivot_window:i])
            right_max = max(highs[i + 1:i + self.pivot_window + 1])
            if highs[i] > left_max and highs[i] > right_max:
                swings.append({"type": "HIGH", "price": highs[i], "index": i})

        return {
            "swings": swings[-10:],
            "structure": {"pattern": "UPTREND" if swings else "RANGE"},
            "trend_alignment": 0.7 if swings else 0.5,
            "recent_high": max(highs[-20:]) if len(highs) >= 20 else max(highs),
            "recent_low": min(lows[-20:]) if len(lows) >= 20 else min(lows),
        }
