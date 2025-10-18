from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from hybrid_ai_trading.execution.broker_api import place_limit

def place_entry(symbol: str, side: str, qty: int, limit_price: float) -> Dict[str, Any]:
    """
    Unified entry: routes via ExecRouter (IBKR primary -> Alpaca fallback).
    Returns dict with broker/status/resp fields.
    """
    return place_limit(symbol, side, int(qty), float(limit_price))