"""
Unit Tests – AlpacaClient (Hybrid AI Quant Pro v12.1 – Hedge-Fund OE Grade, AAA+ Coverage)
------------------------------------------------------------------------------------------
Covers all branches of alpaca_client.py with stable micro-tests:
- __init__ with and without keys
- _mask_key_local (None, short, long)
- _headers (valid + raises on missing creds)
- _request (success, raise_for_status fail, json fail, network fail)
- account() and positions() (list + dict wrapping)
- ping() (success, None, missing status, AlpacaAPIError, generic Exception)
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from hybrid_ai_trading.data.clients.alpaca_client import AlpacaAPIError, AlpacaClient


def test_init_with_and_without_keys(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    c = AlpacaClient(api_key="KEY", api_secret="SEC")
    assert c.api_key == "KEY"
    assert c.api_secret == "SEC"

    monkeypatch.delenv("ALPACA_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)
    caplog.set_level(logging.WARNING)
    _ = AlpacaClient(api_key=None, api_secret=None)
    assert "API keys not set" in caplog.text


def test_mask_key_local_variants():
    assert AlpacaClient._mask_key_local(None) == "None"
    assert AlpacaClient._mask_key_local("short") == "short"
    masked = AlpacaClient._mask_key_local("ABCDEFGHIJKL")
    assert masked == "ABCD****IJKL"


def test_headers_and_missing():
    c = AlpacaClient(api_key="KEY", api_secret="SEC")
    h = c._headers()
    assert h["APCA-API-KEY-ID"] == "KEY"
    assert h["APCA-API-SECRET-KEY"] == "SEC"

    c.api_key, c.api_secret = None, None
    with pytest.raises(AlpacaAPIError):
        c._headers()


@patch("hybrid_ai_trading.data.clients.alpaca_client.requests.request")
def test_request_success_and_failures(mock_req, caplog):
    c = AlpacaClient(api_key="KEY", api_secret="SEC")

    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"ok": 1}
    mock_req.return_value = r
    assert c._request("account") == {"ok": 1}

    r.raise_for_status.side_effect = Exception("bad req")
    mock_req.return_value = r
    with pytest.raises(AlpacaAPIError):
        c._request("account")

    r.raise_for_status.side_effect = None
    r.json.side_effect = ValueError("json fail")
    mock_req.return_value = r
    caplog.set_level(logging.ERROR)
    with pytest.raises(AlpacaAPIError):
        c._request("account")
    assert "request failed" in caplog.text

    mock_req.side_effect = Exception("network down")
    with pytest.raises(AlpacaAPIError):
        c._request("account")


@patch.object(AlpacaClient, "_request")
def test_account_and_positions(mock_req):
    c = AlpacaClient(api_key="K", api_secret="S")

    mock_req.return_value = {"equity": "1000"}
    assert c.account()["equity"] == "1000"

    mock_req.return_value = [{"symbol": "AAPL"}]
    out = c.positions()
    assert isinstance(out, list) and out[0]["symbol"] == "AAPL"

    mock_req.return_value = {"symbol": "TSLA"}
    out2 = c.positions()
    assert isinstance(out2, list) and out2[0]["symbol"] == "TSLA"


@patch.object(AlpacaClient, "account")
def test_ping_variants(mock_acc, caplog):
    caplog.set_level(logging.INFO)
    c = AlpacaClient(api_key="K", api_secret="S")

    mock_acc.return_value = {"status": "ACTIVE"}
    assert c.ping() is True

    mock_acc.return_value = None
    assert c.ping() is False

    mock_acc.return_value = {"status": None}
    assert c.ping() is False

    mock_acc.side_effect = AlpacaAPIError("fail")
    assert c.ping() is False
    assert "ping failed" in caplog.text

    mock_acc.side_effect = Exception("boom")
    assert c.ping() is False
    assert "Unexpected ping error" in caplog.text
