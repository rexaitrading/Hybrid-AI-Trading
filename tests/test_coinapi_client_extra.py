import unittest
from unittest.mock import patch, MagicMock
from src.data.clients import coinapi_client
from src.data.clients.coinapi_client import CoinAPIError

class TestCoinAPIClientExtra(unittest.TestCase):

    @patch("src.data.clients.coinapi_client._get_headers")
    @patch("src.data.clients.coinapi_client.requests.get")
    def test_retry_server_error_then_success(self, mock_get, mock_headers):
        """Should retry on 500 and then succeed"""
        mock_headers.return_value = {"X-CoinAPI-Key": "FAKE"}
        bad_resp = MagicMock(status_code=500, text="server error")
        good_resp = MagicMock(status_code=200)
        good_resp.json.return_value = {"rate": 42}
        mock_get.side_effect = [bad_resp, good_resp]

        rate = coinapi_client.get_fx_rate("BTC", "USD")
        self.assertEqual(rate, 42)

    @patch("src.data.clients.coinapi_client._get_headers")
    @patch("src.data.clients.coinapi_client.requests.get")
    def test_retry_all_failures(self, mock_get, mock_headers):
        """Should raise CoinAPIError after repeated failures"""
        mock_headers.return_value = {"X-CoinAPI-Key": "FAKE"}
        bad_resp = MagicMock(status_code=500, text="fail")
        mock_get.return_value = bad_resp

        with self.assertRaises(CoinAPIError):
            coinapi_client.get_fx_rate("BTC", "USD")

    @patch("src.data.clients.coinapi_client._get_headers")
    @patch("src.data.clients.coinapi_client.requests.get")
    def test_ohlcv_invalid_json_error(self, mock_get, mock_headers):
        """Should raise CoinAPIError if API returns error dict"""
        mock_headers.return_value = {"X-CoinAPI-Key": "FAKE"}
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"error": "bad symbol"}
        mock_get.return_value = mock_resp

        with self.assertRaises(CoinAPIError):
            coinapi_client.get_ohlcv_latest("BTC", "USD")

    @patch("src.data.clients.coinapi_client._get_headers")
    @patch("src.data.clients.coinapi_client.requests.get")
    def test_ohlcv_all_candidates_fail(self, mock_get, mock_headers):
        """Should try all symbol candidates and fail"""
        mock_headers.return_value = {"X-CoinAPI-Key": "FAKE"}
        bad_resp = MagicMock(status_code=500, text="no data")
        mock_get.return_value = bad_resp

        with self.assertRaises(CoinAPIError):
            coinapi_client.get_ohlcv_latest("BTC", "USD")

