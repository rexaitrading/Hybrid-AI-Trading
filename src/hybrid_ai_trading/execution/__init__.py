"""
Execution adapters (IB, paper/live).
Re-exports selected symbols from route_ib to provide a clean API.
"""

__all__ = [
    "IB",
    "LimitOrder",
    "RiskConfig",
    "Stock",
    "dollars_for_symbol",
    "place_entry",
    "size_from_dollars",
]

# Keep imports local to avoid heavy side-effects on package import
from .route_ib import (  # noqa: E402
    IB,
    LimitOrder,
    RiskConfig,
    Stock,
    dollars_for_symbol,
    place_entry,
    size_from_dollars,
)
