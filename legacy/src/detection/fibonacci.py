"""Fibonacci Calculator"""
from typing import Dict

class FibonacciCalculator:
    RETRACEMENT_LEVELS = [0.236, 0.382, 0.500, 0.618, 0.786, 1.0]
    EXTENSION_LEVELS = [1.272, 1.414, 1.618, 2.0, 2.618]

    async def calculate(self, swing_data: Dict) -> Dict:
        swings = swing_data.get("swings", [])
        if len(swings) < 2:
            return {"confluence_score": 0.5, "levels": {}}

        highs = [s for s in swings if s["type"] == "HIGH"]
        lows = [s for s in swings if s["type"] == "LOW"]

        if not highs or not lows:
            return {"confluence_score": 0.5, "levels": {}}

        swing_high = highs[-1]["price"]
        swing_low = lows[-1]["price"]
        swing_range = swing_high - swing_low

        retracements = {}
        for level in self.RETRACEMENT_LEVELS:
            retracements[f"ret_{level}"] = swing_high - (swing_range * level)

        extensions = {}
        for level in self.EXTENSION_LEVELS:
            extensions[f"ext_{level}"] = swing_high + (swing_range * (level - 1))

        return {
            "confluence_score": 0.7,
            "retracements": retracements,
            "extensions": extensions,
            "extension_1618": extensions.get("ext_1.618", 0),
        }
