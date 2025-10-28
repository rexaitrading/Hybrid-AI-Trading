"""
Unit Tests – CoinAPIClient (Hybrid AI Quant Pro v13.6 – Hedge-Fund OE Grade, 100% Coverage)
-------------------------------------------------------------------------------------------
Covers ALL branches in coinapi_client.py:
- _get_headers: stub, load_config exception, invalid config, None config,
  missing api_key_env, missing env (stub + forced error), empty key, valid key
- _iso: naive datetime formatting
- _retry_get: stub path, success, retryable, non-retryable, exception
- CoinAPIClient.get_fx_rate: stub, valid, invalid
- CoinAPIClient.get_ohlcv_latest: stub, list, dict no error, dict error,
  unexpected format, candidates exhausted
- CoinAPIClient.ping: success, CoinAPIError, Exception, module-level
- batch_prev_close: stub mode, OK path, NO_DATA, ERROR
- module-level wrappers: get_ohlcv_latest, get_fx_rate, ping
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from hybrid_ai_trading.data.clients import coinapi_client
from hybrid_ai_trading.data.clients.coinapi_client import (
    CoinAPIClient,
    CoinAPIError,
    _iso,
    batch_prev_close,
    get_fx_rate,
    get_ohlcv_latest,
    ping,
)


# ----------------------------------------------------------------------
# _get_headers
# ----------------------------------------------------------------------
def test_get_headers_stub(monkeypatch):
    monkeypatch.setenv("COINAPI_STUB", "1")
    out = coinapi_client._get_headers()
    assert out == {}
    monkeypatch.delenv("COINAPI_STUB", raising=False)


def test_get_headers_load_config_exception(monkeypatch):
    """Covers branch where load_config() itself raises."""

    def bad_loader():
        raise RuntimeError("config fail")

    monkeypatch.setattr(coinapi_client, "load_config", bad_loader)
    with pytest.raises(CoinAPIError) as e:
        coinapi_client._get_headers()
    assert "config fail" in str(e.value)


def test_get_headers_full_paths(monkeypatch):
    with patch("hybrid_ai_trading.data.clients.coinapi_client.load_config") as mock_cfg:
        # invalid config type
        mock_cfg.return_value = "bad"
        with pytest.raises(CoinAPIError):
            coinapi_client._get_headers()

        # None config
        mock_cfg.return_value = None
        with pytest.raises(CoinAPIError):
            coinapi_client._get_headers()

        # missing api_key_env
        mock_cfg.return_value = {"providers": {"coinapi": {"api_key_env": None}}}
        with pytest.raises(CoinAPIError):
            coinapi_client._get_headers()

        # missing env var → stub fallback
        mock_cfg.return_value = {"providers": {"coinapi": {"api_key_env": "MISSING"}}}
        monkeypatch.delenv("MISSING", raising=False)
        assert coinapi_client._get_headers() == {}

        # disable stub fallback → force error
        monkeypatch.setenv("COINAPI_ALLOW_STUB", "0")
        with pytest.raises(CoinAPIError):
            coinapi_client._get_headers()
        monkeypatch.delenv("COINAPI_ALLOW_STUB", raising=False)

        # env var is set but empty string → triggers stub
        mock_cfg.return_value = {"providers": {"coinapi": {"api_key_env": "EMPTY"}}}
        monkeypatch.setenv("EMPTY", "")
        assert coinapi_client._get_headers() == {}
        monkeypatch.delenv("EMPTY", raising=False)

        # happy path with non-empty env var
        mock_cfg.return_value = {"providers": {"coinapi": {"api_key_env": "FAKE"}}}
        monkeypatch.setenv("FAKE", "SECRETKEY")
        headers = coinapi_client._get_headers()
        assert "X-CoinAPI-Key" in headers
        monkeypatch.delenv("FAKE", raising=False)


# ----------------------------------------------------------------------
# _iso
# ----------------------------------------------------------------------
def test_iso_formats_with_timezone():
    ts = datetime(2025, 1, 1, 12, 0, 0)  # naive datetime
    out = _iso(ts)
    assert out.endswith("Z")


# ----------------------------------------------------------------------
# _retry_get
# ----------------------------------------------------------------------
def test_retry_get_stub_when_headers_empty(monkeypatch):
    monkeypatch.setenv("COINAPI_ALLOW_STUB", "1")
    with patch("hybrid_ai_trading.data.clients.coinapi_client._get_headers", return_value={}):
        resp = coinapi_client._retry_get("http://fake")
        assert isinstance(resp.json(), dict)
    monkeypatch.delenv("COINAPI_ALLOW_STUB", raising=False)


@patch("hybrid_ai_trading.data.clients.coinapi_client.requests.get")
@patch(
    "hybrid_ai_trading.data.clients.coinapi_client._get_headers",
    return_value={"X": "Y"},
)
def test_retry_get_success(mock_headers, mock_get):
    good = MagicMock(status_code=200)
    good.json.return_value = {"ok": 1}
    mock_get.return_value = good
    resp = coinapi_client._retry_get("http://fake")
    assert resp is good


@patch("hybrid_ai_trading.data.clients.coinapi_client.time.sleep", return_value=None)
@patch("hybrid_ai_trading.data.clients.coinapi_client.requests.get")
@patch(
    "hybrid_ai_trading.data.clients.coinapi_client._get_headers",
    return_value={"X": "Y"},
)
def test_retry_get_retryable_then_success(mock_headers, mock_get, _sleep):
    bad = MagicMock(status_code=503, text="retry")
    good = MagicMock(status_code=200)
    good.json.return_value = {"ok": True}
    mock_get.side_effect = [bad, good]
    resp = coinapi_client._retry_get("http://fake", max_retry=2)
    assert resp is good


@patch("hybrid_ai_trading.data.clients.coinapi_client.time.sleep", return_value=None)
@patch("hybrid_ai_trading.data.clients.coinapi_client.requests.get")
@patch(
    "hybrid_ai_trading.data.clients.coinapi_client._get_headers",
    return_value={"X": "Y"},
)
def test_retry_get_exhausts_and_nonretryable(mock_headers, mock_get, _sleep):
    bad_retry = MagicMock(status_code=503, text="retry")
    mock_get.return_value = bad_retry
    with pytest.raises(CoinAPIError):
        coinapi_client._retry_get("http://fake", max_retry=1)

    bad_nonretry = MagicMock(status_code=400, text="bad")
    mock_get.return_value = bad_nonretry
    with pytest.raises(CoinAPIError):
        coinapi_client._retry_get("http://fake")


@patch(
    "hybrid_ai_trading.data.clients.coinapi_client.requests.get",
    side_effect=Exception("boom"),
)
@patch(
    "hybrid_ai_trading.data.clients.coinapi_client._get_headers",
    return_value={"X": "Y"},
)
def test_retry_get_exception_path(mock_headers, mock_get):
    with pytest.raises(CoinAPIError):
        coinapi_client._retry_get("http://fake", max_retry=1)


# ----------------------------------------------------------------------
# CoinAPIClient methods
# ----------------------------------------------------------------------
def test_fx_rate_stub(monkeypatch):
    monkeypatch.setenv("COINAPI_STUB", "1")
    client = CoinAPIClient()
    assert client.get_fx_rate("BTC", "USD") == 1.2345
    monkeypatch.delenv("COINAPI_STUB", raising=False)


@patch("hybrid_ai_trading.data.clients.coinapi_client._retry_get")
def test_fx_rate_success_and_invalid(mock_retry):
    client = CoinAPIClient()
    good = MagicMock()
    good.json.return_value = {"rate": 123.4}
    mock_retry.return_value = good
    assert client.get_fx_rate("BTC", "USD") == 123.4

    bad = MagicMock()
    bad.json.return_value = {"oops": "x"}
    mock_retry.return_value = bad
    with pytest.raises(CoinAPIError):
        client.get_fx_rate("BTC", "USD")


@patch("hybrid_ai_trading.data.clients.coinapi_client._retry_get")
def test_ohlcv_latest_paths(mock_retry):
    client = CoinAPIClient()
    good = MagicMock()
    good.json.return_value = [{"c": 1}]
    mock_retry.return_value = good
    assert client.get_ohlcv_latest("BTCUSD")[0]["c"] == 1

    good.json.return_value = {"random": "dict"}
    assert client.get_ohlcv_latest("BTC", "USD") == []

    good.json.return_value = {"error": "bad"}
    mock_retry.return_value = good
    with pytest.raises(CoinAPIError):
        client.get_ohlcv_latest("BTC", "USD")

    good.json.return_value = "unexpected string"
    mock_retry.return_value = good
    assert client.get_ohlcv_latest("BTC", "USD") == []


@patch(
    "hybrid_ai_trading.data.clients.coinapi_client._retry_get",
    side_effect=Exception("fail"),
)
def test_ohlcv_exhaust_candidates(mock_retry):
    client = CoinAPIClient()
    with pytest.raises(CoinAPIError):
        client.get_ohlcv_latest("BTC", "USD")


def test_ohlcv_stub(monkeypatch):
    monkeypatch.setenv("COINAPI_STUB", "1")
    client = CoinAPIClient()
    bars = client.get_ohlcv_latest("BTC", "USD", limit=2)
    assert all("price_close" in b for b in bars)
    monkeypatch.delenv("COINAPI_STUB", raising=False)


# ----------------------------------------------------------------------
# ping
# ----------------------------------------------------------------------
@patch("hybrid_ai_trading.data.clients.coinapi_client.CoinAPIClient.get_fx_rate")
def test_ping_paths(mock_fx):
    client = CoinAPIClient()

    # success
    mock_fx.return_value = 123
    assert client.ping() is True
    assert ping() is True  # module-level

    # error branch
    mock_fx.side_effect = CoinAPIError("bad")
    assert client.ping() is False

    mock_fx.side_effect = Exception("boom")
    assert client.ping() is False


# ----------------------------------------------------------------------
# batch_prev_close
# ----------------------------------------------------------------------
def test_batch_prev_close_stub(monkeypatch):
    monkeypatch.setenv("COINAPI_STUB", "1")
    out = batch_prev_close(["BTC", "ETH"])
    assert out["BTC"]["status"] == "STUB"
    monkeypatch.delenv("COINAPI_STUB", raising=False)


@patch("hybrid_ai_trading.data.clients.coinapi_client.CoinAPIClient.get_ohlcv_latest")
def test_batch_prev_close_ok_no_data_error(mock_ohlcv):
    now = datetime.now(timezone.utc).isoformat()
    mock_ohlcv.side_effect = [
        [
            {
                "time_period_start": now,
                "price_open": 1,
                "price_high": 2,
                "price_low": 0.5,
                "price_close": 1.1,
                "volume_traded": 100,
                "price_vwap": 1.05,
            }
        ],
        [],  # no data
        Exception("fail"),  # error
    ]
    out = batch_prev_close(["BTC", "ETH", "XRP"])
    assert out["BTC"]["status"] == "OK"
    assert out["ETH"]["status"] == "NO_DATA"
    assert out["XRP"]["status"].startswith("ERROR:")


# ----------------------------------------------------------------------
# module-level wrappers
# ----------------------------------------------------------------------
def test_module_wrappers(monkeypatch):
    monkeypatch.setenv("COINAPI_STUB", "1")
    bars = get_ohlcv_latest("BTC", "USD", limit=1)
    assert isinstance(bars, list)
    assert all("price_close" in b for b in bars)
    assert isinstance(get_fx_rate("BTC", "USD"), float)
    assert ping() in (True, False)
    monkeypatch.delenv("COINAPI_STUB", raising=False)
