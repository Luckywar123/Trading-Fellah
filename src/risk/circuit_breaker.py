"""Circuit Breaker"""
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, risk_cfg):
        self.cfg = risk_cfg.CIRCUIT_BREAKER

    def check(self, equity, daily_pnl, consec_losses):
        max_daily = self.cfg.get("max_daily_loss_pct", 5)
        max_consec = self.cfg.get("max_consecutive_losses", 5)

        daily_loss_pct = abs(daily_pnl) / equity * 100 if daily_pnl < 0 else 0
        if daily_pnl < 0 and daily_loss_pct >= max_daily:
            return True
        if consec_losses >= max_consec:
            return True
        return False
