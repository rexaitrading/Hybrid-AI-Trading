import unittest
from unittest.mock import patch
from src.data.clients.polygon_client import PolygonClient, PolygonAPIError

class TestEnv(unittest.TestCase):

    @patch("src.data.clients.polygon_client.load_config")
    def test_polygon_client_with_valid_key(self, mock_load):
        """PolygonClient should init with a valid API key (mocked)"""
        mock_load.return_value = {
            "providers": {
                "polygon": {"api_key_env": "TEST_KEY"}  # fake key for test
            }
        }
        client = PolygonClient()
        self.assertIn("Authorization", client.headers)
        self.assertEqual(client.headers["Authorization"], "Bearer TEST_KEY")

    @patch("src.data.clients.polygon_client.load_config")
    def test_polygon_client_missing_key(self, mock_load):
        """PolygonClient should raise RuntimeError if API key missing"""
        mock_load.return_value = {
            "providers": {
                "polygon": {"api_key_env": None}
            }
        }
        with self.assertRaises(RuntimeError):
            PolygonClient()

    @patch("src.data.clients.polygon_client.load_config")
    def test_invalid_config_structure(self, mock_load):
        """Invalid config structure should raise PolygonAPIError"""
        mock_load.return_value = {}
        with self.assertRaises(PolygonAPIError):
            PolygonClient()
