"""
Hybrid AI Quant Pro – Data Clients Package (Hedge-Fund Grade)
-------------------------------------------------------------
Unified public API for all data provider clients.

Exports:
- AlpacaClient
- BenzingaClient
- CoinAPIClient
- PolygonClient

Also re-exports shared error types for consistent, centralized
exception handling across all data client modules.
"""

from .alpaca_client import AlpacaClient
from .benzinga_client import BenzingaClient
from .coinapi_client import CoinAPIClient
from .errors import (
    AlpacaAPIError,
    BenzingaAPIError,
    CoinAPIError,
    DataClientError,
    PolygonAPIError,
)
from .polygon_client import PolygonClient

__all__ = [
    # Clients
    "AlpacaClient",
    "BenzingaClient",
    "CoinAPIClient",
    "PolygonClient",
    # Errors
    "DataClientError",
    "AlpacaAPIError",
    "BenzingaAPIError",
    "CoinAPIError",
    "PolygonAPIError",
]
