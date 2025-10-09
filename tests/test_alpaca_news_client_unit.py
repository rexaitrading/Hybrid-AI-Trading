import requests as _requests

from hybrid_ai_trading.data.clients.alpaca_news_client import AlpacaNewsClient


class DR:
    def __init__(self, data):
        self._d = data
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._d


def test_alpaca_news_basic(monkeypatch):
    monkeypatch.setenv("ALPACA_KEY_ID", "kid")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "sec")
    data = {
        "news": [
            {
                "id": "n1",
                "author": "ap",
                "created_at": "2025-10-01T12:00:00Z",
                "headline": "MSFT approval",
                "url": "https://x/a",
                "symbols": ["MSFT"],
            }
        ]
    }
    monkeypatch.setattr(_requests, "get", lambda *a, **k: DR(data))
    out = AlpacaNewsClient().get_news("MSFT", 1, "2025-09-30")
    assert out and out[0]["stocks"][0]["name"] == "MSFT"
