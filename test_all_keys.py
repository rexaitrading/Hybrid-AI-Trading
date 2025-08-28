import os
import pytest
from unittest.mock import patch, MagicMock
import requests


def _make_mock_response(status_code=200, json_data=None, text_data=None):
    mock_resp = MagicMock(status_code=status_code)
    if json_data:
        mock_resp.json.return_value = json_data
    else:
        mock_resp.json.side_effect = ValueError("No JSON")
    if text_data:
        mock_resp.text = text_data
    return mock_resp


@patch("requests.get")
def test_polygon_api(mock_get, monkeypatch):
    monkeypatch.setenv("POLYGON_KEY", "FAKE_KEY")
    mock_get.return_value = _make_mock_response(
        200, {"status": "OK"}
    )

    key = os.getenv("POLYGON_KEY")
    url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey={key}"
    r = requests.get(url)
    assert r.status_code == 200
    assert r.json()["status"] == "OK"


@patch("requests.get")
def test_coinapi_api(mock_get, monkeypatch):
    monkeypatch.setenv("COINAPI_KEY", "FAKE_KEY")
    mock_get.return_value = _make_mock_response(200, {"rate": 123.45})

    url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
    r = requests.get(url, headers={"X-CoinAPI-Key": os.getenv("COINAPI_KEY")})
    assert r.status_code == 200
    assert "rate" in r.json()


@patch("requests.get")
def test_alpaca_api(mock_get, monkeypatch):
    monkeypatch.setenv("ALPACA_KEY", "FAKE_KEY")
    monkeypatch.setenv("ALPACA_SECRET", "FAKE_SECRET")
    mock_get.return_value = _make_mock_response(200, {"id": "account-id"})

    url = "https://paper-api.alpaca.markets/v2/account"
    r = requests.get(url, headers={
        "APCA-API-KEY-ID": os.getenv("ALPACA_KEY"),
        "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET"),
    })
    assert r.status_code == 200
    assert "id" in r.json()


@patch("requests.get")
def test_benzinga_api(mock_get, monkeypatch):
    monkeypatch.setenv("BENZINGA_KEY", "FAKE_KEY")
    mock_get.return_value = _make_mock_response(200, {"success": True})

    key = os.getenv("BENZINGA_KEY")
    url = f"https://api.benzinga.com/api/v2.1/calendar/earnings?token={key}"
    r = requests.get(url)
    assert r.status_code == 200
    assert r.json()["success"] is True
