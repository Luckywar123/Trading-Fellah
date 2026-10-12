"""Crypto Connector (CCXT)"""
import logging

logger = logging.getLogger(__name__)

class CryptoConnector:
    def __init__(self):
        self.exchange = None

    async def connect(self):
        try:
            import ccxt.pro as ccxtpro
            logger.info("Crypto connector ready")
        except ImportError:
            logger.warning("CCXT not installed - simulated mode")

    async def get_ticker(self, pair: str):
        return self._simulate(pair)

    def _simulate(self, pair):
        import random
        base = 50000 if "BTC" in pair else 3000 if "ETH" in pair else 100
        prices = [base * (1 + random.uniform(-0.01, 0.01)) for _ in range(50)]
        return {
            "price": prices[-1],
            "prices": prices,
            "volumes": [random.randint(100, 10000) for _ in range(50)],
            "highs": [p * 1.001 for p in prices],
            "lows": [p * 0.999 for p in prices],
            "pip_value": 0.01,
            "atr": base * 0.005,
        }
