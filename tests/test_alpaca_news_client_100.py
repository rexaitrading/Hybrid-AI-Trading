import os, pytest, requests as _requests
from hybrid_ai_trading.data.clients.alpaca_news_client import AlpacaNewsClient, AlpacaAPIError

class DR:
    def __init__(self, data, ok=True):
        self._d=data; self.status_code=200 if ok else 500
    def raise_for_status(self): 
        if self.status_code!=200: raise Exception("http")
    def json(self): return self._d

def test_missing_keys_raise():
    os.environ.pop("ALPACA_KEY_ID", None); os.environ.pop("ALPACA_SECRET_KEY", None)
    with pytest.raises(AlpacaAPIError):
        AlpacaNewsClient()

def test_request_exception_wrapped(monkeypatch):
    os.environ["ALPACA_KEY_ID"]="kid"; os.environ["ALPACA_SECRET_KEY"]="sec"
    def boom(*a,**k): raise Exception("net")
    monkeypatch.setattr(_requests,"get", boom)
    c = AlpacaNewsClient()
    with pytest.raises(AlpacaAPIError):
        c.get_news("AAPL",1,"2025-09-30")

def test_updated_at_fallback(monkeypatch):
    os.environ["ALPACA_KEY_ID"]="kid"; os.environ["ALPACA_SECRET_KEY"]="sec"
    data = {"news":[{"id":"n2","author":"a","updated_at":"2025-10-01T15:00:00Z","headline":"AAPL upd","url":"https://x/z","symbols":["AAPL"]}]}
    monkeypatch.setattr(_requests,"get", lambda *a,**k: DR(data))
    out = AlpacaNewsClient().get_news("AAPL",1,"2025-09-30")
    assert out and out[0]["created"].startswith("2025-10-01")