"""
Unit Tests: Data Clients (Hybrid AI Quant Pro v9.3 – Hedge-Fund OE Grade, 100% Coverage)
----------------------------------------------------------------------------------------
Covers Alpaca, Polygon, Benzinga, and CoinAPI clients.
"""

from unittest.mock import MagicMock, patch

import pytest

import hybrid_ai_trading.data.clients.coinapi_client as coinapi
from hybrid_ai_trading.data.clients.alpaca_client import AlpacaAPIError, AlpacaClient
from hybrid_ai_trading.data.clients.benzinga_client import (
    BenzingaAPIError,
    BenzingaClient,
)
from hybrid_ai_trading.data.clients.polygon_client import PolygonAPIError, PolygonClient


# ==========================================================
# AlpacaClient
# ==========================================================
def test_alpaca_missing_keys(monkeypatch, caplog):
    monkeypatch.delenv("ALPACA_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)
    with caplog.at_level("WARNING"):
        _ = AlpacaClient(api_key=None, api_secret=None)
    assert "keys not set" in caplog.text


def test_alpaca_mask_key_variants():
    client = AlpacaClient(api_key="abcd1234efgh5678", api_secret="demo")
    assert client._mask_key_local(None) == "None"
    assert client._mask_key_local("short") == "short"
    masked = client._mask_key_local("abcd1234efgh5678")
    assert masked.startswith("abcd") and masked.endswith("5678")


def test_alpaca_headers_and_failure():
    client = AlpacaClient("key", "secret")
    headers = client._headers()
    assert "APCA-API-KEY-ID" in headers

    client.api_key, client.api_secret = None, None
    with pytest.raises(AlpacaAPIError):
        client._headers()


@patch("hybrid_ai_trading.data.clients.alpaca_client.requests.request")
def test_alpaca_request_success(mock_req):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"account": "ok"}
    mock_resp.raise_for_status.return_value = None
    mock_req.return_value = mock_resp
    client = AlpacaClient("demo", "demo")
    assert "account" in client.account()


@patch("hybrid_ai_trading.data.clients.alpaca_client.requests.request")
def test_alpaca_request_failure(mock_req):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("API fail")
    mock_req.return_value = mock_resp
    client = AlpacaClient("demo", "demo")
    with pytest.raises(AlpacaAPIError):
        client.account()


@patch("hybrid_ai_trading.data.clients.alpaca_client.AlpacaClient.account")
def test_alpaca_ping_all_paths(mock_acc, caplog):
    mock_acc.return_value = {"status": "ok"}
    client = AlpacaClient("demo", "demo")
    assert client.ping() is True

    mock_acc.side_effect = AlpacaAPIError("bad")
    with caplog.at_level("WARNING"):
        assert client.ping() is False

    mock_acc.side_effect = Exception("weird")
    with caplog.at_level("ERROR"):
        assert client.ping() is False


# ==========================================================
# PolygonClient
# ==========================================================


def test_polygon_missing_key(monkeypatch):
    monkeypatch.delenv("POLYGON_KEY", raising=False)
    with pytest.raises(PolygonAPIError, match="Polygon API key not provided"):
        PolygonClient(api_key=None)


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_polygon_request_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"c": 123}]}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp
    client = PolygonClient("demo")
    assert "results" in client.prev_close("AAPL")


@patch("hybrid_ai_trading.data.clients.polygon_client.requests.get")
def test_polygon_request_failure(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("bad")
    mock_get.return_value = mock_resp
    client = PolygonClient("demo")
    with pytest.raises(PolygonAPIError):
        client.prev_close("AAPL")


@patch("hybrid_ai_trading.data.clients.polygon_client.PolygonClient.prev_close")
def test_polygon_ping_all_paths(mock_prev):
    client = PolygonClient("demo")

    mock_prev.return_value = {"results": [1]}
    assert client.ping() is True

    mock_prev.side_effect = PolygonAPIError("fail")
    assert client.ping() is False

    mock_prev.side_effect = Exception("weird")
    assert client.ping() is False


# ==========================================================
# BenzingaClient
# ==========================================================
def test_benzinga_missing_key(monkeypatch):
    monkeypatch.delenv("BENZINGA_KEY", raising=False)
    with pytest.raises(BenzingaAPIError):
        BenzingaClient(api_key=None)


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_benzinga_success_and_fail(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"articles": [{"id": 1, "title": "fake"}]}
    mock_get.return_value = mock_resp

    client = BenzingaClient("demo")
    result = client.get_news("AAPL")

    assert isinstance(result, dict)
    assert "articles" in result
    assert isinstance(result["articles"], list)

    bad_resp = MagicMock()
    bad_resp.raise_for_status.side_effect = Exception("fail")
    mock_get.return_value = bad_resp

    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")


# ==========================================================
# CoinAPI Client
# ==========================================================
def test_coinapi_headers_valid_and_stub(monkeypatch):
    monkeypatch.setenv("COINAPI_KEY", "demo")

    def fake_load():
        return {"providers": {"coinapi": {"api_key_env": "COINAPI_KEY"}}}

    monkeypatch.setattr(coinapi, "load_config", fake_load)
    assert "X-CoinAPI-Key" in coinapi._get_headers()

    monkeypatch.delenv("COINAPI_KEY", raising=False)
    monkeypatch.setenv("COINAPI_ALLOW_STUB", "1")
    assert coinapi._get_headers() == {}
    monkeypatch.delenv("COINAPI_ALLOW_STUB", raising=False)

    monkeypatch.delenv("COINAPI_KEY", raising=False)
    monkeypatch.setenv("COINAPI_ALLOW_STUB", "0")
    with pytest.raises(coinapi.CoinAPIError):
        coinapi._get_headers()
    monkeypatch.delenv("COINAPI_ALLOW_STUB", raising=False)


def test_coinapi_headers_exception(monkeypatch):
    def bad_load():
        raise Exception("config fail")

    monkeypatch.setattr(coinapi, "load_config", bad_load)
    with pytest.raises(coinapi.CoinAPIError):
        coinapi._get_headers()


def test_coinapi_iso():
    from datetime import datetime

    ts = datetime(2020, 1, 1)
    assert coinapi._iso(ts).endswith("Z")


@patch("hybrid_ai_trading.data.clients.coinapi_client.requests.get")
def test_coinapi_retry_paths(mock_get, monkeypatch):
    monkeypatch.setenv("COINAPI_KEY", "demo")
    monkeypatch.setattr(
        coinapi,
        "load_config",
        lambda: {"providers": {"coinapi": {"api_key_env": "COINAPI_KEY"}}},
    )

    good = MagicMock(status_code=200)
    good.json.return_value = {"rate": 1.23}
    mock_get.return_value = good
    assert isinstance(coinapi.get_fx_rate("BTC", "USD"), float)

    bad = MagicMock(status_code=500, text="fail")
    mock_get.return_value = bad
    with pytest.raises(coinapi.CoinAPIError):
        coinapi._retry_get("url", max_retry=1, backoff=0.01)


@patch("hybrid_ai_trading.data.clients.coinapi_client._retry_get")
def test_coinapi_ohlcv_paths(mock_retry):
    mock_retry.return_value.json.return_value = [{"candle": 1}]
    assert isinstance(coinapi.get_ohlcv_latest("BTC", "USD"), list)

    mock_retry.return_value.json.return_value = {"error": "bad"}
    with pytest.raises(coinapi.CoinAPIError):
        coinapi.get_ohlcv_latest("BTC", "USD")

    mock_retry.side_effect = Exception("down")
    with pytest.raises(coinapi.CoinAPIError):
        coinapi.get_ohlcv_latest("BTC", "USD", "1MIN", 1)


@patch("hybrid_ai_trading.data.clients.coinapi_client.CoinAPIClient.get_fx_rate")
def test_coinapi_ping_true_and_false(mock_fx):
    mock_fx.return_value = 123
    assert coinapi.ping() is True

    mock_fx.side_effect = Exception("fail")
    assert coinapi.ping() is False
