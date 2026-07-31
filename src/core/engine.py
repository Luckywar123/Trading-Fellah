"""
Aggressive Sniper Engine v3.0
SL TIGHT + Trailing 10 pips setelah 50 pips profit
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self, settings, risk_cfg, trail_cfg):
        self.settings = settings
        self.risk_cfg = risk_cfg
        self.trail_cfg = trail_cfg

        self.is_running = False
        self.mode = "PAPER"

        self.equity = 100.0
        self.initial_equity = 100.0
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.active_positions: List[Dict] = []
        self.trade_history: List[Dict] = []

        self.modules_loaded = False

    async def initialize(self):
        from src.detection.swing_detector import SwingDetector
        from src.detection.fibonacci import FibonacciCalculator
        from src.detection.mtf_analyzer import MultiTimeframeAnalyzer
        from src.detection.momentum_scanner import MomentumScanner
        from src.ai.exhaustion_ai import ExhaustionDetector
        from src.core.trailing_stop import TrailingStopManager
        from src.risk.position_sizer import PositionSizer
        from src.risk.circuit_breaker import CircuitBreaker
        from src.risk.kill_switch import KillSwitch
        from src.connectors.vantage_connector import VantageConnector
        from src.connectors.crypto_connector import CryptoConnector

        self.swing = SwingDetector()
        self.fib = FibonacciCalculator()
        self.mtf = MultiTimeframeAnalyzer()
        self.momentum = MomentumScanner()
        self.exhaustion = ExhaustionDetector()
        self.trailing = TrailingStopManager(self.risk_cfg, self.trail_cfg)
        self.sizer = PositionSizer(self.risk_cfg)
        self.breaker = CircuitBreaker(self.risk_cfg)
        self.kill = KillSwitch(self.risk_cfg)
        self.vantage = VantageConnector()
        self.crypto = CryptoConnector()

        await self.vantage.connect()
        await self.crypto.connect()
        self.modules_loaded = True

    async def run(self):
        await self.initialize()
        self.is_running = True
        logger.info("=" * 70)
        logger.info("AGGRESSIVE SNIPER BOT v3.0 - SL TIGHT MODE")
        logger.info(f"Equity: ${self.equity}")
        logger.info("=" * 70)

        while self.is_running:
            try:
                market_data = await self.fetch_all_markets()
                if not market_data:
                    await asyncio.sleep(3)
                    continue

                signals = await self.momentum.scan(market_data)
                if not signals:
                    await asyncio.sleep(3)
                    continue

                for signal in signals:
                    mtf_result = await self.mtf.confirm(signal, market_data)
                    if not mtf_result["confirmed"]:
                        continue

                    swing_data = await self.swing.detect(market_data[signal["symbol"]])
                    fib_levels = await self.fib.calculate(swing_data)

                    ai_results = await asyncio.gather(
                        self.exhaustion.analyze(market_data[signal["symbol"]]),
                    )
                    exh = ai_results[0]

                    composite = self.score_composite(signal, mtf_result, swing_data,
                                                      fib_levels, exh)

                    if not self.sizer.can_trade(
                        self.daily_trades, self.daily_pnl,
                        self.consecutive_losses, self.equity
                    ):
                        continue

                    if composite["score"] >= self.risk_cfg.AGGRESSIVE_FLAGS["ai_confidence_threshold"]:
                        await self.execute_entry(composite)

                await self.manage_positions(market_data)

                if self.breaker.check(self.equity, self.daily_pnl, self.consecutive_losses):
                    logger.critical("CIRCUIT BREAKER TRIGGERED")
                    await self.emergency_close_all()
                    break

                await asyncio.sleep(self.settings.SCAN_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Engine error: {e}", exc_info=True)
                await asyncio.sleep(5)

        logger.info("ENGINE STOPPED")

    def score_composite(self, signal, mtf, swing, fib, exh):
        weights = {
            "momentum": 0.25, "mtf": 0.15, "swing": 0.10,
            "fib": 0.10, "exhaustion": 0.10, "psychology": 0.07,
            "sentiment": 0.08, "vol": 0.05,
        }

        scores = {
            "momentum": signal.get("strength", 0),
            "mtf": mtf.get("confidence", 0),
            "swing": swing.get("trend_alignment", 0.5),
            "fib": fib.get("confluence_score", 0.5),
            "exhaustion": exh.get("score", 0.5),
        }

        total = sum(scores[k] * weights[k] for k in weights)

        atr = 0.001
        entry_price = signal.get("price", 0)

        if signal.get("direction") == "LONG":
            sl = entry_price - (atr * self.risk_cfg.SL_ATR_MULTIPLIER)
            tp = entry_price + (atr * 2.5)
        else:
            sl = entry_price + (atr * self.risk_cfg.SL_ATR_MULTIPLIER)
            tp = entry_price - (atr * 2.5)

        return {
            "score": total,
            "direction": signal.get("direction", "LONG"),
            "symbol": signal.get("symbol", ""),
            "entry_price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
            "atr": atr,
            "components": scores,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def execute_entry(self, composite):
        size = self.sizer.calculate(
            self.equity, composite["entry_price"], composite["stop_loss"]
        )

        order = {
            "order_id": f"{'PAPER' if self.mode == 'PAPER' else 'LIVE'}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "symbol": composite["symbol"],
            "direction": composite["direction"],
            "size": size,
            "entry_price": composite["entry_price"],
            "stop_loss": composite["stop_loss"],
            "take_profit": composite["take_profit"],
            "trailing_enabled": self.risk_cfg.TRAILING_ENABLED,
            "trail_trigger_pips": self.risk_cfg.TRAILING_TRIGGER_PIPS,
            "trail_distance_pips": self.risk_cfg.TRAIL_DISTANCE_PIPS,
            "confidence": composite["score"],
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "trailing_active": False,
            "breakeven_done": False,
        }

        self.active_positions.append(order)
        self.daily_trades += 1

        pip_value = 0.0001
        sl_pips = abs(composite["entry_price"] - composite["stop_loss"]) / pip_value

        logger.info(
            f"ENTRY: {order['direction']} {order['symbol']} | "
            f"Size: {size:.4f} | SL: {sl_pips:.0f} pips | "
            f"Trail: ON after {self.risk_cfg.TRAILING_TRIGGER_PIPS} pips"
        )

    async def manage_positions(self, market_data):
        for position in list(self.active_positions):
            sym = position["symbol"]
            data = market_data.get(sym)
            if not data:
                continue

            current_price = data.get("price", 0)
            if current_price == 0:
                continue

            pip_value = data.get("pip_value", 0.0001)

            if position["direction"] == "LONG":
                profit_pips = (current_price - position["entry_price"]) / pip_value
            else:
                profit_pips = (position["entry_price"] - current_price) / pip_value

            # Breakeven
            be_trigger = self.risk_cfg.BREAKEVEN_TRIGGER_PIPS
            if profit_pips >= be_trigger and not position.get("breakeven_done"):
                be_sl = position["entry_price"] + (1 * pip_value)
                if position["direction"] == "SHORT":
                    be_sl = position["entry_price"] - (1 * pip_value)
                position["stop_loss"] = be_sl
                position["breakeven_done"] = True
                logger.info(f"BREAKEVEN: {sym} SL moved to BE+1")

            # Trailing
            trail_trigger = self.risk_cfg.TRAILING_TRIGGER_PIPS
            trail_distance = self.risk_cfg.TRAIL_DISTANCE_PIPS

            if profit_pips >= trail_trigger and not position.get("trailing_active"):
                position["trailing_active"] = True
                logger.info(f"TRAILING ACTIVATED: {sym} @ {profit_pips:.0f} pips profit")

            if position.get("trailing_active"):
                pip_dist = trail_distance * pip_value
                if position["direction"] == "LONG":
                    new_sl = current_price - pip_dist
                else:
                    new_sl = current_price + pip_dist

                if position["direction"] == "LONG" and new_sl > position["stop_loss"]:
                    position["stop_loss"] = new_sl
                    logger.info(f"TRAIL UPDATE: {sym} SL -> {new_sl:.5f} | Profit: {profit_pips:.0f} pips")

            # Exit checks
            if position["direction"] == "LONG" and current_price <= position["stop_loss"]:
                await self.close_position(position, current_price, "SL_HIT")
                continue
            elif position["direction"] == "SHORT" and current_price >= position["stop_loss"]:
                await self.close_position(position, current_price, "SL_HIT")
                continue

    async def close_position(self, position, exit_price, reason):
        pnl = self.calc_pnl(position, exit_price, position["size"])

        position["exit_price"] = exit_price
        position["exit_reason"] = reason
        position["pnl"] = pnl
        position["closed_at"] = datetime.now(timezone.utc).isoformat()

        self.daily_pnl += pnl
        self.equity += pnl

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self.trade_history.append(dict(position))
        
        if position in self.active_positions:
            self.active_positions.remove(position)

        emoji = "✅" if pnl >= 0 else "❌"
        logger.info(
            f"{emoji} CLOSE: {position['symbol']} | {reason} | "
            f"PnL: ${pnl:.2f} | Equity: ${self.equity:.2f}"
        )

    def calc_pnl(self, position, exit_price, size):
        entry = position["entry_price"]
        if position["direction"] == "LONG":
            return (exit_price - entry) * size
        else:
            return (entry - exit_price) * size

    async def fetch_all_markets(self):
        data = {}
        for pair in self.settings.CRYPTO_PAIRS:
            d = await self.crypto.get_ticker(pair)
            if d: data[pair] = d
        for pair in self.settings.FOREX_PAIRS:
            d = await self.vantage.get_ticker(pair)
            if d: data[pair] = d
        return data

    async def emergency_close_all(self):
        logger.critical("!!! EMERGENCY CLOSE ALL !!!")
        for pos in list(self.active_positions):
            try:
                await self.close_position(pos, pos["entry_price"], "KILL_SWITCH")
            except Exception as e:
                logger.critical(f"Fail close {pos['symbol']}: {e}")
        self.is_running = False

    def calculate_win_rate(self):
        if not self.trade_history: return 0.0
        wins = sum(1 for t in self.trade_history if t.get("pnl", 0) > 0)
        return (wins / len(self.trade_history)) * 100
