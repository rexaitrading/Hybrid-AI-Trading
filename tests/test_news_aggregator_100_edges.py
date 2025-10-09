import os, yaml, pytest
from hybrid_ai_trading.data import news_aggregator as agg
CFG="config/config.yaml"

def _write_cfg(np):
    os.makedirs("config", exist_ok=True)
    with open(CFG,"w",encoding="utf-8") as f: yaml.safe_dump({"news_providers":np}, f, sort_keys=False)

class BZ_boom:
    def __init__(self): raise Exception("bz ctor")

class RSS_mix:
    _n={"i":0}
    def __init__(self,*a,**k): pass
    def get_news(self, s, date_from=None):
        RSS_mix._n["i"] += 1
        if RSS_mix._n["i"]==1:
            return [{"id":"k1","url":"https://kr","title":"k","stocks":[]}]
        raise Exception("cme down")

def test_benzinga_ctor_exception_swallowed(monkeypatch):
    _write_cfg({"aggregate":True,"benzinga":{"enabled":True},"polygon":{"enabled":False},"alpaca":{"enabled":False},"rss":{"enabled":False}})
    monkeypatch.setattr(agg,"BenzingaClient", lambda: BZ_boom())
    out = agg.aggregate_news("AAPL", limit=3, date_from="2025-09-30")
    assert out == []

def test_cme_rss_exception_swallowed(monkeypatch):
    _write_cfg({"aggregate":True,"benzinga":{"enabled":False},"polygon":{"enabled":False},"alpaca":{"enabled":False},
                "rss":{"enabled":False}, "kraken_rss":{"enabled":True,"feeds":["http://k"]}, "cme_rss":{"enabled":True,"feeds":["http://c"]}})
    RSS_mix._n["i"]=0
    monkeypatch.setattr(agg,"RSSClient", lambda *a,**k: RSS_mix())
    out = agg.aggregate_news("AAPL", limit=5, date_from="2025-09-30")
    assert any(s.get("source")=="kraken_rss" for s in out)