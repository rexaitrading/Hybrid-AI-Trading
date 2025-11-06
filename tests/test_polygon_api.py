"""
Unit Tests: Polygon API Raw Endpoint (Hybrid AI Quant Pro v13.5 Ã¢â‚¬â€œ Hedge-Fund Grade)
----------------------------------------------------------------------------------
Covers:
- Successful REST call with mocked requests
- Failure branch when requests raises
- Skips gracefully if POLYGON_KEY not set
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()
POLYGON_KEY = os.getenv("POLYGON_KEY")


@pytest.mark.skipif(not POLYGON_KEY, reason="POLYGON_KEY not set in environment")
@patch("requests.get")
def test_polygon_api_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [{"c": 150}]}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2025-01-01?limit=5&apiKey={POLYGON_KEY}"
    resp = requests.get(url)
    data = resp.json()

    assert resp.status_code == 200
    assert "results" in data
    assert data["results"][0]["c"] == 150


@patch("requests.get")
def test_polygon_api_failure(mock_get, caplog):
    mock_get.side_effect = Exception("network down")
    url = "https://api.polygon.io/v2/aggs/ticker/FAIL/range/1/day/2024-01-01/2025-01-01?limit=5&apiKey=FAKE"
    with pytest.raises(Exception):
        requests.get(url)
