"""
Unit Tests: BenzingaClient (Hybrid AI Quant Pro v11.6 – Hedge-Fund OE Grade, 100% Coverage)
------------------------------------------------------------------------------------------
Covers ALL explicit branches of benzinga_client.py:
- __init__ with env key, without key (raises)
- _mask_key_local: None, short key, long key
- get_news success: no dates, with dates
- get_news failures:
  * HTTP error
  * JSON decoding error
  * JSON returning non-dict
  * Response.json returns None
  * Response missing .json attribute
  * Response.json raises AttributeError
"""

from unittest.mock import MagicMock, patch

import pytest

from hybrid_ai_trading.data.clients.benzinga_client import (
    BenzingaAPIError,
    BenzingaClient,
)


# ----------------------------------------------------------------------
# __init__
# ----------------------------------------------------------------------
def test_init_with_env_and_missing(monkeypatch):
    """Init: picks up env key or raises if missing."""
    monkeypatch.setenv("BENZINGA_KEY", "FAKEKEY")
    client = BenzingaClient()
    assert client.api_key == "FAKEKEY"

    monkeypatch.delenv("BENZINGA_KEY", raising=False)
    with pytest.raises(BenzingaAPIError):
        BenzingaClient(api_key=None)


# ----------------------------------------------------------------------
# _mask_key_local
# ----------------------------------------------------------------------
def test_mask_key_local_variants():
    """Mask key logic: None, short string, long string."""
    assert BenzingaClient._mask_key_local(None) == "None"
    assert BenzingaClient._mask_key_local("short") == "short"
    masked = BenzingaClient._mask_key_local("ABCDEFGHIJKL")
    assert masked.startswith("ABCD") and masked.endswith("IJKL")
    assert "****" in masked


# ----------------------------------------------------------------------
# get_news success paths
# ----------------------------------------------------------------------
@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_success_no_dates_and_with_dates(mock_get):
    """get_news works with and without date filters."""
    client = BenzingaClient(api_key="FAKE")

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"news": [{"id": 1}]}
    mock_get.return_value = resp

    # No dates
    out = client.get_news("AAPL", limit=5)
    assert isinstance(out, dict)
    assert "news" in out

    # With dates
    out2 = client.get_news(
        "AAPL", limit=5, date_from="2020-01-01", date_to="2020-01-02"
    )
    assert "news" in out2

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["date_from"] == "2020-01-01"
    assert kwargs["params"]["date_to"] == "2020-01-02"


# ----------------------------------------------------------------------
# get_news failure paths
# ----------------------------------------------------------------------
@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_http_error(mock_get):
    client = BenzingaClient(api_key="FAKE")
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("bad req")
    mock_get.return_value = resp
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_bad_json(mock_get):
    client = BenzingaClient(api_key="FAKE")
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.side_effect = ValueError("bad json")
    mock_get.return_value = resp
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_non_dict_and_none(mock_get):
    client = BenzingaClient(api_key="FAKE")
    resp = MagicMock()
    resp.raise_for_status.return_value = None

    # Non-dict JSON
    resp.json.return_value = ["not", "a", "dict"]
    mock_get.return_value = resp
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")

    # None JSON
    resp.json.return_value = None
    mock_get.return_value = resp
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_missing_json_attr(mock_get):
    """Response missing .json attribute should raise."""
    client = BenzingaClient(api_key="FAKE")

    class NoJson:
        def raise_for_status(self):
            return None

    mock_get.return_value = NoJson()
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_json_attribute_error(mock_get):
    """Response.json raises AttributeError branch."""
    client = BenzingaClient(api_key="FAKE")

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.side_effect = AttributeError("no json available")
    mock_get.return_value = resp

    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")
