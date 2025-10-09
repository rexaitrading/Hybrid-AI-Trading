"""
Unit Tests: PolygonClient API Calls (Hybrid AI Quant Pro – Hedge-Fund Grade)
----------------------------------------------------------------------------
Covers:
- prev_close(): success + failure
- ping(): success + failure
"""

from unittest.mock import MagicMock, patch

import pytest

from hybrid_ai_trading.data.clients.polygon_client import PolygonAPIError, PolygonClient


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_prev_close_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [{"c": 150.0}]}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    client = PolygonClient(api_key="FAKE", allow_missing=True)
    data = client.prev_close("AAPL")
    assert "results" in data
    assert data["results"][0]["c"] == 150.0


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_prev_close_failure(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("API error")
    mock_get.return_value = mock_resp

    client = PolygonClient(api_key="FAKE", allow_missing=True)
    with pytest.raises(PolygonAPIError):
        client.prev_close("AAPL")


@patch("hybrid_ai_trading.data.clients.polygon_client.PolygonClient.prev_close")
def test_ping_success(mock_prev):
    mock_prev.return_value = {"results": [{"c": 150.0}]}
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    assert client.ping() is True


@patch("hybrid_ai_trading.data.clients.polygon_client.PolygonClient.prev_close")
def test_ping_failure(mock_prev):
    mock_prev.side_effect = PolygonAPIError("down")
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    assert client.ping() is False
