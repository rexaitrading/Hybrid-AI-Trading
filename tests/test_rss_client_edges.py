import types

import feedparser as _feed

from hybrid_ai_trading.data.clients.rss_client import RSSClient


def test_rss_yahoo_and_extra(monkeypatch):
    e1 = types.SimpleNamespace(link="u1", title="AAPL gains", author="a", published="p")
    e2 = types.SimpleNamespace(link="u2", title="Generic feed", author="a", published="p")
    parsed1 = types.SimpleNamespace(entries=[e1])
    parsed2 = types.SimpleNamespace(entries=[e2])
    calls = {"n": 0}

    def parse(url):
        calls["n"] += 1
        return parsed1 if calls["n"] == 1 else parsed2

    monkeypatch.setattr(_feed, "parse", parse)
    out = RSSClient(
        google_template=None,
        yahoo_template="http://y?s={sym}",
        extra_feeds=["http://extra"],
        per_feed_max=5,
    ).get_news("AAPL")
    assert out[0]["stocks"] and out[0]["stocks"][0]["name"] == "AAPL" and out[1]["stocks"] == []
