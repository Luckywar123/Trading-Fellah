"""Position Sizer"""
import logging

logger = logging.getLogger(__name__)

class PositionSizer:
    def __init__(self, risk_cfg):
        self.cfg = risk_cfg

    def calculate(self, equity, entry, sl):
        risk_pct = self.cfg.MAX_RISK_PER_TRADE_PCT / 100
        risk_amt = equity * risk_pct
        sl_dist = abs(entry - sl)
        
        if sl_dist == 0:
            return 0
        
        return risk_amt / sl_dist

    def can_trade(self, daily_trades, daily_pnl, consec_losses, equity):
        if daily_trades >= self.cfg.MAX_DAILY_TRADES:
            return False
        if consec_losses >= self.cfg.CONSECUTIVE_LOSS_PAUSE:
            return False
        return True
