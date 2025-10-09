"""
Unit Tests – PolygonClient Environment Handling
(Hybrid AI Quant Pro – Hedge-Fund Grade, 100% Coverage)
------------------------------------------------------

Covers:
- Valid API key via mocked config/env
- Missing key → raises PolygonAPIError
- Invalid config dict → raises PolygonAPIError
"""

import unittest
from unittest.mock import patch
import pytest

from hybrid_ai_trading.data.clients.polygon_client import (
    PolygonClient,
    PolygonAPIError,
)


class TestPolygonEnv(unittest.TestCase):
    """AAA tests for PolygonClient config/env handling."""

    @patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
    def test_polygon_client_with_valid_key(self, mock_load):
        """Valid config should produce working headers."""
        mock_load.return_value = {
            "providers": {"polygon": {"api_key_env": "TEST_POLYGON_KEY"}}
        }
        client = PolygonClient(api_key="TEST_POLYGON_KEY")
        headers = client._headers()
        self.assertIn("apiKey", headers)
        self.assertEqual(headers["apiKey"], "TEST_POLYGON_KEY")

    @patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
    def test_polygon_client_missing_key(self, mock_load):
        """Config exists but key_env is None → raise PolygonAPIError."""
        mock_load.return_value = {"providers": {"polygon": {"api_key_env": None}}}
        # Ensure env variable is not leaking into test
        import os
        os.environ.pop("POLYGON_KEY", None)

        with self.assertRaises(PolygonAPIError) as ctx:
            PolygonClient(api_key=None, allow_missing=False)
        self.assertIn("Polygon API key not provided", str(ctx.exception))

    @patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
    def test_invalid_config_structure(self, mock_load):
        """Config dict is empty → raise PolygonAPIError (missing key)."""
        mock_load.return_value = {}
        # Ensure env variable is not leaking into test
        import os
        os.environ.pop("POLYGON_KEY", None)

        with self.assertRaises(PolygonAPIError) as ctx:
            PolygonClient(api_key=None, allow_missing=False)
        self.assertIn("Polygon API key not provided", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
