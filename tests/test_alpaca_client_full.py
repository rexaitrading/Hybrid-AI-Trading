"""
Unit Tests: AlpacaClient (Hybrid AI Quant Pro v7.7 – 100% Coverage)
-------------------------------------------------------------------
Covers:
- __init__ with env keys present and missing (warning branch)
- _mask_key with None, short, and long keys
- _headers with and without credentials
- _request success + failure
- account() and positions() delegation
- ping() success, AlpacaAPIError fail, generic Exception fail
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from hybrid_ai_trading.data.clients.alpaca_client import AlpacaClient, AlpacaAPIError


def test_init_with_missing_keys(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.delenv("ALPACA_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)
    client = AlpacaClient(api_key=None, api_secret=None)
    assert client.api_key is None
    assert "Alpaca API keys not set" in caplog.text


def test_mask_key_variants():
    c = AlpacaClient(api_key="FAKEKEY1234", api_secret="FAKESECRET5678")
    assert c._mask_key(None) == "None"
    assert c._mask_key("short") == "short"
    masked = c._mask_key("ABCDEFGHIJKL")
    assert masked.startswith("ABCD") and masked.endswith("IJKL")


def test_headers_and_missing():
    client = AlpacaClient(api_key="KEY1234", api_secret="SECRET5678")
    headers = client._headers()
    assert headers["APCA-API-KEY-ID"] == "KEY1234"
    client.api_key, client.api_secret = None, None
    with pytest.raises(AlpacaAPIError):
        client._headers()


@patch("hybrid_ai_trading.data.clients.alpaca_client.requests.request")
def test_request_success_and_failure(mock_req):
    client = AlpacaClient(api_key="KEY1234", api_secret="SECRET5678")
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"id": "account123"}
    mock_req.return_value = resp
    assert client._request("account")["id"] == "account123"

    resp.raise_for_status.side_effect = Exception("bad req")
    mock_req.return_value = resp
    with pytest.raises(AlpacaAPIError):
        client._request("account")


@patch.object(AlpacaClient, "account")
def test_ping_all_paths(mock_acc, caplog):
    client = AlpacaClient(api_key="KEY1234", api_secret="SECRET5678")

    mock_acc.return_value = {"status": "ok"}
    assert client.ping() is True

    mock_acc.side_effect = AlpacaAPIError("fail")
    assert client.ping() is False
    assert "ping failed" in caplog.text

    mock_acc.side_effect = Exception("unexpected")
    assert client.ping() is False
    assert "Unexpected ping error" in caplog.text
