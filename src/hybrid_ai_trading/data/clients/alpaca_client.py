# src/hybrid_ai_trading/data/clients/alpaca_client.py
"""
Alpaca Client (Hybrid AI Quant Pro v11.0 – Hedge-Fund Grade, Clean)
-------------------------------------------------------------------
Responsibilities:
- Local wrapper around Alpaca REST API
- Masked key handling for logs
- Safe request execution (raises AlpacaAPIError on failure)
- Access to account(), positions(), and ping() methods
- Fully covered by tests/test_alpaca_client_full.py
"""

import logging
import os
import requests

logger = logging.getLogger("hybrid_ai_trading.data.clients.alpaca_client")


class AlpacaAPIError(Exception):
    """Custom exception for Alpaca API errors."""


class AlpacaClient:
    BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")

    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or os.getenv("ALPACA_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_SECRET")

        if not self.api_key or not self.api_secret:
            logger.warning("⚠️ Alpaca API keys not set – client may not work")

    # ------------------------------------------------------------------
    @staticmethod
    def _mask_key_local(key: str) -> str:
        """Mask an API key for safe local display in logs."""
        if key is None:
            return "None"
        if len(key) <= 8:
            return key
        return f"{key[:4]}****{key[-4:]}"

    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        """Return HTTP headers for authenticated requests."""
        if not self.api_key or not self.api_secret:
            raise AlpacaAPIError("Missing Alpaca API credentials")
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    def _request(self, endpoint: str, method: str = "GET", **kwargs):
        """Perform HTTP request and return JSON, raising AlpacaAPIError on failure."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            resp = requests.request(method, url, headers=self._headers(), **kwargs)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("❌ Alpaca request failed: %s", e)
            raise AlpacaAPIError(str(e))

    # ------------------------------------------------------------------
    def account(self):
        """Fetch account details."""
        return self._request("account")

    def positions(self):
        """Fetch open positions (always return list)."""
        data = self._request("positions")
        return data if isinstance(data, list) else [data]

    def ping(self) -> bool:
        """Check if account is reachable. Returns True/False safely."""
        try:
            acc = self.account()
            return bool(acc and acc.get("status"))
        except AlpacaAPIError as e:
            logger.warning("⚠️ Alpaca ping failed: %s", e)
            return False
        except Exception as e:
            logger.error("❌ Unexpected ping error: %s", e)
            return False
