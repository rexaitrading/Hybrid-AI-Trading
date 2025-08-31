import os
import ccxt
import yaml
import pandas as pd
from datetime import datetime

# ==============================
# Load Config
# ==============================
with open("portfolio_config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

BROKERS = cfg.get("brokers", ["binance"])
DRY_RUN = cfg.get("dry_run", True)
ORDER_TYPE = cfg.get("order_type", "market")
SLIPPAGE = cfg.get("slippage", 0.001)
MAX_DAILY_SHIFT = cfg.get("max_daily_shift", 0.2)
MAX_DRAWDOWN = cfg.get("max_drawdown", 0.25)
ALERTS = cfg.get("alerts", {})
STRESS_SCENARIOS = cfg.get("stress_scenarios", [])

print(f"Execution config loaded | Brokers={BROKERS}, DryRun={DRY_RUN}, OrderType={ORDER_TYPE}")

# ==============================
# Broker Abstraction
# ==============================
def connect_broker(name):
    if name == "binance":
        return ccxt.binance()
    elif name == "bybit":
        return ccxt.bybit()
    # elif name == "ibkr":  # Future support
    #     return connect_ibkr()
    else:
        raise ValueError(f"Unsupported broker: {name}")

brokers = {b: connect_broker(b) for b in BROKERS}

# ==============================
# Trade Logger
# ==============================
LOG_FILE = "trade_log.csv"
if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["datetime","broker","symbol","side","qty","price","slippage","pnl"]).to_csv(LOG_FILE, index=False)

def log_trade(broker, symbol, side, qty, price, slippage, pnl=0):
    entry = {
        "datetime": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "broker": broker,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "slippage": slippage,
        "pnl": pnl
    }
    df = pd.DataFrame([entry])
    df.to_csv(LOG_FILE, mode="a", header=False, index=False)
    print(f"Trade logged: {entry}")

# ==============================
# Risk Management
# ==============================
def check_risk(current_dd, shift_fraction):
    if current_dd < -MAX_DRAWDOWN:
        raise Exception(f"❌ Max drawdown exceeded ({current_dd:.2%}). Blocked trades.")
    if shift_fraction > MAX_DAILY_SHIFT:
        raise Exception(f"❌ Shift {shift_fraction:.2%} exceeds max_daily_shift {MAX_DAILY_SHIFT:.2%}.")

# ==============================
# Stress Testing
# ==============================
def run_stress_test(weights):
    impacts = []
    for scenario in STRESS_SCENARIOS:
        name = scenario["name"]
        shock = scenario["shock"]
        impact = sum(weights.get(asset,0) * change for asset, change in shock.items())
        impacts.append({"Scenario": name, "Impact": impact})
    return pd.DataFrame(impacts)

# ==============================
# Order Execution
# ==============================
def execute_order(broker_name, symbol, side, qty, price=None):
    broker = brokers[broker_name]
    simulated_price = price * (1 + SLIPPAGE) if price else None

    if DRY_RUN:
        print(f"[DRY-RUN] {side} {qty} {symbol} @ {simulated_price:.4f}")
        log_trade(broker_name, symbol, side, qty, simulated_price or 0, SLIPPAGE)
        return simulated_price

    try:
        if ORDER_TYPE == "market":
            order = broker.create_market_order(symbol, side, qty)
        elif ORDER_TYPE == "limit":
            if price is None:
                raise ValueError("Limit order requires a price.")
            order = broker.create_limit_order(symbol, side, qty, price)
        else:
            raise ValueError(f"Unsupported order type: {ORDER_TYPE}")

        log_trade(broker_name, symbol, side, qty, order.get("price", price), SLIPPAGE)
        return order
    except Exception as e:
        with open("execution_errors.log","a") as errfile:
            errfile.write(f"{datetime.utcnow()} | {symbol} | {str(e)}\n")
        print(f"⚠️ Execution error for {symbol}: {e}")
        return None

# ==============================
# Example Run
# ==============================
if __name__ == "__main__":
    # Example portfolio rebalance weights
    new_weights = {"BTC/USDT": 0.4, "ETH/USDT": 0.2, "SPY": 0.3, "GLD": 0.1}
    stress_df = run_stress_test(new_weights)
    print("\nStress Test Before Execution:\n", stress_df)

    # Simulated execution loop
    for sym, w in new_weights.items():
        execute_order("binance", sym, "buy", qty=0.1, price=20000)  # Example qty/price

if __name__ == "__main__":
    import json
    with open("latest_weights.json","r") as f:
        new_weights = json.load(f)

    stress_df = run_stress_test(new_weights)
    print("\nStress Test Before Execution:\n", stress_df)

    # Example execution loop
    for sym, w in new_weights.items():
        # Replace qty logic with your actual portfolio sizing model
        execute_order("binance", sym, "buy", qty=0.1, price=20000)
