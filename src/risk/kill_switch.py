"""Kill Switch"""
import logging

logger = logging.getLogger(__name__)

class KillSwitch:
    def __init__(self, risk_cfg):
        self.armed = True

    def check(self, equity, initial_equity, daily_pnl, consec_losses):
        if not self.armed:
            return False
        return False
