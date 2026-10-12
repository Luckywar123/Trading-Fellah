"""Vantage MT5 Connector"""
import logging

logger = logging.getLogger(__name__)

class VantageConnector:
    def __init__(self):
        self.mt5 = None
        self.connected = False

    async def connect(self):
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.connected = True
            logger.info("Vantage MT5 connected")
            return True
        except ImportError:
            logger.warning("MetaTrader5 not installed - paper mode")
            return False

    async def get_ticker(self, symbol: str):
        if not self.connected:
            return self._simulate(symbol)
        return self._simulate(symbol)

    async def place_order(self, order: Dict):
        return {"order_id": f"PAPER_{order['symbol']}"}

    def _simulate(self, symbol):
        import random
        base = 1.0 if "USD" in symbol else 100.0
        prices = [base * (1 + random.uniform(-0.01, 0.01)) for _ in range(50)]
        return {
            "price": prices[-1],
            "prices": prices,
            "volumes": [random.randint(100, 1000) for _ in range(50)],
            "highs": [p * 1.001 for p in prices],
            "lows": [p * 0.999 for p in prices],
            "pip_value": 0.0001,
            "atr": base * 0.005,
        }
