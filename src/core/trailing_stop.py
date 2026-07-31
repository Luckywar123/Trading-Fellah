"""Trailing Stop Manager v3.0"""
import logging

logger = logging.getLogger(__name__)

class TrailingStopManager:
    def __init__(self, risk_cfg, trail_cfg):
        self.risk_cfg = risk_cfg
        self.trail_cfg = trail_cfg
        self.states = {}

    def update(self, position, current_price, profit_pips, market_data):
        pid = position.get("order_id", "")
        
        if pid not in self.states:
            self.states[pid] = {"activated": False, "last_sl": position["stop_loss"]}
        
        state = self.states[pid]
        activation = self.risk_cfg.TRAILING_TRIGGER_PIPS
        distance = self.risk_cfg.TRAIL_DISTANCE_PIPS
        pip_value = market_data.get("pip_value", 0.0001)

        if profit_pips < activation:
            return position["stop_loss"]
        
        state["activated"] = True
        position["trailing_active"] = True

        trail_distance = distance * pip_value
        
        if position["direction"] == "LONG":
            new_sl = current_price - trail_distance
            if new_sl > position["stop_loss"]:
                state["last_sl"] = new_sl
                return new_sl
        else:
            new_sl = current_price + trail_distance
            if position["stop_loss"] == 0 or new_sl < position["stop_loss"]:
                state["last_sl"] = new_sl
                return new_sl

        return position["stop_loss"]
