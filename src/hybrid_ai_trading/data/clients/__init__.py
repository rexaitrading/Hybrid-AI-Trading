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
from .polygon_client import PolygonClient
from .errors import (
    DataClientError,
    AlpacaAPIError,
    BenzingaAPIError,
    CoinAPIError,
    PolygonAPIError,
)

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
