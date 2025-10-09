import types
from hybrid_ai_trading.data.clients.rss_client import RSSClient
import feedparser as _feed

def test_rss_basic(monkeypatch):
    entry = types.SimpleNamespace(link="https://example.com/r", title="GOOGL gains", author="rss",
                                  published="2025-10-01T10:00:00Z")
    parsed = types.SimpleNamespace(entries=[entry])
    monkeypatch.setattr(_feed, "parse", lambda url: parsed)
    c = RSSClient(google_template="http://x?q={sym}", yahoo_template=None, extra_feeds=[], per_feed_max=5)
    out = c.get_news("GOOGL", date_from="2025-09-30")
    assert out and out[0]["title"].startswith("GOOGL")
    assert out[0]["stocks"][0]["name"] == "GOOGL"