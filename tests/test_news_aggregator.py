import os

import pytest
import yaml

# Import the aggregator module (this module holds the symbols we must patch)
from hybrid_ai_trading.data import news_aggregator as agg

CFG_PATH = "config/config.yaml"


@pytest.fixture(autouse=True)
def _temp_config(tmp_path):
    os.makedirs("config", exist_ok=True)
    backup = None
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            backup = f.read()

    cfg = {
        "news_providers": {
            "aggregate": True,
            "benzinga": {"enabled": True, "weight": 1.0},
            "polygon": {"enabled": True, "weight": 1.0},
            "alpaca": {"enabled": True, "weight": 1.0},
            "rss": {
                "enabled": True,
                "per_feed_max": 3,
                "google_template": None,
                "yahoo_template": None,
                "extra_feeds": [],
            },
        }
    }
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    try:
        yield
    finally:
        if backup is None:
            try:
                os.remove(CFG_PATH)
            except FileNotFoundError:
                pass
        else:
            with open(CFG_PATH, "w", encoding="utf-8") as f:
                f.write(backup)


# ---- Dummy client classes returned by monkeypatch ----
class _DummyBZ:
    def get_news(self, symbols_csv, limit=10, date_from=None):
        # Two stories; one duplicates Polygon by URL
        return [
            {
                "id": "bz1",
                "author": "bz",
                "created": "2025-10-01",
                "title": "AAPL beats estimates",
                "url": "https://example.com/s1",
                "stocks": [{"name": "AAPL", "exchange": ""}],
            },
            {
                "id": "bz_dup",
                "author": "bz",
                "created": "2025-10-01",
                "title": "META update",
                "url": "https://dup.example.com",
                "stocks": [{"name": "META", "exchange": ""}],
            },
        ]


class _DummyPG:
    def get_news(self, symbol, limit=5, date_from=None):
        # Polygon returns dup URL for META; and another for TSLA with empty stocks
        if symbol == "META":
            return [
                {
                    "id": "pg_meta",
                    "author": "pg",
                    "created": "2025-10-01",
                    "title": "META update",
                    "url": "https://dup.example.com",
                    "stocks": [{"name": "META", "exchange": ""}],
                }
            ]
        elif symbol == "TSLA":
            return [
                {
                    "id": "pg_tsla",
                    "author": "pg",
                    "created": "2025-10-01",
                    "title": "TSLA recall",
                    "url": "https://example.com/s2",
                    "stocks": [],
                }
            ]
        else:
            return []


class _DummyAP:
    def get_news(self, symbols_csv, limit=10, date_from=None):
        # One extra story for AAPL
        return [
            {
                "id": "ap_aapl",
                "author": "ap",
                "created": "2025-10-01",
                "title": "AAPL approval",
                "url": "https://example.com/s3",
                "stocks": [{"name": "AAPL", "exchange": ""}],
            }
        ]


class _DummyRSS:
    def __init__(self, *a, **k):
        pass

    def get_news(self, symbols_csv, date_from=None):
        # One RSS generic headline that still tags AAPL
        return [
            {
                "id": "rss_aapl",
                "author": "rss",
                "created": "2025-10-01",
                "title": "Record profit at Apple",
                "url": "https://example.com/s4",
                "stocks": [{"name": "AAPL", "exchange": ""}],
            }
        ]


def test_aggregate_news_dedupe_and_normalize(monkeypatch):
    # IMPORTANT: patch the symbols INSIDE the aggregator module
    monkeypatch.setattr(agg, "BenzingaClient", lambda: _DummyBZ())
    monkeypatch.setattr(agg, "PolygonNewsClient", lambda: _DummyPG())
    monkeypatch.setattr(agg, "AlpacaNewsClient", lambda: _DummyAP())
    monkeypatch.setattr(agg, "RSSClient", lambda *a, **k: _DummyRSS())

    stories = agg.aggregate_news("AAPL,META,TSLA", limit=12, date_from="2025-09-30")

    # Expect dedupe by URL ("https://dup.example.com" appears once)
    urls = [s.get("url") for s in stories]
    assert urls.count("https://dup.example.com") == 1

    # Normalization sanity
    for s in stories:
        assert isinstance(s.get("title", ""), str)
        assert isinstance(s.get("url", ""), str)
        assert isinstance(s.get("stocks", []), list)
        for t in s.get("stocks", []):
            assert isinstance(t.get("name", ""), str)

    # Expect at least AAPL/META/TSLA presence across normalized stories
    symset = {t["name"] for s in stories for t in s.get("stocks", [])}
    assert {"AAPL", "META", "TSLA"} & symset
