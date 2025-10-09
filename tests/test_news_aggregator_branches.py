import os

import pytest
import yaml

from hybrid_ai_trading.data import news_aggregator as agg

CFG = "config/config.yaml"


class _OKBZ:
    def get_news(self, symbols_csv, limit=10, date_from=None):
        return [
            {
                "id": "sid_dup",
                "url": "https://dup.url",
                "title": "META X",
                "stocks": [{"name": "META", "exchange": ""}],
            }
        ]


class _OKPG:
    def get_news(self, symbol, limit=5, date_from=None):
        return [
            {
                "id": "sid_dup",
                "url": "https://diff.url",
                "title": f"{symbol} Y",
                "stocks": [{"name": symbol, "exchange": ""}],
            }
        ]


class _BoomAP:
    def get_news(self, symbols_csv, limit=10, date_from=None):
        raise Exception("alpaca down")


class _OKRSS:
    def __init__(self, *a, **k):
        pass

    def get_news(self, symbols_csv, date_from=None):
        return [
            {
                "id": "rss1",
                "url": "https://rss",
                "title": "AAPL Z",
                "stocks": [{"name": "AAPL", "exchange": ""}],
            }
        ]


@pytest.fixture(autouse=True)
def cfg(tmp_path):
    os.makedirs("config", exist_ok=True)
    backup = None
    if os.path.exists(CFG):
        with open(CFG, "r", encoding="utf-8") as f:
            backup = f.read()
    cfg = {
        "news_providers": {
            "aggregate": True,
            "benzinga": {"enabled": True},
            "polygon": {"enabled": True},
            "alpaca": {"enabled": True},
            "rss": {
                "enabled": True,
                "per_feed_max": 3,
                "google_template": None,
                "yahoo_template": None,
                "extra_feeds": [],
            },
            "kraken_rss": {"enabled": True, "feeds": ["http://kraken"]},
            "cme_rss": {"enabled": True, "feeds": ["http://cme"]},
        }
    }
    with open(CFG, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    try:
        yield
    finally:
        if backup is None:
            try:
                os.remove(CFG)
            except FileNotFoundError:
                pass
        else:
            with open(CFG, "w", encoding="utf-8") as f:
                f.write(backup)


def test_aggregator_all_paths(monkeypatch):
    monkeypatch.setattr(agg, "BenzingaClient", lambda: _OKBZ())
    monkeypatch.setattr(agg, "PolygonNewsClient", lambda: _OKPG())
    monkeypatch.setattr(agg, "AlpacaNewsClient", lambda: _BoomAP())
    monkeypatch.setattr(agg, "RSSClient", lambda *a, **k: _OKRSS())
    out = agg.aggregate_news("AAPL,META", limit=6, date_from="2025-09-30")
    urls = [s.get("url") for s in out]
    assert urls.count("https://dup.url") == 1
    assert any(s.get("source") in ("rss", "kraken_rss", "cme_rss") for s in out)
