"""
Hybrid AI Quant Pro – Data Client Errors (Hedge-Fund Grade, Flake8 Clean)
-------------------------------------------------------------------------
Centralized base and provider-specific exceptions for all
data client modules. This ensures consistent error handling
across CoinAPI, Polygon, Alpaca, Benzinga, etc.

Usage:
    raise CoinAPIError("Request failed: 429 Too Many Requests")
    raise PolygonAPIError("Unexpected response format")
"""

__all__ = [
    "DataClientError",
    "CoinAPIError",
    "PolygonAPIError",
    "AlpacaAPIError",
    "BenzingaAPIError",
]


class DataClientError(RuntimeError):
    """Base exception for all data client errors."""


class CoinAPIError(DataClientError):
    """Raised for any CoinAPI-related error."""


class PolygonAPIError(DataClientError):
    """Raised for any Polygon API-related error."""


class AlpacaAPIError(DataClientError):
    """Raised for any Alpaca API-related error."""


class BenzingaAPIError(DataClientError):
    """Raised for any Benzinga API-related error."""
