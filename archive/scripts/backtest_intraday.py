"""
Intraday Backtest Pipeline (Quant Pro v6.5 – Hedge-Fund OE Grade, Fixed)
------------------------------------------------------------------------
Responsibilities:
- Run intraday breakout backtests using Polygon intraday bars
- Engine stack: RiskManager, PaperSimulator, PortfolioTracker, TradeEngine
- Strategy: breakout (buy highs, sell lows, ties → SELL risk-off)
- Reports: CSV trades, equity curve, drawdown plots, summary table
- Robust: safe bar parsing, RiskManager args fixed, CSV write guarded
"""

import logging
import math
import os
import statistics as stats
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import requests
import yaml

from src.execution.paper_simulator import PaperSimulator
from src.execution.portfolio_tracker import PortfolioTracker
from src.risk.risk_manager import RiskManager
from src.trade_engine import TradeEngine

# ------------------------------------------------------
# Logging
# ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("IntradayBacktester")

# ------------------------------------------------------
# Config & Environment
# ------------------------------------------------------
def load_config(path: str = "src/config/config.yaml") -> dict:
    """Load YAML configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


cfg = load_config()
POLYGON_KEY = os.getenv(cfg["providers"]["polygon"]["api_key_env"], "")

START_CAPITAL = cfg["risk"].get("start_capital", 100000)
RISK_PER_TRADE = cfg["risk"].get("max_position_risk", 0.01)
DAILY_STOP = cfg["risk"].get("max_daily_loss", -0.03)
DAILY_TARGET = cfg["risk"].get("target_daily_return", 0.02)

COMMISSION_PER_SHARE = cfg["costs"].get("commission_per_share", 0.0)
MIN_COMMISSION = cfg["costs"].get("min_commission", 0.0)
SLIPPAGE_PER_SHARE = cfg["costs"].get("slippage_per_share", 0.0)

US_HOLIDAYS = {"2025-01-01", "2025-07-04", "2025-11-27", "2025-12-25"}

# ------------------------------------------------------
# Data Fetchers
# ------------------------------------------------------
def get_intraday_bars(ticker: str, start: str, end: str, interval="1", timespan="minute"):
    """Fetch intraday bars from Polygon.io."""
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/"
        f"{interval}/{timespan}/{start}/{end}?limit=5000&apiKey={POLYGON_KEY}"
    )
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            logger.error(f"❌ Error fetching {ticker}: {resp.text[:200]}")
            return []
        return resp.json().get("results", [])
    except Exception as e:
        logger.error(f"❌ Request failed for {ticker}: {e}")
        return []

# ------------------------------------------------------
# Strategy
# ------------------------------------------------------
def breakout_strategy(bars) -> str:
    """Breakout strategy: buy new high, sell new low, else hold."""
    if len(bars) < 3:
        return "HOLD"

    try:
        closes = [b["c"] for b in bars if "c" in b]
        highs = [b["h"] for b in bars if "h" in b]
        lows = [b["l"] for b in bars if "l" in b]
    except Exception:
        logger.warning("⚠️ Missing fields in bars → HOLD")
        return "HOLD"

    if not closes or not highs or not lows:
        logger.warning("⚠️ Empty closes/highs/lows → HOLD")
        return "HOLD"

    recent_close = closes[-1]
    prev_high = max(highs[:-1])
    prev_low = min(lows[:-1])

    if recent_close > prev_high:
        return "BUY"
    if recent_close < prev_low:
        return "SELL"
    # Tie cases → SELL (risk-off)
    if recent_close == prev_high or recent_close == prev_low:
        return "SELL"
    return "HOLD"

# ------------------------------------------------------
# Backtester
# ------------------------------------------------------
class IntradayBacktester:
    def __init__(self, symbols, days: int = 5):
        self.symbols = symbols
        self.days = days
        self.results_summary = {}
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Engine stack
        self.risk_manager = RiskManager(
            daily_loss_limit=DAILY_STOP,
            trade_loss_limit=None,
            max_leverage=1.0,
            equity=START_CAPITAL,
        )
        self.paper = PaperSimulator(
            slippage=SLIPPAGE_PER_SHARE,
            commission=COMMISSION_PER_SHARE,
        )
        self.portfolio = PortfolioTracker()
        self.engine = TradeEngine(cfg)

    def run(self):
        """Run intraday backtest across all symbols."""
        end_date = datetime.today()
        start_date = end_date - timedelta(days=self.days)
        logfile = os.path.join(self.reports_dir, "intraday_backtest.csv")

        # init CSV header
        pd.DataFrame(
            columns=[
                "symbol",
                "date",
                "time",
                "signal",
                "trade_pnl",
                "daily_pnl",
                "cum_equity",
            ]
        ).to_csv(logfile, index=False)

        for symbol in self.symbols:
            equity, cum_pnl, wins, losses = START_CAPITAL, 0, 0, 0
            daily_returns, equity_curve = [], []

            logger.info(f"=== Backtesting {symbol} ===")

            for i in range(self.days):
                day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                if day in US_HOLIDAYS:
                    continue

                bars = get_intraday_bars(symbol, day, day)
                if not bars:
                    continue

                daily_pnl, stop_day = 0, False
                for j in range(2, len(bars) - 1):
                    signal = breakout_strategy(bars[j - 2 : j + 1])
                    entry_bar, exit_bar = bars[j], bars[j + 1]

                    # Risk check (dummy args)
                    try:
                        if not self.risk_manager.check_trade(signal, 1, 0.0):
                            continue
                    except Exception as e:
                        logger.error(f"RiskManager check failed: {e}")
                        continue

                    # simulate fill
                    fill = self.paper.simulate_fill(
                        symbol, signal.lower(), 1, entry_bar.get("c", 0.0)
                    )
                    trade_pnl = 0
                    if signal == "BUY":
                        trade_pnl = exit_bar.get("c", 0.0) - entry_bar.get("c", 0.0)
                    elif signal == "SELL":
                        trade_pnl = entry_bar.get("c", 0.0) - exit_bar.get("c", 0.0)

                    trade_pnl -= fill.get("commission", 0.0)

                    daily_pnl += trade_pnl
                    cum_pnl += trade_pnl
                    equity += trade_pnl
                    equity_curve.append(equity)

                    try:
                        pd.DataFrame(
                            [[
                                symbol,
                                day,
                                datetime.fromtimestamp(entry_bar["t"] / 1000).strftime("%H:%M"),
                                signal,
                                trade_pnl,
                                daily_pnl,
                                equity,
                            ]],
                            columns=[
                                "symbol",
                                "date",
                                "time",
                                "signal",
                                "trade_pnl",
                                "daily_pnl",
                                "cum_equity",
                            ],
                        ).to_csv(logfile, mode="a", header=False, index=False)
                    except Exception as e:
                        logger.error(f"CSV write failed: {e}")

                    if trade_pnl > 0:
                        wins += 1
                    elif trade_pnl < 0:
                        losses += 1

                    if daily_pnl <= DAILY_STOP * START_CAPITAL:
                        stop_day = True
                        break
                    if daily_pnl >= DAILY_TARGET * START_CAPITAL:
                        stop_day = True
                        break

                if not stop_day:
                    daily_returns.append(daily_pnl)

            # metrics
            avg_daily = stats.mean(daily_returns) if daily_returns else 0
            stdev = stats.stdev(daily_returns) if len(daily_returns) > 1 else 0
            sharpe = (avg_daily / stdev) * math.sqrt(252) if stdev > 0 else 0
            win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

            self.results_summary[symbol] = {
                "trades": wins + losses,
                "win_rate": win_rate,
                "avg_daily": avg_daily,
                "total_pnl": cum_pnl,
                "final_equity": equity,
                "sharpe": sharpe,
            }

            # plots
            if equity_curve:
                self._plot_equity(symbol, equity_curve)
                self._plot_drawdown(symbol, equity_curve)

        self.print_summary()

    def _plot_equity(self, symbol: str, equity_curve):
        plt.figure(figsize=(10, 5))
        plt.plot(equity_curve, label=f"{symbol} Equity")
        plt.title(f"Equity Curve – {symbol}")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.reports_dir, f"{symbol}_equity_curve.png"))
        plt.close()

    def _plot_drawdown(self, symbol: str, equity_curve):
        rolling_max = [max(equity_curve[: i + 1]) for i in range(len(equity_curve))]
        drawdowns = [rm - x for rm, x in zip(rolling_max, equity_curve)]
        plt.figure(figsize=(10, 3))
        plt.plot(drawdowns, color="red", label=f"{symbol} DD")
        plt.title(f"Drawdown – {symbol}")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.reports_dir, f"{symbol}_drawdown.png"))
        plt.close()

    def print_summary(self):
        print("\n=== SUMMARY ===")
        print(
            f"{'Symbol':<8}{'Trades':<8}{'WinRate':<10}{'AvgDaily':<12}"
            f"{'PnL':<12}{'Equity':<12}{'Sharpe':<8}"
        )
        for sym, s in self.results_summary.items():
            print(
                f"{sym:<8}{s['trades']:<8}{s['win_rate']:.1%:<10}"
                f"{s['avg_daily']:<12.2f}{s['total_pnl']:<12.2f}"
                f"{s['final_equity']:<12.2f}{s['sharpe']:.2f}"
            )


# ------------------------------------------------------
# Run
# ------------------------------------------------------
if __name__ == "__main__":
    symbols = cfg["universe"]["Core_Stocks"][:3]  # sample: first 3 symbols
    backtester = IntradayBacktester(symbols, days=5)
    backtester.run()
