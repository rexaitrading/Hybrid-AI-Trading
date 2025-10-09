import os
from unittest.mock import MagicMock, patch

import pytest
import requests


def test_coinapi_key_missing(monkeypatch):
    monkeypatch.delenv("COINAPI_KEY", raising=False)
    assert os.getenv("COINAPI_KEY") is None


@patch("requests.get")
def test_coinapi_account_success(mock_get, monkeypatch):
    monkeypatch.setenv("COINAPI_KEY", "FAKE_KEY")

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"id": "demo", "status": "active"}
    mock_get.return_value = mock_resp

    url = "https://rest.coinapi.io/v1/some_endpoint"
    r = requests.get(url, headers={"X-CoinAPI-Key": os.getenv("COINAPI_KEY")})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


@patch("requests.get")
def test_coinapi_account_failure(mock_get, monkeypatch):
    monkeypatch.setenv("COINAPI_KEY", "FAKE_KEY")

    mock_resp = MagicMock(status_code=401)
    mock_resp.text = "Unauthorized"
    mock_resp.json.side_effect = ValueError("Bad JSON")
    mock_get.return_value = mock_resp

    url = "https://rest.coinapi.io/v1/some_endpoint"
    r = requests.get(url, headers={"X-CoinAPI-Key": os.getenv("COINAPI_KEY")})

    assert r.status_code == 401
    with pytest.raises(ValueError):
        _ = r.json()
