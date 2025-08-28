import unittest
from unittest.mock import patch, MagicMock
from src.data.clients import coinapi_client, polygon_client
from src.data.clients.coinapi_client import CoinAPIError, _get_headers


class TestCoinAPIClientEdges(unittest.TestCase):
    """Edge-case tests for CoinAPI client"""

    @patch("src.data.clients.coinapi_client.load_config")
    def test_coinapi_missing_key_raises_runtimeerror(self, mock_load):
        mock_load.return_value = {"providers": {"coinapi": {"api_key_env": None}}}
        with self.assertRaises(RuntimeError):
            _ = _get_headers()

    @patch("src.data.clients.coinapi_client.load_config")
    def test_headers_invalid_structure_triggers_coinapierror(self, mock_load):
        mock_load.return_value = {}
        with self.assertRaises(CoinAPIError):
            _ = _get_headers()

    @patch("src.data.clients.coinapi_client.load_config")
    def test_headers_none_config_triggers_coinapierror(self, mock_load):
        mock_load.return_value = None
        with self.assertRaises(CoinAPIError):
            _ = _get_headers()

    def test_retry_get_direct_non_retryable_error(self):
        """Line 45: non-retryable HTTP error (404)"""
        with patch("src.data.clients.coinapi_client.requests.get") as mock_get, \
             patch("src.data.clients.coinapi_client._get_headers", return_value={"X-CoinAPI-Key": "FAKE"}):
            resp = MagicMock(status_code=404, text="not found")
            mock_get.return_value = resp
            with self.assertRaises(CoinAPIError):
                coinapi_client._retry_get("http://fake")

    def test_retry_get_exhausted_retries(self):
        """Line 51: retries exhausted after all attempts fail"""
        with patch("src.data.clients.coinapi_client.requests.get", side_effect=Exception("fail")), \
             patch("src.data.clients.coinapi_client._get_headers", return_value={"X-CoinAPI-Key": "FAKE"}):
            with self.assertRaises(CoinAPIError):
                coinapi_client._retry_get("http://fake", max_retry=2, backoff=0)

    @patch("src.data.clients.coinapi_client._retry_get")
    @patch("src.data.clients.coinapi_client._get_headers")
    def test_error_dict_triggers_guard(self, mock_headers, mock_retry):
        """Line 82: API returns {'error': ...}"""
        mock_headers.return_value = {"X-CoinAPI-Key": "FAKE"}
        mock_retry.return_value.json.return_value = {"error": "bad symbol"}
        with self.assertRaises(CoinAPIError):
            coinapi_client.get_ohlcv_latest("FAKE_ID", None, "1MIN", 1)

    def test_all_candidates_fail_final_raise(self):
        """Line 104: all fallback candidates fail"""
        with patch("src.data.clients.coinapi_client._get_headers", return_value={"X-CoinAPI-Key": "FAKE"}), \
             patch("src.data.clients.coinapi_client._retry_get", side_effect=Exception("exchange down")):
            with self.assertRaises(CoinAPIError) as cm:
                coinapi_client.get_ohlcv_latest("BTC", "USD", "1MIN", 1)
            self.assertIn("OHLCV not found", str(cm.exception))

    @patch("src.data.clients.coinapi_client.get_fx_rate")
    def test_ping_handles_failure(self, mock_fx):
        """Line 142: ping() returns False on failure"""
        mock_fx.side_effect = Exception("down")
        self.assertFalse(coinapi_client.ping())


class TestPolygonClientEdges(unittest.TestCase):
    """Edge-case tests for Polygon client"""

    @patch("src.data.clients.polygon_client.requests.get")
    def test_prev_close_failure_http_error(self, mock_get):
        """Line 37: raise_for_status raises"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("API fail")
        mock_get.return_value = mock_resp
        client = polygon_client.PolygonClient()
        with self.assertRaises(polygon_client.PolygonAPIError):
            client.prev_close("AAPL")

    @patch("src.data.clients.polygon_client.requests.get")
    def test_prev_close_failure_malformed_response(self, mock_get):
        """Line 38: .json() raises"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = Exception("bad json")
        mock_get.return_value = mock_resp
        client = polygon_client.PolygonClient()
        with self.assertRaises(polygon_client.PolygonAPIError):
            client.prev_close("AAPL")

    @patch("src.data.clients.polygon_client.PolygonClient.prev_close")
    def test_ping_failure_returns_false(self, mock_prev_close):
        mock_prev_close.side_effect = Exception("connection failed")
        client = polygon_client.PolygonClient()
        self.assertFalse(client.ping())
