"""
rebalance_engine.py
--------------------------------
Professional Quant-Grade Rebalancing Engine
Upgrades included (Step 1 - Step 8):
1. Config-driven broker/exchange setup
2. Normalize balances to USD-equivalent
3. Precision & lot size handling
4. Risk management layer
5. Multi-portfolio support (Sharpe, MinVol, Custom)
6. Dry-run mode for safe testing
7. Logging & audit trail
8. Direct integration with execution.py
"""

import os
import json
import yaml
import ccxt
import pandas as pd
from datetime import datetime

# --- Load Config ---
with open("portfolio_config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

# --- Flags ---
DRY_RUN = cfg.get("dry_run", True)
MAX_DAILY_SHIFT = cfg.get("max_daily_shift", 0.2)  # never move more than 20% of equity

# --- Broker Setup ---
def connect_exchanges():
    exchanges = {}
    if "binance" in cfg["brokers"]:
        exchanges["binance"] = ccxt.binance({
            "apiKey": os.getenv("BINANCE_KEY"),
            "secret": os.getenv("BINANCE_SECRET")
        })
    if "bybit" in cfg["brokers"]:
        exchanges["bybit"] = ccxt.bybit({
            "apiKey": os.getenv("BYBIT_KEY"),
            "secret": os.getenv("BYBIT_SECRET")
        })
    # TODO: Add IBKR + Coinbase adapters
    return exchanges

# --- Load Portfolio Targets ---
def load_target_portfolio():
    # Choose between multiple optimized portfolios
    choice = cfg.get("portfolio_choice", "sharpe")  # options: sharpe, minvol, custom
    if choice == "custom":
        return pd.DataFrame(cfg["custom_weights"].items(), columns=["Ticker", "Weight"])
    else:
        fname = f"optimal_portfolio_{choice}.csv" if choice != "sharpe" else "optimal_portfolio.csv"
        return pd.read_csv(fname)

# --- Normalize Balances ---
def fetch_all_balances(exchanges):
    balances = {}
    for name, ex in exchanges.items():
        try:
            bal = ex.fetch_balance()
            for asset, data in bal["total"].items():
                if data and data > 0:
                    price = 1
                    if asset not in ["USDT", "USD"]:
                        try:
                            price = ex.fetch_ticker(f"{asset}/USDT")["last"]
                        except Exception:
                            price = 0
                    usd_value = float(data) * price
                    balances[asset] = balances.get(asset, 0) + usd_value
        except Exception as e:
            print(f"[{name}] Balance fetch failed:", e)
    return balances

# --- Apply Risk Management ---
def cap_orders(order_queue, total_equity):
    capped = []
    max_shift_usd = total_equity * MAX_DAILY_SHIFT
    for o in order_queue:
        if abs(o["notional"]) > max_shift_usd:
            print(f"⚠️ Order for {o['symbol']} capped from {o['notional']} to {max_shift_usd}")
            o["notional"] = max_shift_usd * (1 if o["notional"] > 0 else -1)
        capped.append(o)
    return capped

# --- Precision Handling ---
def adjust_for_precision(exchange, symbol, amount):
    try:
        market = exchange.market(symbol)
        step = market["limits"]["amount"]["min"] or 0.001
        precision = market["precision"]["amount"]
        adjusted = round(max(amount, step), precision)
        return adjusted
    except Exception:
        return amount

# --- Main Rebalancing ---
def rebalance():
    exchanges = connect_exchanges()
    targets = load_target_portfolio()
    balances = fetch_all_balances(exchanges)

    total_equity = sum(balances.values())
    print("Total Equity (USD):", round(total_equity, 2))

    order_queue = []
    for _, row in targets.iterrows():
        ticker = row["Ticker"]
        target_pct = row["Weight"] / 100
        target_usd = total_equity * target_pct
        current_usd = balances.get(ticker.replace("/USDT", ""), 0)
        diff = target_usd - current_usd

        if abs(diff) / total_equity < 0.01:
            continue  # skip small adjustments

        order = {
            "symbol": ticker,
            "target_pct": round(target_pct * 100, 2),
            "target_usd": round(target_usd, 2),
            "current_usd": round(current_usd, 2),
            "notional": round(diff, 2),
            "side": "buy" if diff > 0 else "sell",
            "timestamp": datetime.utcnow().isoformat()
        }
        order_queue.append(order)

    # --- Risk Cap ---
    order_queue = cap_orders(order_queue, total_equity)

    # --- Precision Fix ---
    for o in order_queue:
        if "binance" in exchanges:
            amt = o["notional"] / exchanges["binance"].fetch_ticker(o["symbol"])["last"]
            o["amount_adj"] = adjust_for_precision(exchanges["binance"], o["symbol"], amt)

    # --- Save Queue ---
    with open("order_queue.json", "w") as f:
        json.dump(order_queue, f, indent=2)

    # --- Logging ---
    log_entry = pd.DataFrame(order_queue)
    log_entry["equity"] = total_equity
    log_entry.to_csv("rebalance_log.csv", mode="a", header=not os.path.exists("rebalance_log.csv"), index=False)

    print("✅ Rebalance completed. Orders saved to order_queue.json + rebalance_log.csv")

    # --- Dry Run / Execution ---
    if not DRY_RUN:
        os.system("python execution.py")  # triggers execution pipeline


if __name__ == "__main__":
    rebalance()
