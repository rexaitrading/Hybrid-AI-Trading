"""
Polygon News Client (Hybrid AI Quant Pro v1.0 – OE Grade)
- Wraps Polygon v2 news endpoint
- Env var: POLYGON_KEY or POLYGON_API_KEY
- Normalizes to: {id, author, created, title, url, stocks:[{name,exchange}], source:"polygon"}
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

import requests

logger = logging.getLogger("hybrid_ai_trading.data.clients.polygon_news_client")


class PolygonAPIError(Exception): ...


class PolygonNewsClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.polygon.io"):
        self.api_key = api_key or os.getenv("POLYGON_KEY") or os.getenv("POLYGON_API_KEY")
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            logger.error(" POLYGON_KEY missing")
            raise PolygonAPIError("Polygon API key not provided")
        logger.info(" PolygonNewsClient initialized")

    def get_news(
        self, symbol: Optional[str] = None, limit: int = 10, date_from: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/v2/reference/news"
        params: Dict[str, Any] = {"limit": int(limit), "apiKey": self.api_key}
        if symbol:
            params["ticker"] = symbol
        if date_from:
            params["published_utc.gte"] = f"{date_from}T00:00:00Z"
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data: Union[Dict[str, Any], List[Dict[str, Any]]] = resp.json()
        except Exception as e:
            logger.error(" Polygon news request failed: %s", e)
            raise PolygonAPIError(str(e))

        results = []
        if isinstance(data, dict):
            results = data.get("results") or data.get("data") or []
        elif isinstance(data, list):
            results = data

        items: List[Dict[str, Any]] = []
        for it in results:
            story_id = it.get("id") or it.get("news_id") or it.get("guid") or it.get("url")
            created = it.get("published_utc") or it.get("timestamp") or it.get("created_at") or ""
            title = it.get("title") or it.get("headline") or ""
            url_out = it.get("article_url") or it.get("url") or ""
            author = it.get("author") or ""
            tickers = it.get("tickers") or it.get("symbols") or []
            if isinstance(tickers, str):
                tickers = [tickers]
            stocks: List[Dict[str, str]] = []
            for t in tickers or []:
                nm = t.get("ticker") if isinstance(t, dict) else str(t)
                nm = (nm or "").strip().upper()
                if nm:
                    stocks.append({"name": nm, "exchange": ""})
            items.append(
                {
                    "id": story_id,
                    "author": author,
                    "created": created,
                    "updated": created,
                    "title": title,
                    "teaser": "",
                    "body": "",
                    "url": url_out,
                    "image": [],
                    "channels": [],
                    "stocks": stocks,
                    "tags": [],
                    "source": "polygon",
                }
            )
        return items
