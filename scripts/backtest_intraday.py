"""
Backtest Pipeline

Unified intraday breakout backtester using TradeEngine, PaperSimulator,
and PortfolioTracker.
"""

import os
import math
import yaml
import requests
import logging
import statistics as stats
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from src.trade_engine import TradeEngine
from src.execution.portfolio_tracker import PortfolioTracker
from src.execution.paper_simulator import PaperSimulator
from src.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)


# ==========================================================
# Config & Environment
# ==========================================================
def load_config(path: str = "src/config/config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


cfg = load_config()
POLYGON_KEY = os.getenv(cfg["providers"]["polygon"]["api_key_env"])

START_CAPITAL = cfg["risk"].get("start_capital", 100000)
RISK_PER_TRADE = cfg["risk"]["max_position_risk"]
DAILY_STOP = cfg["risk"]["max_daily_loss"]
DAILY_TARGET = cfg["risk"]["target_daily_return"]

COMMISSION_PER_SHARE = cfg["costs"]["commission_per_share"]
MIN_COMMISSION = cfg["costs"]["min_commission"]
SLIPPAGE_PER_SHARE = cfg["costs"]["slippage_per_share"]
MARGIN_INTEREST_RATE = cfg["costs"]["margin_interest_rate"]
TRADING_DAYS_PER_YEAR = cfg["costs"]["trading_days_per_year"]

US_HOLIDAYS = {"2025-01-01", "2025-07-04", "2025-11-27", "2025-12-25"}


# ==========================================================
# Data Fetchers
# ==========================================================
def get_intraday_bars(ticker: str, start: str, end: str, interval="1", timespan="minute"):
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/"
        f"{interval}/{timespan}/{start}/{end}?limit=5000&apiKey={POLYGON_KEY}"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        logger.error(f"❌ Error fetching {ticker}: {resp.text[:200]}")
        return []
    return resp.json().get("results", [])


# ==========================================================
# Strategy
# ==========================================================
def breakout_strategy(bars) -> str:
    """Simple breakout: buy new high, sell new low."""
    if len(bars) < 3:
        return "HOLD"
    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]
    recent_close = closes[-1]
    if recent_close > max(highs[:-1]):
        return "BUY"
    if recent_close < min(lows[:-1]):
        return "SELL"
    return "HOLD"


# ==========================================================
# Backtest Class
# ==========================================================
class IntradayBacktester:
    def __init__(self, symbols, days=5):
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
        self.paper = PaperSimulator(slippage=SLIPPAGE_PER_SHARE, commission=COMMISSION_PER_SHARE)
        self.portfolio = PortfolioTracker()
        self.engine = TradeEngine(cfg)

    def run(self):
        end_date = datetime.today()
        start_date = end_date - timedelta(days=self.days)
        logfile = os.path.join(self.reports_dir, "intraday_backtest.csv")

        with open(logfile, "w", newline="") as f:
            writer = pd.DataFrame(
                columns=["symbol", "date", "time", "signal", "trade_pnl", "daily_pnl", "cum_equity"]
            )
            writer.to_csv(logfile, index=False)

        for symbol in self.symbols:
            equity, cum_pnl, wins, losses = START_CAPITAL, 0, 0, 0
            daily_returns, equity_curve = [], []

            logger.info(f"\n=== Backtesting {symbol} ===")

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

                    # simulate fill
                    fill = self.paper.simulate_fill(symbol, signal.lower(), 1, entry_bar["c"])
                    trade_pnl = (
                        (exit_bar["c"] - entry_bar["c"]) if signal == "BUY" else (entry_bar["c"] - exit_bar["c"])
                    ) if signal in ["BUY", "SELL"] else 0

                    trade_pnl -= fill["commission"]

                    daily_pnl += trade_pnl
                    cum_pnl += trade_pnl
                    equity += trade_pnl
                    equity_curve.append(equity)

                    with open(logfile, "a") as f:
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
                            columns=["symbol", "date", "time", "signal", "trade_pnl", "daily_pnl", "cum_equity"],
                        ).to_csv(f, header=False, index=False)

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
                plt.figure(figsize=(10, 5))
                plt.plot(equity_curve, label=f"{symbol} Equity")
                plt.title(f"Equity Curve – {symbol}")
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(self.reports_dir, f"{symbol}_equity_curve.png"))
                plt.close()

                rolling_max = [max(equity_curve[: i + 1]) for i in range(len(equity_curve))]
                drawdowns = [rm - x for rm, x in zip(rolling_max, equity_curve)]
                plt.figure(figsize=(10, 3))
                plt.plot(drawdowns, color="red", label=f"{symbol} DD")
                plt.title(f"Drawdown – {symbol}")
                plt.legend()
                plt.grid(True)
                plt.savefig(os.path.join(self.reports_dir, f"{symbol}_drawdown.png"))
                plt.close()

        self.print_summary()

    def print_summary(self):
        print("\n=== SUMMARY ===")
        print(f"{'Symbol':<8}{'Trades':<8}{'WinRate':<10}{'AvgDaily':<12}{'PnL':<12}{'Equity':<12}{'Sharpe':<8}")
        for sym, s in self.results_summary.items():
            print(
                f"{sym:<8}{s['trades']:<8}{s['win_rate']:.1%:<10}"
                f"{s['avg_daily']:<12.2f}{s['total_pnl']:<12.2f}"
                f"{s['final_equity']:<12.2f}{s['sharpe']:.2f}"
            )


# ==========================================================
# Run
# ==========================================================
if __name__ == "__main__":
    symbols = cfg["universe"]["Core_Stocks"][:3]  # sample: first 3 symbols
    backtester = IntradayBacktester(symbols, days=5)
    backtester.run()
