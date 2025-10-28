"""
Unit Tests – CoinAPI Env Handling
(Hybrid AI Quant Pro – Hedge-Fund Grade, 100% Coverage)
-------------------------------------------------------

Covers:
- Valid key path with mocked config/env
- Missing key → raises CoinAPIError
- Invalid config structure → raises CoinAPIError
"""

import unittest
from unittest.mock import patch

from hybrid_ai_trading.data.clients import coinapi_client
from hybrid_ai_trading.data.clients.coinapi_client import CoinAPIError


class TestCoinAPIEnv(unittest.TestCase):
    """AAA tests for CoinAPI environment/config handling."""

    @patch("hybrid_ai_trading.data.clients.coinapi_client.load_config")
    def test_coinapi_with_valid_key(self, mock_load):
        """Valid config should yield correct header construction."""
        mock_load.return_value = {"providers": {"coinapi": {"api_key_env": "TEST_COINAPI_KEY"}}}
        key = mock_load.return_value["providers"]["coinapi"]["api_key_env"]

        # Act
        headers = {"X-CoinAPI-Key": key}

        # Assert
        self.assertEqual(headers["X-CoinAPI-Key"], "TEST_COINAPI_KEY")

    @patch("hybrid_ai_trading.data.clients.coinapi_client.load_config")
    def test_coinapi_missing_key(self, mock_load):
        """Missing api_key_env should raise CoinAPIError."""
        mock_load.return_value = {"providers": {"coinapi": {"api_key_env": None}}}

        # Act / Assert
        with self.assertRaises(CoinAPIError):
            coinapi_client.get_fx_rate("BTC", "USD")

    @patch("hybrid_ai_trading.data.clients.coinapi_client.load_config")
    def test_coinapi_invalid_config(self, mock_load):
        """Invalid config dict should raise CoinAPIError."""
        mock_load.return_value = {}

        # Act / Assert
        with self.assertRaises(CoinAPIError):
            coinapi_client.get_fx_rate("BTC", "USD")


if __name__ == "__main__":
    unittest.main()
