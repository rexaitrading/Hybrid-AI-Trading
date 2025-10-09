import os

import pytest
import requests as _requests

from hybrid_ai_trading.data.clients.polygon_news_client import (
    PolygonAPIError,
    PolygonNewsClient,
)


class DR:
    def __init__(self, data):
        self._d = data
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._d


def test_no_key_raises(monkeypatch):
    # clear keys
    os.environ.pop("POLYGON_KEY", None)
    os.environ.pop("POLYGON_API_KEY", None)
    with pytest.raises(PolygonAPIError):
        PolygonNewsClient()


def test_list_payload_and_empty_tickers(monkeypatch):
    os.environ["POLYGON_KEY"] = "k"
    data = [
        {
            "id": "a",
            "published_utc": "2025-10-01T00:00:00Z",
            "title": "No tickers",
            "url": "https://x/a",
            "tickers": [],
        },
        {
            "id": "b",
            "published_utc": "2025-10-01T01:00:00Z",
            "title": "Str ticker",
            "url": "https://x/b",
            "tickers": "MSFT",
        },
    ]
    monkeypatch.setattr(_requests, "get", lambda *a, **k: DR(data))
    out = PolygonNewsClient().get_news(None, limit=2, date_from="2025-09-30")
    assert len(out) == 2 and out[1]["stocks"][0]["name"] == "MSFT"
