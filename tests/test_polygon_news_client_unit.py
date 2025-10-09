import os, requests as _requests
from hybrid_ai_trading.data.clients.polygon_news_client import PolygonNewsClient
class DR: 
    def __init__(self, data): self._d=data; self.status_code=200
    def raise_for_status(self): pass
    def json(self): return self._d
def test_polygon_normalization(monkeypatch):
    monkeypatch.setenv("POLYGON_KEY","poly_test")
    data={"results":[
        {"id":"id1","published_utc":"2025-10-01T12:00:00Z","title":"AAPL H","article_url":"https://x/p1","tickers":["AAPL"]},
        {"id":"id2","published_utc":"2025-10-01T13:00:00Z","title":"META H","url":"https://x/p2","tickers":[{"ticker":"META"}]}]}
    monkeypatch.setattr(_requests,"get",lambda *a,**k:DR(data))
    c=PolygonNewsClient(); out=c.get_news("AAPL",2,"2025-09-30")
    assert len(out)==2 and out[0]["stocks"][0]["name"]=="AAPL" and out[1]["stocks"][0]["name"]=="META"