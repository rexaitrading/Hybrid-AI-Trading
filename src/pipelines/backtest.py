"""
Backtest Pipeline (Multi-Strategy with Risk Integration)

Features:
- Fetch Polygon intraday bars
- Run multiple modular strategies (Breakout, MA, RSI, Bollinger, MACD, VWAP, etc.)
- Execute trades via PaperSimulator
- Enforce RiskManager rules (daily stop, per-trade stop, leverage)
- Track blocked trades & blocked %
- Generate Excel + HTML comparison reports
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
from typing import Dict, Callable, List

from src.trade_engine import TradeEngine
from src.execution.portfolio_tracker import PortfolioTracker
from src.execution.paper_simulator import PaperSimulator
from src.risk.risk_manager import RiskManager

# === Strategies ===
from src.signals import (
    breakout_intraday,
    moving_average_signal,
    rsi_signal,
    bollinger_bands_signal,
    macd_signal,
    vwap_signal,
)

logger = logging.getLogger(__name__)


# ==========================================================
# Config Loader
# ==========================================================
def load_config(path: str = "src/config/config.yaml") -> dict:
    """Load config YAML safely."""
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


# ==========================================================
# Data Fetcher
# ==========================================================
def get_intraday_bars(
    ticker: str, start: str, end: str, api_key: str, interval="1", timespan="minute"
):
    """Fetch intraday bars from Polygon.io"""
    if not api_key:
        return []
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/"
        f"{interval}/{timespan}/{start}/{end}?limit=5000&apiKey={api_key}"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        logger.error(f"❌ Error fetching {ticker}: {resp.text[:200]}")
        return []
    return resp.json().get("results", [])


# ==========================================================
# Backtester
# ==========================================================
class IntradayBacktester:
    def __init__(self, symbols: List[str], days: int = 5, strategies: Dict[str, Callable] = None):
        # Load config
        self.cfg = load_config()
        providers = self.cfg.get("providers", {})
        polygon_cfg = providers.get("polygon", {})
        self.POLYGON_KEY = os.getenv(polygon_cfg.get("api_key_env", ""), "")

        risk_cfg = self.cfg.get("risk", {})
        cost_cfg = self.cfg.get("costs", {})

        self.start_capital = risk_cfg.get("start_capital", 100000)
        self.daily_stop = risk_cfg.get("max_daily_loss", -0.03)
        self.daily_target = risk_cfg.get("target_daily_return", 0.02)

        self.commission_per_share = cost_cfg.get("commission_per_share", 0.0)
        self.slippage_per_share = cost_cfg.get("slippage_per_share", 0.0)

        self.symbols = symbols
        self.days = days
        self.results_summary: Dict = {}
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Register strategies
        self.strategies = strategies or {
            "breakout": breakout_intraday,
            "ma": moving_average_signal,
            "rsi": rsi_signal,
            "bollinger": bollinger_bands_signal,
            "macd": macd_signal,
            "vwap": vwap_signal,
        }
        # Drop None
        self.strategies = {k: v for k, v in self.strategies.items() if v}

        # Engine stack
        self.risk_manager = RiskManager(
            daily_loss_limit=self.daily_stop,
            trade_loss_limit=-0.01,  # per-trade -1%
            max_leverage=1.0,
            equity=self.start_capital,
        )
        self.paper = PaperSimulator(
            slippage=self.slippage_per_share, commission=self.commission_per_share
        )
        self.portfolio = PortfolioTracker()
        self.engine = TradeEngine(self.cfg)

    def run(self):
        """Main backtest loop."""
        end_date = datetime.today()
        start_date = end_date - timedelta(days=self.days)

        for strategy_name, strategy_func in self.strategies.items():
            self.results_summary[strategy_name] = {}
            logger.info(f"\n🚀 Running strategy: {strategy_name}")

            logfile = os.path.join(self.reports_dir, f"backtest_{strategy_name}.csv")
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
                equity, cum_pnl, wins, losses, blocked_trades = (
                    self.start_capital,
                    0,
                    0,
                    0,
                    0,
                )
                daily_returns, equity_curve = [], []

                for i in range(self.days):
                    day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                    if day in {"2025-01-01", "2025-07-04", "2025-11-27", "2025-12-25"}:
                        continue

                    self.risk_manager.reset_day()
                    bars = get_intraday_bars(symbol, day, day, self.POLYGON_KEY)
                    if not bars:
                        continue

                    daily_pnl, stop_day = 0, False
                    for j in range(10, len(bars) - 1):
                        signal = strategy_func(bars[: j + 1])
                        if signal == "HOLD":
                            continue

                        entry_bar, exit_bar = bars[j], bars[j + 1]
                        fill = self.paper.simulate_fill(
                            symbol, signal.lower(), 1, entry_bar["c"]
                        )

                        trade_pnl = (
                            (exit_bar["c"] - entry_bar["c"])
                            if signal == "BUY"
                            else (entry_bar["c"] - exit_bar["c"])
                        )
                        trade_pnl -= fill["commission"]

                        notional = entry_bar["c"]
                        allowed = self.risk_manager.check_trade(trade_pnl, notional)

                        if not allowed:
                            blocked_trades += 1
                            self._log_trade(
                                logfile,
                                symbol,
                                day,
                                entry_bar,
                                signal,
                                "BLOCKED",
                                daily_pnl,
                                equity,
                            )
                            stop_day = True
                            break

                        daily_pnl += trade_pnl
                        cum_pnl += trade_pnl
                        equity += trade_pnl
                        equity_curve.append(equity)

                        self._log_trade(
                            logfile,
                            symbol,
                            day,
                            entry_bar,
                            signal,
                            trade_pnl,
                            daily_pnl,
                            equity,
                        )

                        if trade_pnl > 0:
                            wins += 1
                        elif trade_pnl < 0:
                            losses += 1

                        if (
                            daily_pnl <= self.daily_stop * self.start_capital
                            or daily_pnl >= self.daily_target * self.start_capital
                        ):
                            stop_day = True
                            break

                    if not stop_day:
                        daily_returns.append(daily_pnl)

                # === Metrics ===
                total_trades = wins + losses + blocked_trades
                avg_daily = stats.mean(daily_returns) if daily_returns else 0
                stdev = stats.stdev(daily_returns) if len(daily_returns) > 1 else 0
                sharpe = (avg_daily / stdev) * math.sqrt(252) if stdev > 0 else 0
                win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
                blocked_pct = (
                    (blocked_trades / total_trades * 100) if total_trades > 0 else 0
                )

                self.results_summary[strategy_name][symbol] = {
                    "trades": wins + losses,
                    "win_rate": win_rate,
                    "avg_daily": avg_daily,
                    "total_pnl": cum_pnl,
                    "final_equity": equity,
                    "sharpe": sharpe,
                    "blocked_trades": blocked_trades,
                    "blocked_pct": blocked_pct,
                }

                if equity_curve:
                    self._plot_equity(symbol, equity_curve, strategy_name)
                    self._plot_drawdown(symbol, equity_curve, strategy_name)

        self.print_summary()
        self.export_leaderboard()

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------
    def _log_trade(self, logfile, symbol, day, entry_bar, signal, trade_pnl, daily_pnl, equity):
        pd.DataFrame(
            [
                [
                    symbol,
                    day,
                    datetime.fromtimestamp(entry_bar["t"] / 1000).strftime("%H:%M"),
                    signal,
                    trade_pnl,
                    daily_pnl,
                    equity,
                ]
            ],
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

    def export_leaderboard(self):
        leaderboard = []
        for strategy, results in self.results_summary.items():
            for sym, s in results.items():
                leaderboard.append(
                    {
                        "Strategy": strategy.upper(),
                        "Symbol": sym,
                        "Trades": s["trades"],
                        "WinRate %": round(s["win_rate"] * 100, 2),
                        "AvgDaily PnL": round(s["avg_daily"], 2),
                        "Total PnL": round(s["total_pnl"], 2),
                        "Final Equity": round(s["final_equity"], 2),
                        "Sharpe": round(s["sharpe"], 2),
                        "Blocked": s["blocked_trades"],
                        "Blocked %": round(s["blocked_pct"], 2),
                    }
                )

        df = pd.DataFrame(leaderboard)

        if not df.empty and "Sharpe" in df.columns:
            df = df.sort_values(by="Sharpe", ascending=False)

        # Excel export
        excel_file = os.path.join(self.reports_dir, "strategy_leaderboard.xlsx")
        with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Leaderboard", index=False)
            workbook, worksheet = writer.book, writer.sheets["Leaderboard"]

            if not df.empty:
                sharpe_col = df.columns.get_loc("Sharpe")
                nrows = len(df) + 1
                col_letter = chr(65 + sharpe_col)

                worksheet.conditional_format(
                    f"{col_letter}2:{col_letter}{nrows}",
                    {
                        "type": "3_color_scale",
                        "min_color": "#F8696B",
                        "mid_color": "#FFEB84",
                        "max_color": "#63BE7B",
                    },
                )

            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)

        # HTML export
        def color_sharpe(val):
            if val > 1:
                return "color: green; font-weight: bold;"
            elif val >= 0:
                return "color: orange; font-weight: bold;"
            else:
                return "color: red; font-weight: bold;"

        if not df.empty:
            styled = df.style.map(color_sharpe, subset=["Sharpe"])
            html_file = os.path.join(self.reports_dir, "strategy_leaderboard.html")
            styled.to_html(html_file)
        else:
            html_file = os.path.join(self.reports_dir, "strategy_leaderboard.html")
            with open(html_file, "w") as f:
                f.write("<h2>No trades executed — empty leaderboard.</h2>")

        print(f"\n🏆 Strategy leaderboard saved to:\n- {excel_file}\n- {html_file}")

    def _plot_equity(self, symbol, equity_curve, strategy):
        plt.figure(figsize=(10, 5))
        plt.plot(equity_curve, label=f"{symbol} Equity")
        plt.title(f"{strategy.upper()} Equity Curve – {symbol}")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.reports_dir, f"{symbol}_{strategy}_equity.png"))
        plt.close()

    def _plot_drawdown(self, symbol, equity_curve, strategy):
        rolling_max = [max(equity_curve[: i + 1]) for i in range(len(equity_curve))]
        drawdowns = [rm - x for rm, x in zip(rolling_max, equity_curve)]
        plt.figure(figsize=(10, 3))
        plt.plot(drawdowns, color="red", label=f"{symbol} DD")
        plt.title(f"{strategy.upper()} Drawdown – {symbol}")
        plt.legend()
        plt.grid(True)
        plt.savefig(os.path.join(self.reports_dir, f"{symbol}_{strategy}_drawdown.png"))
        plt.close()

    def print_summary(self):
        print("\n=== MULTI-STRATEGY SUMMARY ===")
        for strategy, results in self.results_summary.items():
            print(f"\n📌 Strategy: {strategy.upper()}")
            print(
                f"{'Symbol':<8}{'Trades':<8}{'WinRate':<10}{'AvgDaily':<12}"
                f"{'PnL':<12}{'Equity':<12}{'Sharpe':<8}{'Blocked':<10}{'Blocked %':<10}"
            )
            for sym, s in results.items():
                print(
                    f"{sym:<8}{s['trades']:<8}"
                    f"{s['win_rate']*100:>8.1f}%   "
                    f"{s['avg_daily']:<12.2f}{s['total_pnl']:<12.2f}"
                    f"{s['final_equity']:<12.2f}{s['sharpe']:<8.2f}"
                    f"{s['blocked_trades']:<10}{s['blocked_pct']:<10.2f}"
                )


# ==========================================================
# Run
# ==========================================================
if __name__ == "__main__":
    cfg = load_config()
    symbols = cfg.get("universe", {}).get("Core_Stocks", [])[:3]

    strategies = {
        "breakout": breakout_intraday,
        "ma": moving_average_signal,
        "rsi": rsi_signal,
        "bollinger": bollinger_bands_signal,
        "macd": macd_signal,
        "vwap": vwap_signal,
    }
    strategies = {k: v for k, v in strategies.items() if v}

    backtester = IntradayBacktester(symbols, days=5, strategies=strategies)
    backtester.run()
