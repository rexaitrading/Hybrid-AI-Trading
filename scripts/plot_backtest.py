import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_equity_curve(filepath="logs/backtest_results.csv"):
    df = pd.read_csv(filepath)

    for symbol, group in df.groupby("symbol"):
        group["date"] = pd.to_datetime(group["date"])
        group = group.sort_values("date")

        # Equity curve
        plt.figure(figsize=(10, 5))
        plt.plot(group["date"], group["cum_pnl"], label=f"{symbol} Equity Curve")
        plt.title(f"Equity Curve for {symbol}")
        plt.xlabel("Date")
        plt.ylabel("Cumulative PnL (%)")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"logs/{symbol}_equity_curve.png")
        plt.close()

        # Drawdown
        rolling_max = group["cum_pnl"].cummax()
        drawdown = group["cum_pnl"] - rolling_max

        plt.figure(figsize=(10, 3))
        plt.plot(group["date"], drawdown, color="red", label=f"{symbol} Drawdown")
        plt.title(f"Drawdown for {symbol}")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"logs/{symbol}_drawdown.png")
        plt.close()

        print(f"✅ Saved plots for {symbol} in logs/")


def plot_portfolio(filepath="logs/backtest_results.csv"):
    """Plot all symbols’ equity curves on one chart, plus portfolio-level curve."""
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])

    # Multi-symbol comparison
    plt.figure(figsize=(12, 6))
    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("date")
        plt.plot(group["date"], group["cum_pnl"], label=symbol)

    plt.title("Equity Curves: Multi-Symbol Comparison")
    plt.xlabel("Date")
    plt.ylabel("Cumulative PnL (%)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("logs/portfolio_equity_curves.png")
    plt.close()
    print("✅ Saved combined portfolio chart as logs/portfolio_equity_curves.png")

    # Portfolio aggregate PnL (equal weight across all symbols)
    pivot = df.pivot(index="date", columns="symbol", values="cum_pnl").fillna(method="ffill")
    portfolio_curve = pivot.mean(axis=1)

    plt.figure(figsize=(12, 6))
    plt.plot(pd.to_datetime(portfolio_curve.index), portfolio_curve, color="blue", linewidth=2, label="Portfolio (Equal Weight)")
    plt.title("Portfolio Equity Curve (All Symbols Combined)")
    plt.xlabel("Date")
    plt.ylabel("Cumulative PnL (%)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("logs/portfolio_total_equity.png")
    plt.close()
    print("✅ Saved portfolio total equity curve as logs/portfolio_total_equity.png")


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    plot_equity_curve()
    plot_portfolio()
