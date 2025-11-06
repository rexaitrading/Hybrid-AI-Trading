"""
Quant Report Generator (Hybrid AI Quant Pro v1.0 Ã¢â‚¬â€œ Research Tool)
-----------------------------------------------------------------
- Simulates trades with random PnL outcomes
- Tracks equity curve, drawdowns, Kelly fraction trend
- Saves chart + text summary into reports/
"""

import os
import random
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import yaml

# Ensure src/ is on Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from hybrid_ai_trading.trade_engine import TradeEngine


def simulate_trades(engine, n_trades=50, seed=42):
    """Simulate trades with random PnL outcomes and update portfolio equity."""
    random.seed(seed)

    equity_history, pnl_history, kelly_frac_history = [], [], []

    for i in range(n_trades):
        # Random PnL outcome
        pnl = (
            random.uniform(100, 600)
            if random.random() < 0.55
            else -random.uniform(50, 300)
        )

        # Execute trade
        result = engine.process_signal("BTC/USDT", "BUY", size=1, price=60000)

        # Apply PnL manually (exploratory mode)
        engine.portfolio.equity += pnl
        engine.performance_tracker.record_trade(pnl)

        equity_history.append(engine.get_equity())
        pnl_history.append(pnl)
        kelly_frac_history.append(
            engine.kelly_sizer.fraction if engine.kelly_sizer else 0
        )

        print(
            f"Trade {i+1:02d}: PnL={pnl:+.2f} | Equity={equity_history[-1]:.2f} | "
            f"Kelly fraction={kelly_frac_history[-1]:.2f}"
        )
        print("   Result:", result)

    return equity_history, pnl_history, kelly_frac_history


def performance_summary(engine, equity_history, pnl_history, kelly_frac_history):
    pt = engine.performance_tracker
    start_eq, end_eq = equity_history[0], equity_history[-1]
    total_return = (end_eq - start_eq) / start_eq
    cagr = (
        (1 + total_return) ** (252 / len(equity_history)) - 1 if equity_history else 0
    )

    return {
        "Start Equity": start_eq,
        "Final Equity": end_eq,
        "Total Return %": total_return * 100,
        "CAGR %": cagr * 100,
        "Win Rate": pt.win_rate(),
        "Payoff Ratio": pt.payoff_ratio(),
        "Sharpe Ratio": pt.sharpe_ratio(),
        "Sortino Ratio": pt.sortino_ratio(),
        "Max Drawdown %": pt.get_drawdown() * 100,
        "Final Kelly Frac": kelly_frac_history[-1] if kelly_frac_history else 0,
    }


def save_report(equity_history, pnl_history, kelly_frac_history, summary):
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Equity curve chart
    plt.figure(figsize=(12, 8))
    trades = range(1, len(equity_history) + 1)
    peak = np.maximum.accumulate(equity_history)
    plt.plot(trades, equity_history, label="Equity Curve", color="blue")
    dd = (peak - np.array(equity_history)) / peak
    plt.fill_between(
        trades,
        equity_history,
        peak,
        where=equity_history < peak,
        color="red",
        alpha=0.3,
        label="Drawdowns",
    )
    plt.title("Equity Curve with Drawdowns")
    plt.xlabel("Trades")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)
    chart_path = os.path.join(reports_dir, f"quant_report_{timestamp}.png")
    plt.savefig(chart_path)
    plt.close()

    # Text summary
    text_path = os.path.join(reports_dir, f"quant_report_{timestamp}.txt")
    with open(text_path, "w") as f:
        f.write("=== Quant Performance Report ===\n")
        for k, v in summary.items():
            f.write(
                f"{k:<18}: {v:.2f}\n" if isinstance(v, float) else f"{k:<18}: {v}\n"
            )
        f.write("===============================\n")

    print(f"\nÃ¢Å“â€¦ Quant report saved to:\n  {chart_path}\n  {text_path}")


def main():
    with open("config/config.yaml", "r", encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)

    engine = TradeEngine(cfg)
    equity_history, pnl_history, kelly_frac_history = simulate_trades(
        engine, n_trades=50
    )
    summary = performance_summary(
        engine, equity_history, pnl_history, kelly_frac_history
    )
    save_report(equity_history, pnl_history, kelly_frac_history, summary)


if __name__ == "__main__":
    main()
