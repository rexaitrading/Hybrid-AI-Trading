import os, yaml, pytest
from hybrid_ai_trading.data import news_aggregator as agg

CFG = "config/config.yaml"

def _write_cfg(np=None):
    os.makedirs("config", exist_ok=True)
    cfg = {} if np is None else {"news_providers": np}
    with open(CFG,"w",encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

class BZ_emptyURL_noSID:
    def get_news(self, s, limit=10, date_from=None):
        return [{"id": None, "url": "", "title": "AAPL naked", "stocks":[{"name":"AAPL","exchange":""}]}]

class BZ_sameURL:
    def get_news(self, s, limit=10, date_from=None):
        return [{"id":"bz1", "url":"https://dup", "title":"META bz", "stocks":[{"name":"META","exchange":""}]}]

class PG_min3:
    def __init__(self, calls): self.calls=calls
    def get_news(self, sym, limit=5, date_from=None):
        self.calls.append(limit)
        return [{"id":f"pg_{sym}","url":f"https://pg/{sym}","title":f"{sym} pg","stocks":[{"name":sym,"exchange":""}]}]

class PG_boom:
    def get_news(self, sym, limit=5, date_from=None):
        raise Exception("polygon net")

class RSS_dummy:
    calls={"n":0}
    def __init__(self,*a,**k): pass
    def get_news(self, s, date_from=None):
        RSS_dummy.calls["n"] += 1
        url = "https://kr" if RSS_dummy.calls["n"]==1 else "https://cm"
        return [{"id":f"rss{RSS_dummy.calls['n']}", "url":url, "title":"rss item", "stocks":[]}]

def test_defaults_when_news_providers_missing(monkeypatch):
    _write_cfg(None)
    monkeypatch.setattr(agg,"BenzingaClient", lambda: BZ_emptyURL_noSID())
    calls=[]
    monkeypatch.setattr(agg,"PolygonNewsClient", lambda: PG_min3(calls))
    out = agg.aggregate_news("AAPL", limit=2, date_from="2025-09-30")
    assert any(s.get("title")=="AAPL naked" for s in out)
    assert any(s.get("url","").startswith("https://pg/") for s in out)

def test_polygon_min3_with_symbols_string(monkeypatch):
    _write_cfg({"aggregate":True,"benzinga":{"enabled":False},"polygon":{"enabled":True},"alpaca":{"enabled":False},"rss":{"enabled":False}})
    calls=[]
    monkeypatch.setattr(agg,"PolygonNewsClient", lambda: PG_min3(calls))
    out = agg.aggregate_news("AAPL", limit=2, date_from="2025-09-30")
    assert calls and all(c==3 for c in calls)
    assert out

def test_polygon_exception_swallowed(monkeypatch):
    _write_cfg({"aggregate":True,"benzinga":{"enabled":False},"polygon":{"enabled":True},"alpaca":{"enabled":False},"rss":{"enabled":False}})
    monkeypatch.setattr(agg,"PolygonNewsClient", lambda: PG_boom())
    out = agg.aggregate_news("AAPL", limit=5, date_from="2025-09-30")
    assert out == []  # swallow exception

def test_url_first_vs_sid_dedupe_and_source_tagging(monkeypatch):
    _write_cfg({"aggregate":True,"benzinga":{"enabled":True},"polygon":{"enabled":True},"alpaca":{"enabled":False},"rss":{"enabled":True}})
    monkeypatch.setattr(agg,"BenzingaClient", lambda: BZ_sameURL())
    calls=[]
    monkeypatch.setattr(agg,"PolygonNewsClient", lambda: PG_min3(calls))
    monkeypatch.setattr(agg,"RSSClient", lambda *a,**k: RSS_dummy())
    out = agg.aggregate_news("META", limit=4, date_from="2025-09-30")
    urls=[s["url"] for s in out]
    assert urls.count("https://dup")==1
    assert any(s.get("source") for s in out)

def test_kraken_and_cme_rss_paths(monkeypatch):
    _write_cfg({"aggregate":True,"benzinga":{"enabled":False},"polygon":{"enabled":False},"alpaca":{"enabled":False},
                "rss":{"enabled":False}, "kraken_rss":{"enabled":True,"feeds":["http://k"]}, "cme_rss":{"enabled":True,"feeds":["http://c"]}})
    RSS_dummy.calls["n"]=0
    monkeypatch.setattr(agg,"RSSClient", lambda *a,**k: RSS_dummy())
    out = agg.aggregate_news("AAPL", limit=5, date_from="2025-09-30")
    sources = {s.get("source") for s in out}
    assert {"kraken_rss","cme_rss"} <= sources

# ---- micro-tests to close the last uncovered lines ----

def test_empty_config_file_triggers_defaults(monkeypatch, tmp_path):
    os.makedirs("config", exist_ok=True)
    with open(CFG,"w",encoding="utf-8") as f: f.write("{}")
    class BZ:
        def get_news(self, s, limit=10, date_from=None):
            return [{"id":"bzE","url":"https://bzE","title":"AAPL E","stocks":[{"name":"AAPL","exchange":""}]}]
    class PG:
        def get_news(self, sym, limit=5, date_from=None):
            return [{"id":"pgE","url":"https://pgE","title":f"{sym} E","stocks":[{"name":sym,"exchange":""}]}]
    monkeypatch.setattr(agg,"BenzingaClient", lambda: BZ())
    monkeypatch.setattr(agg,"PolygonNewsClient", lambda: PG())
    out = agg.aggregate_news("AAPL", limit=2, date_from="2025-09-30")
    assert any(s.get("url") in ("https://bzE","https://pgE") for s in out)

def test_cme_only_rss_branch(monkeypatch, tmp_path):
    os.makedirs("config", exist_ok=True)
    cfg={"news_providers":{"aggregate": True,
                           "benzinga":{"enabled":False},
                           "polygon":{"enabled":False},
                           "alpaca":{"enabled":False},
                           "rss":{"enabled":False},
                           "kraken_rss":{"enabled":False,"feeds":["http://k"]},
                           "cme_rss":{"enabled":True,"feeds":["http://c"]}}}
    with open(CFG,"w",encoding="utf-8") as f: yaml.safe_dump(cfg,f,sort_keys=False)
    class RSSCME:
        def __init__(self,*a,**k): pass
        def get_news(self, s, date_from=None):
            return [{"id":"c1","url":"https://cmeOnly","title":"CME item","stocks":[]}]
    monkeypatch.setattr(agg,"RSSClient", lambda *a,**k: RSSCME())
    out = agg.aggregate_news("AAPL", limit=3, date_from="2025-09-30")
    assert any(s.get("source")=="cme_rss" for s in out)