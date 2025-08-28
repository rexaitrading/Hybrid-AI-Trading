import os
import pytest
from unittest.mock import patch, MagicMock
import requests


def test_missing_env_vars(monkeypatch):
    monkeypatch.delenv("ALPACA_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET", raising=False)
    assert os.getenv("ALPACA_KEY") is None
    assert os.getenv("ALPACA_SECRET") is None


def test_env_vars_present(monkeypatch):
    monkeypatch.setenv("ALPACA_KEY", "FAKE_KEY")
    monkeypatch.setenv("ALPACA_SECRET", "FAKE_SECRET")
    assert os.getenv("ALPACA_KEY") == "FAKE_KEY"
    assert os.getenv("ALPACA_SECRET") == "FAKE_SECRET"


@patch("requests.get")
def test_account_request_success(mock_get, monkeypatch):
    monkeypatch.setenv("ALPACA_KEY", "FAKE_KEY")
    monkeypatch.setenv("ALPACA_SECRET", "FAKE_SECRET")

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"id": "account-id", "status": "ACTIVE"}
    mock_get.return_value = mock_resp

    url = "https://paper-api.alpaca.markets/v2/account"
    r = requests.get(url, headers={
        "APCA-API-KEY-ID": os.getenv("ALPACA_KEY"),
        "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET"),
    }, timeout=15)

    assert r.status_code == 200
    assert r.json()["status"] == "ACTIVE"


@patch("requests.get")
def test_account_request_failure(mock_get, monkeypatch):
    monkeypatch.setenv("ALPACA_KEY", "FAKE_KEY")
    monkeypatch.setenv("ALPACA_SECRET", "FAKE_SECRET")

    mock_resp = MagicMock(status_code=403)
    mock_resp.text = "Forbidden"
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_resp

    url = "https://paper-api.alpaca.markets/v2/account"
    r = requests.get(url, headers={
        "APCA-API-KEY-ID": os.getenv("ALPACA_KEY"),
        "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET"),
    }, timeout=15)

    assert r.status_code == 403
    with pytest.raises(ValueError):
        _ = r.json()
