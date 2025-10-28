"""
Alpaca News Client (Hybrid AI Quant Pro v1.0  OE Grade)
- Uses Alpaca Data API news endpoint
- Headers: APCA-API-KEY-ID / APCA-API-SECRET-KEY
- Normalizes to: {id, author, created, title, url, stocks:[{name}], source:"alpaca"}
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("hybrid_ai_trading.data.clients.alpaca_news_client")


class AlpacaAPIError(Exception): ...


class AlpacaNewsClient:
    def __init__(
        self,
        key_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url="https://data.alpaca.markets",
    ):
        self.key_id = key_id or os.getenv("ALPACA_KEY_ID")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.base_url = base_url.rstrip("/")
        if not (self.key_id and self.secret_key):
            logger.error(" Alpaca keys missing (ALPACA_KEY_ID/ALPACA_SECRET_KEY)")
            raise AlpacaAPIError("Alpaca API keys not provided")
        logger.info(" AlpacaNewsClient initialized")

    def get_news(
        self, symbols_csv: str, limit: int = 10, date_from: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/v1beta1/news"
        params: Dict[str, Any] = {"symbols": symbols_csv, "limit": int(limit)}
        if date_from:
            params["start"] = f"{date_from}T00:00:00Z"
        headers = {"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret_key}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error(" Alpaca news request failed: %s", e)
            raise AlpacaAPIError(str(e))
        out = []
        for it in data.get("news", []):
            syms = it.get("symbols") or []
            stocks = [{"name": s.strip().upper(), "exchange": ""} for s in syms if s]
            out.append(
                {
                    "id": it.get("id"),
                    "author": it.get("author", ""),
                    "created": it.get("created_at") or it.get("updated_at") or "",
                    "updated": it.get("updated_at") or "",
                    "title": it.get("headline") or it.get("title") or "",
                    "teaser": it.get("summary") or "",
                    "body": "",
                    "url": it.get("url") or "",
                    "image": [],
                    "channels": [],
                    "stocks": stocks,
                    "tags": [],
                    "source": "alpaca",
                }
            )
        return out
