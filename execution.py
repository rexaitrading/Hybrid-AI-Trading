"""
Execution Engine (Hybrid AI Quant Pro v4.0 â€“ AAA Hedge-Fund Grade)
==================================================================
Provides broker abstraction, trade logging, risk checks, stress testing,
and order execution for portfolio trades.

- Config-driven from portfolio_config.yaml
- Dry-run mode for simulation vs live trading
- Structured trade logging (CSV)
- Risk guardrails (drawdown, shift limits)
- Stress testing scenarios
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import ccxt
import pandas as pd
import yaml

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------
logger = logging.getLogger("hybrid_ai_trading.execution")
logger.setLevel(logging.INFO)

# ----------------------------------------------------------------------
# Load Config
# ----------------------------------------------------------------------
CONFIG_FILE = "portfolio_config.yaml"
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

BROKERS = cfg.get("brokers", ["binance"])
DRY_RUN = cfg.get("dry_run", True)
ORDER_TYPE = cfg.get("order_type", "market")
SLIPPAGE = cfg.get("slippage", 0.001)
MAX_DAILY_SHIFT = cfg.get("max_daily_shift", 0.2)
MAX_DRAWDOWN = cfg.get("max_drawdown", 0.25)
ALERTS = cfg.get("alerts", {})
STRESS_SCENARIOS = cfg.get("stress_scenarios", [])

logger.info(
    "Execution config loaded | Brokers=%s, DryRun=%s, OrderType=%s",
    BROKERS,
    DRY_RUN,
    ORDER_TYPE,
)


# ----------------------------------------------------------------------
# Broker Abstraction
# ----------------------------------------------------------------------
def connect_broker(name: str) -> Any:
    """Return ccxt broker client by name."""
    if name == "binance":
        return ccxt.binance()
    if name == "bybit":
        return ccxt.bybit()
    # elif name == "ibkr":  # Future support
    #     return connect_ibkr()
    raise ValueError(f"Unsupported broker: {name}")


brokers: Dict[str, Any] = {b: connect_broker(b) for b in BROKERS}

# ----------------------------------------------------------------------
# Trade Logger
# ----------------------------------------------------------------------
LOG_FILE = "trade_log.csv"
if not os.path.exists(LOG_FILE):
    pd.DataFrame(
        columns=[
            "datetime",
            "broker",
            "symbol",
            "side",
            "qty",
            "price",
            "slippage",
            "pnl",
        ]
    ).to_csv(LOG_FILE, index=False)


def log_trade(
    broker: str,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    slippage: float,
    pnl: float = 0.0,
) -> None:
    """Append executed trade details to log file."""
    entry = {
        "datetime": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "broker": broker,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": price,
        "slippage": slippage,
        "pnl": pnl,
    }
    df = pd.DataFrame([entry])
    df.to_csv(LOG_FILE, mode="a", header=False, index=False)
    logger.info("Trade logged: %s", entry)


# ----------------------------------------------------------------------
# Risk Management
# ----------------------------------------------------------------------
def check_risk(current_dd: float, shift_fraction: float) -> None:
    """
    Raise exception if drawdown or daily shift thresholds breached.
    Args:
        current_dd: current portfolio drawdown (negative fraction)
        shift_fraction: fraction of portfolio shifted today
    """
    if current_dd < -MAX_DRAWDOWN:
        raise RuntimeError(
            f"âŒ Max drawdown exceeded ({current_dd:.2%}). Blocked trades."
        )
    if shift_fraction > MAX_DAILY_SHIFT:
        raise RuntimeError(
            f"âŒ Shift {shift_fraction:.2%} exceeds max_daily_shift "
            f"{MAX_DAILY_SHIFT:.2%}."
        )


# ----------------------------------------------------------------------
# Stress Testing
# ----------------------------------------------------------------------
def run_stress_test(weights: Dict[str, float]) -> pd.DataFrame:
    """
    Run portfolio shocks based on configured stress scenarios.
    Args:
        weights: dict of asset â†’ weight
    Returns:
        DataFrame of scenario impacts
    """
    impacts = []
    for scenario in STRESS_SCENARIOS:
        name = scenario["name"]
        shock = scenario["shock"]
        impact = sum(weights.get(asset, 0) * change for asset, change in shock.items())
        impacts.append({"Scenario": name, "Impact": impact})
    return pd.DataFrame(impacts)


# ----------------------------------------------------------------------
# Order Execution
# ----------------------------------------------------------------------
def execute_order(
    broker_name: str, symbol: str, side: str, qty: float, price: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Execute or simulate an order.
    Args:
        broker_name: broker key
        symbol: trading pair / ticker
        side: 'buy' or 'sell'
        qty: quantity
        price: price if limit order
    Returns:
        Dict with order result or None on failure
    """
    broker = brokers[broker_name]
    simulated_price = price * (1 + SLIPPAGE) if price else None

    if DRY_RUN:
        logger.info(
            "[DRY-RUN] %s %s %s @ %.4f", side, qty, symbol, simulated_price or 0.0
        )
        log_trade(broker_name, symbol, side, qty, simulated_price or 0.0, SLIPPAGE)
        return {"status": "simulated", "price": simulated_price or 0.0}

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
    except Exception as exc:
        with open("execution_errors.log", "a", encoding="utf-8") as errfile:
            errfile.write(f"{datetime.utcnow()} | {symbol} | {str(exc)}\n")
        logger.error("âš ï¸ Execution error for %s: %s", symbol, exc)
        return None


# ----------------------------------------------------------------------
# CLI Entrypoint
# ----------------------------------------------------------------------
if __name__ == "__main__":
    WEIGHTS_FILE = "latest_weights.json"
    if not os.path.exists(WEIGHTS_FILE):
        logger.warning("No %s found. Skipping execution loop.", WEIGHTS_FILE)
    else:
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            new_weights = json.load(f)

        stress_df = run_stress_test(new_weights)
        print("\nStress Test Before Execution:\n", stress_df)

        for sym, weight in new_weights.items():
            # Replace qty logic with portfolio sizing model
            execute_order("binance", sym, "buy", qty=0.1, price=20000)
