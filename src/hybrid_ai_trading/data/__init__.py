"""
Hybrid AI Quant Pro â€“ Data Layer
--------------------------------
Unified access to external market data clients and adapters.

Provides:
- AlpacaClient: equities/crypto broker data
- BenzingaClient: news and sentiment
- CoinAPIClient: crypto data feeds
- PolygonClient: equities/ETF/indices market data
- DataClientError: base error type for consistency

This package abstracts away vendor-specific APIs and exposes
a consistent hedge-fund grade interface for ingestion, backtesting,
and live trading.
"""

from .clients.alpaca_client import AlpacaClient
from .clients.benzinga_client import BenzingaClient
from .clients.coinapi_client import CoinAPIClient
from .clients.errors import DataClientError
from .clients.polygon_client import PolygonClient

__all__ = [
    "AlpacaClient",
    "BenzingaClient",
    "CoinAPIClient",
    "PolygonClient",
    "DataClientError",
]
