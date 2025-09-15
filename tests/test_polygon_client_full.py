"""
Unit Tests: PolygonClient (Hybrid AI Quant Pro v8.1 – Absolute 100% Coverage)
----------------------------------------------------------------------------
Now covers every branch:
- Init with env key
- Init with missing key (allow_missing=True vs False)
- Config error path
- _request success, non-dict JSON, requests.get exception, raise_for_status exception
- prev_close wrapper
- ping() success, PolygonAPIError fail, generic Exception fail
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from hybrid_ai_trading.data.clients.polygon_client import PolygonClient, PolygonAPIError
import hybrid_ai_trading.data.clients.polygon_client as polygon_module


# ------------------------------------------------------
# Init Coverage
# ------------------------------------------------------
def test_init_with_env_valid(monkeypatch, caplog):
    monkeypatch.setenv("POLYGON_KEY", "FAKEKEY")
    caplog.set_level("INFO")
    c = PolygonClient(api_key=None, allow_missing=False)
    assert c.api_key == "FAKEKEY"
    assert "PolygonClient initialized" in caplog.text


def test_init_without_key_allow_missing(monkeypatch, caplog):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    caplog.set_level("WARNING")
    c = PolygonClient(api_key=None, allow_missing=True)
    assert c.api_key is None
    assert "Polygon API key not set" in caplog.text


def test_init_without_key_disallow(monkeypatch):
    """Covers RuntimeError branch when no API key and allow_missing=False."""
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Polygon API key not configured"):
        PolygonClient(api_key=None, allow_missing=False)


def test_init_with_invalid_config(monkeypatch):
    """Covers branch where CONFIG structure is broken."""
    monkeypatch.setattr(polygon_module, "CONFIG", None)
    with pytest.raises(RuntimeError, match="Invalid Polygon config structure"):
        PolygonClient(api_key="FAKE", allow_missing=True)


# ------------------------------------------------------
# _request Coverage
# ------------------------------------------------------
@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_success(mock_get):
    c = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"results": []}
    mock_get.return_value = resp
    out = c._request("aggs/ticker/AAPL/prev")
    assert "results" in out


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_unexpected_json_format(mock_get):
    """Covers non-dict JSON branch."""
    c = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = ["not-a-dict"]
    mock_get.return_value = resp
    with pytest.raises(PolygonAPIError, match="Unexpected response format"):
        c._request("aggs/ticker/AAPL/prev")


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_raise_for_status_exception(mock_get):
    """Covers branch where raise_for_status throws."""
    c = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("HTTP fail")
    mock_get.return_value = resp
    with pytest.raises(PolygonAPIError):
        c._request("aggs/ticker/AAPL/prev")


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_requests_get_exception(mock_get):
    """Covers branch where requests.get itself throws."""
    c = PolygonClient(api_key="FAKE", allow_missing=True)
    mock_get.side_effect = Exception("network error")
    with pytest.raises(PolygonAPIError):
        c._request("aggs/ticker/AAPL/prev")


# ------------------------------------------------------
# prev_close + ping Coverage
# ------------------------------------------------------
@patch.object(PolygonClient, "_request")
def test_prev_close_direct(mock_req):
    c = PolygonClient(api_key="FAKE", allow_missing=True)
    mock_req.return_value = {"results": [{"c": 123.45}]}
    out = c.prev_close("AAPL")
    assert out["results"][0]["c"] == 123.45


@patch.object(PolygonClient, "prev_close")
def test_ping_success_and_failures(mock_prev, caplog):
    c = PolygonClient(api_key="FAKE", allow_missing=True)

    # Success
    mock_prev.return_value = {"results": [{"c": 100}]}
    assert c.ping() is True

    # PolygonAPIError
    mock_prev.side_effect = PolygonAPIError("bad")
    caplog.set_level("WARNING")
    assert c.ping() is False
    assert "Polygon ping failed" in caplog.text

    # Generic Exception
    mock_prev.side_effect = Exception("network down")
    assert c.ping() is False

import pytest
from unittest.mock import patch
from hybrid_ai_trading.data.clients.polygon_client import PolygonClient, PolygonAPIError
import hybrid_ai_trading.data.clients.polygon_client as polygon_module


def test_init_invalid_config(monkeypatch):
    """Force CONFIG to break to hit RuntimeError at init."""
    monkeypatch.setattr(polygon_module, "CONFIG", None)
    with pytest.raises(RuntimeError, match="Invalid Polygon config structure"):
        PolygonClient(api_key="FAKE", allow_missing=True)


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_direct_exception(mock_get):
    """Force requests.get itself to raise to cover error branch."""
    c = PolygonClient(api_key="FAKE", allow_missing=True)
    mock_get.side_effect = Exception("network down hard")
    with pytest.raises(PolygonAPIError, match="network down hard"):
        c._request("aggs/ticker/AAPL/prev")
