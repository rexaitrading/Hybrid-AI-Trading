import unittest
from unittest.mock import patch, MagicMock
from src.data.clients import coinapi_client
from src.data.clients.coinapi_client import CoinAPIError

class TestCoinAPIClient(unittest.TestCase):

    @patch("src.data.clients.coinapi_client._retry_get")
    def test_get_fx_rate_success(self, mock_retry):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"rate": 123.45}
        mock_retry.return_value = mock_resp

        rate = coinapi_client.get_fx_rate("BTC", "USD")
        self.assertEqual(rate, 123.45)

    @patch("src.data.clients.coinapi_client._retry_get")
    def test_get_fx_rate_failure(self, mock_retry):
        mock_retry.side_effect = CoinAPIError("API down")
        with self.assertRaises(CoinAPIError):
            coinapi_client.get_fx_rate("BTC", "USD")

    @patch("src.data.clients.coinapi_client._retry_get")
    def test_get_ohlcv_latest_success(self, mock_retry):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                "time_period_start": "2025-08-01T00:00:00Z",
                "price_open": 100,
                "price_high": 110,
                "price_low": 95,
                "price_close": 105,
            }
        ]
        mock_retry.return_value = mock_resp

        data = coinapi_client.get_ohlcv_latest("BTC", "USD", period_id="1DAY", limit=1)
        self.assertEqual(data[0]["price_close"], 105)

    @patch("src.data.clients.coinapi_client._retry_get")
    def test_ping_success(self, mock_retry):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"rate": 50000}
        mock_retry.return_value = mock_resp

        self.assertTrue(coinapi_client.ping())

    @patch("src.data.clients.coinapi_client._retry_get")
    def test_ping_failure(self, mock_retry):
        mock_retry.side_effect = CoinAPIError("timeout")
        self.assertFalse(coinapi_client.ping())

