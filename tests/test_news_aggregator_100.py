import os

import yaml

from hybrid_ai_trading.data import news_aggregator as agg

CFG = "config/config.yaml"


class BZ:
    def get_news(self, s, limit=10, date_from=None):
        return [
            {
                "id": "bz1",
                "url": "https://same",
                "title": "META bz",
                "stocks": [{"name": "META", "exchange": ""}],
            }
        ]


class PG:
    def __init__(self, calls):
        self.calls = calls

    def get_news(self, sym, limit=5, date_from=None):
        self.calls.append(limit)
        return [
            {
                "id": "pg1",
                "url": "https://same",
                "title": f"{sym} pg",
                "stocks": [{"name": sym, "exchange": ""}],
            }
        ]


class AP:
    def get_news(self, s, limit=10, date_from=None):
        return [
            {
                "id": "ap1",
                "url": "https://ap",
                "title": "AAPL ap",
                "stocks": [{"name": "AAPL", "exchange": ""}],
                "source": "alpaca",
            }
        ]


class RSS:
    def __init__(self, *a, **k):
        pass

    def get_news(self, s, date_from=None):
        return [
            {
                "id": "r1",
                "url": "https://r",
                "title": "AAPL r",
                "stocks": [{"name": "AAPL", "exchange": ""}],
            }
        ]


def write_cfg(np):
    os.makedirs("config", exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        yaml.safe_dump({"news_providers": np}, f, sort_keys=False)


def test_only_polygon_and_per_symbol_limit(monkeypatch):
    calls = []
    write_cfg(
        {
            "aggregate": True,
            "benzinga": {"enabled": False},
            "polygon": {"enabled": True},
            "alpaca": {"enabled": False},
            "rss": {"enabled": False},
        }
    )
    monkeypatch.setattr(agg, "PolygonNewsClient", lambda: PG(calls))
    out = agg.aggregate_news("AAPL,META,TSLA", limit=12, date_from="2025-09-30")
    # per-symbol limit should be round(12/3)=4
    assert calls and all(c == 4 for c in calls)


def test_url_first_dedupe_and_source_tagging(monkeypatch):
    write_cfg(
        {
            "aggregate": True,
            "benzinga": {"enabled": True},
            "polygon": {"enabled": True},
            "alpaca": {"enabled": True},
            "rss": {"enabled": True},
        }
    )
    monkeypatch.setattr(agg, "BenzingaClient", lambda: BZ())
    calls = []
    monkeypatch.setattr(agg, "PolygonNewsClient", lambda: PG(calls))
    monkeypatch.setattr(agg, "AlpacaNewsClient", lambda: AP())
    monkeypatch.setattr(agg, "RSSClient", lambda *a, **k: RSS())
    out = agg.aggregate_news("AAPL,META", limit=6, date_from="2025-09-30")
    urls = [s["url"] for s in out]
    # 'https://same' appears once (URL dedupe wins before SID)
    assert urls.count("https://same") == 1
    # ensure items missing 'source' got annotated
    assert all("source" in s for s in out)
