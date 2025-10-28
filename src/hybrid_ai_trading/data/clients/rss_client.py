"""
RSS Client (Hybrid AI Quant Pro v1.0  OE Grade)
- Uses feedparser to pull RSS/Atom feeds for symbols
- Normalizes to: {id, author, created, title, url, stocks:[{name}], source:"rss-*"}
"""
import logging, time
from typing import Any, Dict, List, Optional
import feedparser

logger = logging.getLogger("hybrid_ai_trading.data.clients.rss_client")

class RSSClient:
    def __init__(self, google_template: Optional[str]=None, yahoo_template: Optional[str]=None, extra_feeds: Optional[List[str]]=None, per_feed_max: int=8):
        self.google_template = google_template
        self.yahoo_template  = yahoo_template
        self.extra_feeds     = extra_feeds or []
        self.per_feed_max    = per_feed_max

    def _parse(self, feed_url: str, sym: Optional[str], source_tag: str, date_from: Optional[str]) -> List[Dict[str, Any]]:
        d = feedparser.parse(feed_url)
        out: List[Dict[str, Any]] = []
        for e in d.entries[: self.per_feed_max]:
            link = getattr(e, "link", "") or ""
            title = getattr(e, "title", "") or ""
            author = getattr(e, "author", "") if hasattr(e, "author") else ""
            published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
            stocks = [{"name": sym, "exchange": ""}] if sym else []
            out.append({
                "id": link or title, "author": author, "created": published, "updated": published,
                "title": title, "teaser": "", "body": "", "url": link,
                "image": [], "channels": [], "stocks": stocks, "tags": [], "source": source_tag
            })
        return out

    def get_news(self, symbols_csv: str, date_from: Optional[str]=None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        symbols = [s.strip().upper() for s in symbols_csv.split(",") if s.strip()]
        # per-symbol feeds
        for sym in symbols:
            if self.google_template:
                items += self._parse(self.google_template.format(sym=sym), sym, "rss-google", date_from)
            if self.yahoo_template:
                items += self._parse(self.yahoo_template.format(sym=sym), sym, "rss-yahoo", date_from)
        # extra feeds (not symbolized)
        for u in self.extra_feeds:
            items += self._parse(u, None, "rss-extra", date_from)
        return items
