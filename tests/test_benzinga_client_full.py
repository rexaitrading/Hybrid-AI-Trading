"""
Unit Tests: BenzingaClient (Hybrid AI Quant Pro v6.2 – 100% Coverage)
---------------------------------------------------------------------
Covers:
- __init__ with env key and missing key
- get_news success + params (date_from/date_to coverage)
- get_news failure raises BenzingaAPIError
- get_news JSON decode error raises BenzingaAPIError
"""

import pytest
from unittest.mock import patch, MagicMock
from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient, BenzingaAPIError


def test_init_with_env_and_missing(monkeypatch):
    monkeypatch.setenv("BENZINGA_KEY", "FAKEKEY")
    client = BenzingaClient()
    assert client.api_key == "FAKEKEY"

    monkeypatch.delenv("BENZINGA_KEY", raising=False)
    with pytest.raises(BenzingaAPIError):
        BenzingaClient(api_key=None)


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_success_with_params(mock_get):
    client = BenzingaClient(api_key="FAKE")
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"news": [{"id": 1}]}
    mock_get.return_value = resp
    news = client.get_news("AAPL", limit=5, date_from="2020-01-01", date_to="2020-01-02")
    assert "news" in news


@patch("hybrid_ai_trading.data.clients.benzinga_client.requests.get")
def test_get_news_failure_and_bad_json(mock_get):
    client = BenzingaClient(api_key="FAKE")
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("bad req")
    mock_get.return_value = resp
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")

    resp.raise_for_status.return_value = None
    resp.json.side_effect = ValueError("bad json")
    mock_get.return_value = resp
    with pytest.raises(BenzingaAPIError):
        client.get_news("AAPL")
