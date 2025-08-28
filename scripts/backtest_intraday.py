import os, requests, csv, math
from dotenv import load_dotenv
from datetime import datetime, timedelta
import statistics as stats
import matplotlib.pyplot as plt

load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY")

# === CONFIG ===
START_CAPITAL = 100000   # total portfolio starting capital (USD)
CAPITAL_PER_TRADE = 10000  # how much to allocate per trade
LEVERAGE = 2             # multiplier for exposure

def get_intraday_bars(ticker, start, end, interval="1", timespan="minute"):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{interval}/{timespan}/{start}/{end}?limit=5000&apiKey={POLYGON_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error fetching {ticker}: {resp.text[:200]}")
        return []
    return resp.json().get("results", [])

def breakout_strategy(bars):
    if len(bars) < 3:
        return "HOLD"
    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]

    recent_close = closes[-1]
    prev_high = max(highs[:-1])
    prev_low = min(lows[:-1])

    if recent_close > prev_high:
        return "BUY"
    elif recent_close < prev_low:
        return "SELL"
    return "HOLD"

def calc_trade_pnl(signal, entry_bar, exit_bar, capital, leverage):
    """Return $ profit/loss given signal, price move, capital & leverage"""
    entry_price = entry_bar["c"]
    exit_price = exit_bar["c"]

    position_size = (capital * leverage) / entry_price  # number of shares/contracts
    if signal == "BUY":
        return (exit_price - entry_price) * position_size
    elif signal == "SELL":
        return (entry_price - exit_price) * position_size
    return 0

def run_intraday_backtest(symbols, days=5):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    os.makedirs("logs", exist_ok=True)
    logfile = "logs/intraday_backtest_multi.csv"

    portfolio_curve = []
    portfolio_daily = []
    portfolio_wins, portfolio_losses = 0, 0
    portfolio_cum = 0

    with open(logfile, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["symbol","date","time","signal","trade_pnl","daily_pnl","cum_pnl"]
        )
        writer.writeheader()

        summary = {}

        for symbol in symbols:
            cum_pnl = 0.0
            daily_returns = []
            wins, losses = 0, 0
            peak, max_dd = 0, 0
            equity_curve = []

            print(f"\n=== Backtesting {symbol} ===")

            for i in range(days):
                day = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                bars = get_intraday_bars(symbol, day, day)
                if not bars:
                    continue

                daily_pnl = 0.0
                for j in range(2, len(bars)-1):
                    window = bars[j-2:j+1]
                    signal = breakout_strategy(window)

                    entry_bar = bars[j]
                    exit_bar = bars[j+1]
                    trade_pnl = calc_trade_pnl(signal, entry_bar, exit_bar, CAPITAL_PER_TRADE, LEVERAGE)

                    daily_pnl += trade_pnl
                    cum_pnl += trade_pnl
                    equity_curve.append(cum_pnl)

                    # portfolio merge
                    if len(portfolio_curve) < len(equity_curve):
                        portfolio_curve.append(0)
                    portfolio_curve[len(equity_curve)-1] += trade_pnl
                    portfolio_cum += trade_pnl

                    if trade_pnl > 0: 
                        wins += 1
                        portfolio_wins += 1
                    elif trade_pnl < 0: 
                        losses += 1
                        portfolio_losses += 1

                    peak = max(peak, cum_pnl)
                    dd = peak - cum_pnl
                    max_dd = max(max_dd, dd)

                    writer.writerow({
                        "symbol": symbol,
                        "date": day,
                        "time": datetime.fromtimestamp(entry_bar["t"]/1000).strftime("%H:%M"),
                        "signal": signal,
                        "trade_pnl": trade_pnl,
                        "daily_pnl": daily_pnl,
                        "cum_pnl": cum_pnl
                    })

                    # stop rules (scaled to $ capital_per_trade)
                    if daily_pnl <= -0.03 * CAPITAL_PER_TRADE:
                        print(f"{symbol} {day}: stopped trading at -3% daily loss")
                        break
                    if daily_pnl >= 0.01 * CAPITAL_PER_TRADE:
                        print(f"{symbol} {day}: locked day at +1% profit")
                        break

                daily_returns.append(daily_pnl)

            avg_daily = stats.mean(daily_returns) if daily_returns else 0
            stdev = stats.stdev(daily_returns) if len(daily_returns) > 1 else 0
            sharpe = (avg_daily / stdev) * math.sqrt(252) if stdev > 0 else 0
            win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

            summary[symbol] = {
                "trades": wins + losses,
                "win_rate": win_rate,
                "avg_daily": avg_daily,
                "total_pnl": cum_pnl,
                "max_dd": max_dd,
                "sharpe": sharpe
            }

            print(f"Finished {days} days for {symbol}. "
                  f"Total PnL: ${cum_pnl:,.2f}, MaxDD: ${max_dd:,.2f}, Sharpe: {sharpe:.2f}")

            # plots per symbol
            if equity_curve:
                plt.figure(figsize=(10,5))
                plt.plot(equity_curve, label=f"{symbol} Equity Curve")
                plt.title(f"Equity Curve for {symbol}")
                plt.xlabel("Trades")
                plt.ylabel("PnL ($)")
                plt.legend()
                plt.grid(True)
                plt.savefig(f"logs/{symbol}_equity_curve.png")
                plt.close()

                drawdowns = [max(0, max(equity_curve[:i+1]) - x) for i,x in enumerate(equity_curve)]
                plt.figure(figsize=(10,3))
                plt.plot(drawdowns, color="red", label=f"{symbol} Drawdown")
                plt.title(f"Drawdown for {symbol}")
                plt.xlabel("Trades")
                plt.ylabel("Drawdown ($)")
                plt.legend()
                plt.grid(True)
                plt.savefig(f"logs/{symbol}_drawdown.png")
                plt.close()

        # portfolio stats
        portfolio_avg = stats.mean(portfolio_daily) if portfolio_daily else 0
        stdev = stats.stdev(portfolio_daily) if len(portfolio_daily) > 1 else 0
        sharpe = (portfolio_avg / stdev) * math.sqrt(252) if stdev > 0 else 0
        portfolio_winrate = portfolio_wins / (portfolio_wins + portfolio_losses) if (portfolio_wins+portfolio_losses)>0 else 0
        total_pnl = portfolio_cum
        peak, max_dd = 0, 0
        cum = 0
        for x in portfolio_daily:
            cum += x
            peak = max(peak, cum)
            max_dd = max(max_dd, peak - cum)

        # portfolio plots
        if portfolio_curve:
            plt.figure(figsize=(10,5))
            plt.plot(portfolio_curve, label="Portfolio Equity Curve", color="blue")
            plt.title("Combined Portfolio Equity Curve")
            plt.xlabel("Trades (across all symbols)")
            plt.ylabel("PnL ($)")
            plt.legend()
            plt.grid(True)
            plt.savefig("logs/portfolio_equity_curve.png")
            plt.close()

            drawdowns = [max(0, max(portfolio_curve[:i+1]) - x) for i,x in enumerate(portfolio_curve)]
            plt.figure(figsize=(10,3))
            plt.plot(drawdowns, color="red", label="Portfolio Drawdown")
            plt.title("Combined Portfolio Drawdown")
            plt.xlabel("Trades")
            plt.ylabel("Drawdown ($)")
            plt.legend()
            plt.grid(True)
            plt.savefig("logs/portfolio_drawdown.png")
            plt.close()

        # console summary
        print("\n=== SUMMARY TABLE ===")
        print(f"{'Symbol':<8} {'Trades':<8} {'WinRate':<10} {'AvgDaily($)':<12} {'TotalPnL($)':<12} {'Sharpe':<8} {'MaxDD($)':<8}")
        for sym, stats_dict in summary.items():
            print(f"{sym:<8} "
                  f"{stats_dict['trades']:<8} "
                  f"{stats_dict['win_rate']:.1%:<10} "
                  f"${stats_dict['avg_daily']:<12.2f} "
                  f"${stats_dict['total_pnl']:<12.2f} "
                  f"{stats_dict['sharpe']:.2f:<8} "
                  f"${stats_dict['max_dd']:<8.2f}")
        print(f"\nPORTFOLIO "
              f"{portfolio_wins+portfolio_losses:<8} "
              f"{portfolio_winrate:.1%:<10} "
              f"${portfolio_avg:<12.2f} "
              f"${total_pnl:<12.2f} "
              f"{sharpe:.2f:<8} "
              f"${max_dd:<8.2f}")

if __name__ == "__main__":
    symbols = ["AAPL", "TSLA", "NVDA", "EURUSD", "BTCUSD"]
    run_intraday_backtest(symbols, days=5)
