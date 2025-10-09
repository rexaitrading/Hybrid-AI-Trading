import pandas as pd


def summarize_backtest(filepath="logs/backtest_results.csv"):
    df = pd.read_csv(filepath)

    results = []
    for symbol, group in df.groupby("symbol"):
        trades = group[group["trade_return"] != 0]
        total_trades = len(trades)
        if total_trades == 0:
            continue

        wins = trades[trades["trade_return"] > 0]
        losses = trades[trades["trade_return"] <= 0]
        win_rate = len(wins) / total_trades * 100
        avg_return = trades["trade_return"].mean() * 100
        total_pnl = trades["trade_return"].sum() * 100
        max_drawdown = group["cum_pnl"].min() * 100
        sharpe = (
            (trades["trade_return"].mean() / trades["trade_return"].std()) * (252**0.5)
            if trades["trade_return"].std() > 0
            else 0
        )

        results.append(
            {
                "Symbol": symbol,
                "Trades": total_trades,
                "WinRate%": round(win_rate, 2),
                "AvgReturn%": round(avg_return, 2),
                "TotalPnL%": round(total_pnl, 2),
                "MaxDD%": round(max_drawdown, 2),
                "Sharpe": round(sharpe, 2),
            }
        )

    return pd.DataFrame(results)


if __name__ == "__main__":
    summary = summarize_backtest()
    print("\n=== Backtest Summary ===")
    print(summary.to_string(index=False))
