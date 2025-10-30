import types

import feedparser as _feed

from hybrid_ai_trading.data.clients.rss_client import RSSClient


def test_google_template_and_extra(monkeypatch):
    e_google = types.SimpleNamespace(
        link="g1", title="TSLA gains", author="", published="p"
    )
    e_extra = types.SimpleNamespace(
        link="e1", title="Vendor note", author="", published="p"
    )
    parsed_g = types.SimpleNamespace(entries=[e_google])
    parsed_e = types.SimpleNamespace(entries=[e_extra])
    calls = {"n": 0}

    def parse(url):
        calls["n"] += 1
        return parsed_g if calls["n"] == 1 else parsed_e

    monkeypatch.setattr(_feed, "parse", parse)
    c = RSSClient(
        google_template="http://g?q={sym}",
        yahoo_template=None,
        extra_feeds=["http://extra"],
        per_feed_max=3,
    )
    out = c.get_news("TSLA")
    assert out[0]["stocks"][0]["name"] == "TSLA" and out[1]["stocks"] == []
