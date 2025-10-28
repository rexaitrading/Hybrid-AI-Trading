"""
Unit Tests: PolygonClient (Hybrid AI Quant Pro v13.4 – Hedge-Fund OE Grade, 100% Coverage)
------------------------------------------------------------------------------------------
Covers:
- __init__ with env, missing keys, invalid config, bad key_env, bad providers
- _headers: valid + missing key
- _request: success, unexpected JSON, HTTP error, network failure, JSON decode failure
- prev_close wrapper
- ping() success, PolygonAPIError, generic Exception
- Final enforcement branch (env var exists but unset)
"""

from unittest.mock import MagicMock, patch

import pytest

from hybrid_ai_trading.data.clients.polygon_client import PolygonAPIError, PolygonClient


# ==========================================================
# Initialization Coverage
# ==========================================================
def test_init_with_env_valid(monkeypatch):
    monkeypatch.setenv("POLYGON_KEY", "FAKEKEY")
    client = PolygonClient(api_key=None, allow_missing=False)
    assert client.api_key == "FAKEKEY"
    monkeypatch.delenv("POLYGON_KEY", raising=False)


def test_init_without_key_allow_missing(monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    client = PolygonClient(api_key=None, allow_missing=True)
    assert client.api_key is None


def test_init_without_key_disallow(monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    with patch("hybrid_ai_trading.data.clients.polygon_client.load_config", return_value={}):
        with pytest.raises(PolygonAPIError, match="Polygon API key not provided"):
            PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_with_load_config_exception(mock_load, monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.side_effect = Exception("boom")
    with pytest.raises(PolygonAPIError, match="Failed to load Polygon config"):
        PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_with_invalid_config_dict(mock_load, monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.return_value = "not a dict"
    with pytest.raises(PolygonAPIError, match="Invalid Polygon config structure"):
        PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_with_bad_providers_not_dict(mock_load, monkeypatch):
    """providers exists but is not a dict"""
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.return_value = {"providers": "not-a-dict"}
    with pytest.raises(PolygonAPIError, match="Invalid Polygon config structure"):
        PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_with_polygon_cfg_not_dict(mock_load, monkeypatch):
    """polygon section exists but is not a dict"""
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.return_value = {"providers": {"polygon": "not-a-dict"}}
    with pytest.raises(PolygonAPIError, match="Invalid Polygon config structure"):
        PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_with_bad_keyenv(mock_load, monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.return_value = {"providers": {"polygon": {"api_key_env": ""}}}
    with pytest.raises(PolygonAPIError, match="Polygon API key not provided"):
        PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_with_keyenv_none(mock_load, monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.return_value = {"providers": {"polygon": {"api_key_env": None}}}
    with pytest.raises(PolygonAPIError, match="Polygon API key not provided"):
        PolygonClient(api_key=None, allow_missing=False)


@patch("hybrid_ai_trading.data.clients.polygon_client.load_config")
def test_init_final_enforcement_missing_env(mock_load, monkeypatch):
    """Covers final enforcement branch when env var exists but is unset."""
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    mock_load.return_value = {"providers": {"polygon": {"api_key_env": "POLY_ENV"}}}
    monkeypatch.delenv("POLY_ENV", raising=False)
    with pytest.raises(PolygonAPIError, match="Polygon API key not provided"):
        PolygonClient(api_key=None, allow_missing=False)


# ==========================================================
# _headers Coverage
# ==========================================================
def test_headers_with_valid_key():
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    headers = client._headers()
    assert headers["apiKey"] == "FAKE"


def test_headers_without_key_raises():
    client = PolygonClient(api_key=None, allow_missing=True)
    client.api_key = None
    with pytest.raises(PolygonAPIError, match="Polygon API key not set"):
        client._headers()


# ==========================================================
# _request Coverage
# ==========================================================
@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_success(mock_get):
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"results": []}
    mock_get.return_value = resp
    out = client._request("aggs/ticker/AAPL/prev")
    assert "results" in out


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_unexpected_json(mock_get):
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = ["oops"]
    mock_get.return_value = resp
    with pytest.raises(PolygonAPIError, match="Polygon response not a dict"):
        client._request("aggs/ticker/AAPL/prev")


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_raise_for_status(mock_get):
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("bad http")
    mock_get.return_value = resp
    with pytest.raises(PolygonAPIError, match="bad http"):
        client._request("aggs/ticker/AAPL/prev")


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_network_error(mock_get):
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    mock_get.side_effect = Exception("network fail")
    with pytest.raises(PolygonAPIError, match="network fail"):
        client._request("aggs/ticker/AAPL/prev")


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_request_json_decode_failure(mock_get):
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.side_effect = ValueError("bad json")
    mock_get.return_value = resp
    with pytest.raises(PolygonAPIError, match="Failed to parse Polygon response"):
        client._request("aggs/ticker/AAPL/prev")


# ==========================================================
# prev_close + ping Coverage
# ==========================================================
@patch.object(PolygonClient, "_request")
def test_prev_close_direct(mock_req):
    client = PolygonClient(api_key="FAKE", allow_missing=True)
    mock_req.return_value = {"results": [{"c": 123}]}
    out = client.prev_close("AAPL")
    assert out["results"][0]["c"] == 123


@patch.object(PolygonClient, "prev_close")
def test_ping_success_and_failures(mock_prev, caplog):
    client = PolygonClient(api_key="FAKE", allow_missing=True)

    # Success
    mock_prev.return_value = {"results": [{"c": 100}]}
    assert client.ping() is True

    # PolygonAPIError → False
    mock_prev.side_effect = PolygonAPIError("fail")
    caplog.set_level("WARNING")
    assert client.ping() is False
    assert "Polygon ping failed" in caplog.text

    # Generic Exception → False
    mock_prev.side_effect = Exception("boom")
    assert client.ping() is False
