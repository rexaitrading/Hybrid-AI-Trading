from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Order:
    symbol: str
    side: str
    qty: float
    order_type: str = "MKT"
    limit_price: float | None = None


@runtime_checkable
class Broker(Protocol):
    """
    Minimal broker interface expected by broker/ib_safe.py tests.

    Keep this narrow and stable. Concrete implementations (IBKR, paper) can expand later.
    """

    def place_order(self, order: Order, **kwargs: Any) -> Any: ...
    def cancel_order(self, order_id: str, **kwargs: Any) -> Any: ...