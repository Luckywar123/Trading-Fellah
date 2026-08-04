"""
Backtest engine — muter ulang data historis (dari MetaApi
get_historical_candles) lewat LOGIC YANG SAMA PERSIS dengan yang dipakai
live (swing_detector + risk_manager), biar hasil backtest representatif
buat forward test & live trading. Gak ada logic kembar yang bisa beda
perilaku.

Catatan jujur: ini backtest sederhana (bar-by-bar, fill di harga close bar
konfirmasi, tanpa model spread/slippage dinamis — dipakai flat pip buffer).
Cukup buat riset & tuning parameter awal, TAPI hasil live selalu bisa beda
karena slippage, requote, dan latency eksekusi broker asli.
"""
from dataclasses import dataclass, field

from backend.services.swing_detector import Candle, SwingDetector
from backend.services.risk_manager import calculate_position_size
from backend.services.signal_engine import compute_atr, find_validated_signal


@dataclass
class BacktestTrade:
    symbol: str
    direction: str
    entry_index: int
    entry_price: float
    stop_loss: float
    exit_index: int | None = None
    exit_price: float | None = None
    volume: float = 0.0
    pnl: float = 0.0
    exit_reason: str = ""
    signal_type: str = ""


@dataclass
class BacktestResult:
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)
    starting_equity: float = 1000.0
    final_equity: float = 1000.0
    win_rate: float = 0.0
    total_trades: int = 0
    net_pnl: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float = 0.0


class BacktestEngine:
    def __init__(self, risk_cfg: dict, pip_value_per_lot: float = 10.0,
                 contract_size: float = 100_000, leverage: int = 100,
                 spread_pips: float = 1.0, lookback_bars: int = 60):
        self.risk_cfg = risk_cfg
        self.pip_value_per_lot = pip_value_per_lot
        self.contract_size = contract_size
        self.leverage = leverage
        self.spread = spread_pips * 0.0001
        self.lookback = lookback_bars
        self.detector = SwingDetector()

    def run(self, symbol: str, candles: list[Candle], starting_equity: float = 1000.0) -> BacktestResult:
        equity = starting_equity
        free_margin = starting_equity
        open_trade: BacktestTrade | None = None
        trades: list[BacktestTrade] = []
        curve = []
        pip = 0.0001

        for i in range(self.lookback, len(candles)):
            window = candles[max(0, i - self.lookback):i + 1]
            atr = compute_atr(window)

            # --- kelola posisi terbuka ---
            if open_trade:
                c = candles[i]
                hit_sl = (c.low <= open_trade.stop_loss) if open_trade.direction == "LONG" \
                    else (c.high >= open_trade.stop_loss)
                if hit_sl:
                    open_trade.exit_index = i
                    open_trade.exit_price = open_trade.stop_loss
                    open_trade.exit_reason = "SL_HIT"
                    pnl = self._calc_pnl(open_trade)
                    open_trade.pnl = pnl
                    equity += pnl
                    free_margin = equity
                    trades.append(open_trade)
                    open_trade = None
                else:
                    profit_pips = self._profit_pips(open_trade, c.close, pip)
                    if profit_pips >= self.risk_cfg["trailing_trigger_pips"]:
                        trail_dist = self.risk_cfg["trail_distance_pips"] * pip
                        new_sl = c.close - trail_dist if open_trade.direction == "LONG" else c.close + trail_dist
                        if open_trade.direction == "LONG" and new_sl > open_trade.stop_loss:
                            open_trade.stop_loss = new_sl
                        elif open_trade.direction == "SHORT" and new_sl < open_trade.stop_loss:
                            open_trade.stop_loss = new_sl

            # --- cari sinyal baru kalau lagi flat ---
            if not open_trade and atr > 0:
                signal = find_validated_signal(self.detector, window, self.risk_cfg)
                if signal:
                    entry_price = candles[i].close + (self.spread if signal["direction"] == "LONG" else -self.spread)
                    sl = self._stop_loss(entry_price, signal["direction"], atr)
                    sizing = calculate_position_size(
                        equity=equity, free_margin=free_margin, entry_price=entry_price,
                        stop_loss=sl, leverage=self.leverage, contract_size=self.contract_size,
                        pip_value_per_lot=self.pip_value_per_lot, risk_cfg=self.risk_cfg,
                    )
                    if sizing.volume_lots > 0:
                        open_trade = BacktestTrade(
                            symbol=symbol, direction=signal["direction"], entry_index=i,
                            entry_price=entry_price, stop_loss=sl, volume=sizing.volume_lots,
                            signal_type=signal["type"],
                        )
                        free_margin -= sizing.margin_required

            curve.append({"t": candles[i].time, "equity": round(equity, 2)})

        if open_trade:
            open_trade.exit_index = len(candles) - 1
            open_trade.exit_price = candles[-1].close
            open_trade.exit_reason = "END_OF_DATA"
            open_trade.pnl = self._calc_pnl(open_trade)
            equity += open_trade.pnl
            trades.append(open_trade)

        return self._summarize(trades, curve, starting_equity, equity)

    # ------------------------------------------------------------------ #

    def _stop_loss(self, entry: float, direction: str, atr: float) -> float:
        dist = atr * self.risk_cfg["sl_atr_multiplier"]
        return entry - dist if direction == "LONG" else entry + dist

    def _profit_pips(self, trade: BacktestTrade, price: float, pip: float) -> float:
        if trade.direction == "LONG":
            return (price - trade.entry_price) / pip
        return (trade.entry_price - price) / pip

    def _calc_pnl(self, trade: BacktestTrade) -> float:
        diff = (trade.exit_price - trade.entry_price) if trade.direction == "LONG" \
            else (trade.entry_price - trade.exit_price)
        pips = diff / 0.0001
        return pips * self.pip_value_per_lot * trade.volume

    def _summarize(self, trades, curve, start_eq, final_eq) -> BacktestResult:
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))

        peak = start_eq
        max_dd = 0.0
        for point in curve:
            peak = max(peak, point["equity"])
            dd = (peak - point["equity"]) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return BacktestResult(
            trades=trades, equity_curve=curve, starting_equity=start_eq, final_equity=round(final_eq, 2),
            win_rate=round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
            total_trades=len(trades), net_pnl=round(final_eq - start_eq, 2),
            max_drawdown_pct=round(max_dd, 2),
            profit_factor=round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
        )
