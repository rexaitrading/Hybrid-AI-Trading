"""
News Aggregator (Hybrid AI Quant Pro v2.0 – OE Grade)
- Combines Benzinga + Polygon + Alpaca + RSS (Google/Yahoo/extra)
- Dedupe by URL first, then (source,id)
"""

from typing import Any, Dict, List

import yaml

from hybrid_ai_trading.data.clients.alpaca_news_client import AlpacaNewsClient
from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient
from hybrid_ai_trading.data.clients.polygon_news_client import PolygonNewsClient
from hybrid_ai_trading.data.clients.rss_client import RSSClient


def aggregate_news(symbols_csv: str, limit: int, date_from: str) -> List[Dict[str, Any]]:
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    np = cfg.get("news_providers") or {}
    news: List[Dict[str, Any]] = []
    seen_url = set()
    seen_sid = set()

    def add_batch(source_name: str, items: List[Dict[str, Any]]):
        for it in items or []:
            u = it.get("url") or ""
            sid = f"{source_name}:{it.get('id')}"
            if u and u in seen_url:
                continue
            if sid in seen_sid:
                continue
            seen_url.add(u) if u else None
            seen_sid.add(sid)
            if "source" not in it:
                it["source"] = source_name
            news.append(it)

    # Benzinga
    if bool((np.get("benzinga") or {}).get("enabled", True)):
        try:
            bz = BenzingaClient()
            add_batch("benzinga", bz.get_news(symbols_csv, limit=limit, date_from=date_from))
        except Exception:
            pass

    # Polygon (per-symbol split tends to recall better)
    if bool((np.get("polygon") or {}).get("enabled", True)):
        try:
            pg = PolygonNewsClient()
            symbols = [s.strip().upper() for s in symbols_csv.split(",") if s.strip()]
            per = max(3, int(round(limit / max(1, len(symbols)))))
            for sym in symbols:
                add_batch("polygon", pg.get_news(sym, limit=per, date_from=date_from))
        except Exception:
            pass

    # Alpaca (single call with symbols CSV)
    if bool((np.get("alpaca") or {}).get("enabled", False)):
        try:
            ap = AlpacaNewsClient()
            add_batch("alpaca", ap.get_news(symbols_csv, limit=limit, date_from=date_from))
        except Exception:
            pass

    # RSS bundle
    rss_cfg = np.get("rss") or {}
    if bool(rss_cfg.get("enabled", True)):
        try:
            client = RSSClient(
                google_template=rss_cfg.get("google_template"),
                yahoo_template=rss_cfg.get("yahoo_template"),
                extra_feeds=rss_cfg.get("extra_feeds") or [],
                per_feed_max=int(rss_cfg.get("per_feed_max", 8)),
            )
            add_batch("rss", client.get_news(symbols_csv, date_from=date_from))
        except Exception:
            pass

    # TODO: kraken_rss / cme_rss  enable easily if desired
    for name in ("kraken_rss", "cme_rss"):
        cfgx = np.get(name) or {}
        if bool(cfgx.get("enabled", False)):
            try:
                client = RSSClient(
                    google_template=None,
                    yahoo_template=None,
                    extra_feeds=cfgx.get("feeds") or [],
                    per_feed_max=10,
                )
                add_batch(name, client.get_news("", date_from=date_from))
            except Exception:
                pass

    return news
