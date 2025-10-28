from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict

from hybrid_ai_trading.execution.broker_api import place_limit


def place_entry(symbol: str, side: str, qty: int, limit_price: float) -> Dict[str, Any]:
    """
    Unified entry: routes via ExecRouter (IBKR primary -> Alpaca fallback).
    Returns dict with broker/status/resp fields.
    """
    return place_limit(symbol, side, int(qty), float(limit_price))
