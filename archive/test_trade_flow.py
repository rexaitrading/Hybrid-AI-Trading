"""
Quant Test Harness for Hybrid AI Trading System (Report Generator v4.0)
-----------------------------------------------------------------------
- Simulates trades with PnL applied to PortfolioTracker
- Tracks Kelly raw vs capped sizing
- Saves equity curve, drawdowns, PnL histogram, Kelly fraction trend
- Writes a text summary of performance into reports/
"""

import os, sys, yaml, random
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# 🔑 Ensure src/ is on Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from hybrid_ai_trading.trade_engine import TradeEngine


def simulate_trades(engine, n_trades=50, seed=42):
    """Simulate trades with random PnL outcomes and update portfolio equity."""
    random.seed(seed)

    equity_history, pnl_history, kelly_frac_history = [], [], []

    for i in range(n_trades):
        # Random PnL: ~55% win rate, wins bigger than losses
        if random.random() < 0.55:
            pnl = random.uniform(100, 600)  # win
        else:
            pnl = -random.uniform(50, 300)  # loss

        # Execute trade
        result = engine.process_signal("BTC/USDT", "BUY", size=1, price=60000)

        # Apply PnL to portfolio equity
        engine.portfolio.equity += pnl

        # Record outcome
        engine.record_trade_outcome(pnl=pnl)

        # Track history
        equity = engine.get_equity()
        equity_history.append(equity)
        pnl_history.append(pnl)
        kelly_frac_history.append(engine.kelly_sizer.fraction if engine.kelly_sizer else 0)

        # Print console log
        print(
            f"Trade {i+1:02d}: PnL={pnl:+.2f} | Equity={equity:.2f} | "
            f"WinRate={engine.performance_tracker.win_rate():.2f} | "
            f"Payoff={engine.performance_tracker.payoff_ratio():.2f} | "
            f"Kelly fraction={kelly_frac_history[-1]:.2f}"
        )
        print("   Result:", result)

    return equity_history, pnl_history, kelly_frac_history


def performance_summary(engine, equity_history, pnl_history, kelly_frac_history):
    """Return summary metrics as dict."""
    pt = engine.performance_tracker
    wr = pt.win_rate()
    pr = pt.payoff_ratio()
    sharpe = pt.sharpe_ratio()
    sortino = pt.sortino_ratio()
    dd = pt.get_drawdown()

    start_eq, end_eq = equity_history[0], equity_history[-1]
    total_return = (end_eq - start_eq) / start_eq
    cagr = (1 + total_return) ** (252 / len(equity_history)) - 1 if len(equity_history) > 0 else 0

    return {
        "Start Equity": start_eq,
        "Final Equity": end_eq,
        "Total Return %": total_return * 100,
        "CAGR %": cagr * 100,
        "Win Rate": wr,
        "Payoff Ratio": pr,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Max Drawdown %": dd * 100,
        "Final Kelly Frac": kelly_frac_history[-1],
    }


def save_report(equity_history, pnl_history, kelly_frac_history, summary):
    """Save charts + text summary into reports/ folder."""
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Save equity curve with drawdowns ---
    plt.figure(figsize=(14, 10))

    trades = range(1, len(equity_history) + 1)
    peak = np.maximum.accumulate(equity_history)

    plt.subplot(3, 1, 1)
    plt.plot(trades, equity_history, label="Equity Curve", linewidth=2, color="blue")
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
    plt.title("Equity Curve with Drawdowns", fontsize=14)
    plt.xlabel("Trades")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.7)

    # --- PnL distribution ---
    plt.subplot(3, 2, 3)
    plt.hist(pnl_history, bins=20, color="purple", alpha=0.7)
    plt.title("PnL Distribution", fontsize=12)
    plt.xlabel("PnL per Trade")
    plt.ylabel("Frequency")

    # --- Kelly fraction trend ---
    plt.subplot(3, 2, 4)
    plt.plot(trades, kelly_frac_history, color="green", linewidth=2)
    plt.title("Kelly Fraction Evolution", fontsize=12)
    plt.xlabel("Trades")
    plt.ylabel("Fraction")

    plt.tight_layout()
    chart_path = os.path.join(reports_dir, f"quant_report_{timestamp}.png")
    plt.savefig(chart_path)
    plt.close()

    # --- Save text summary ---
    text_path = os.path.join(reports_dir, f"quant_report_{timestamp}.txt")
    with open(text_path, "w") as f:
        f.write("=== Quant Performance Report ===\n")
        for k, v in summary.items():
            if isinstance(v, float):
                f.write(f"{k:<18}: {v:.2f}\n")
            else:
                f.write(f"{k:<18}: {v}\n")
        f.write("===============================\n")

    print(f"\n✅ Quant report saved to:\n  {chart_path}\n  {text_path}")


def main():
    # Load config
    with open("config.yaml", "r", encoding="utf-8-sig") as f:
        cfg = yaml.safe_load(f)

    # Init engine
    engine = TradeEngine(cfg)

    # Simulate trades
    equity_history, pnl_history, kelly_frac_history = simulate_trades(engine, n_trades=50)

    # Report metrics
    summary = performance_summary(engine, equity_history, pnl_history, kelly_frac_history)

    # Save report
    save_report(equity_history, pnl_history, kelly_frac_history, summary)


if __name__ == "__main__":
    main()
