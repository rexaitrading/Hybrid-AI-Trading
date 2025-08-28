import unittest
from unittest.mock import patch, MagicMock
from src.data.clients.polygon_client import PolygonClient, PolygonAPIError

class TestPolygonClient(unittest.TestCase):

    @patch("src.data.clients.polygon_client.requests.get")
    def test_prev_close_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ticker": "AAPL", "results": [{"c": 150.0}]}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client = PolygonClient()
        data = client.prev_close("AAPL")
        self.assertIn("results", data)
        self.assertEqual(data["results"][0]["c"], 150.0)

    @patch("src.data.clients.polygon_client.requests.get")
    def test_prev_close_failure(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("API error")
        mock_get.return_value = mock_resp

        client = PolygonClient()
        with self.assertRaises(PolygonAPIError):
            client.prev_close("AAPL")

    @patch("src.data.clients.polygon_client.PolygonClient.prev_close")
    def test_ping_success(self, mock_prev):
        mock_prev.return_value = {"results": [{"c": 150.0}]}  # ✅ properly closed
        client = PolygonClient()
        self.assertTrue(client.ping())

