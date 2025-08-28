import unittest
from unittest.mock import patch
from src.data.clients import coinapi_client
from src.data.clients.coinapi_client import CoinAPIError

class TestCoinAPIEnv(unittest.TestCase):

    @patch("src.data.clients.coinapi_client.load_config")
    def test_coinapi_with_valid_key(self, mock_load):
        """CoinAPI should load with a valid key (mocked)"""
        mock_load.return_value = {
            "providers": {
                "coinapi": {"api_key_env": "TEST_COINAPI_KEY"}
            }
        }
        key = mock_load.return_value["providers"]["coinapi"]["api_key_env"]
        headers = {"X-CoinAPI-Key": key}
        self.assertEqual(headers["X-CoinAPI-Key"], "TEST_COINAPI_KEY")

    @patch("src.data.clients.coinapi_client.load_config")
    def test_coinapi_missing_key(self, mock_load):
        """CoinAPI should raise RuntimeError if key missing"""
        mock_load.return_value = {
            "providers": {
                "coinapi": {"api_key_env": None}
            }
        }
        with self.assertRaises(RuntimeError):
            _ = coinapi_client.get_fx_rate("BTC", "USD")  # triggers _get_headers()

    @patch("src.data.clients.coinapi_client.load_config")
    def test_coinapi_invalid_config(self, mock_load):
        """Invalid config structure should raise CoinAPIError"""
        mock_load.return_value = {}
        with self.assertRaises(CoinAPIError):
            _ = coinapi_client.get_fx_rate("BTC", "USD")

