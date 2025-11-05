from __future__ import annotations

from hybrid_ai_trading.utils.time_utils import utc_now

"""
News Client (Hybrid AI Quant Pro v2.1 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ Hedge Fund OE Grade, DB-Integrated)
---------------------------------------------------------------------------
Responsibilities:
- Fetch normalized news from provider APIs (Polygon, Benzinga, etc.)
- Normalize and upsert into News table (SQLAlchemy-backed)
- Provide query helpers for latest headlines
- Structured logging & robust error handling
"""


import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.exc import IntegrityError

from hybrid_ai_trading.data.store.database import News, SessionLocal

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logger = logging.getLogger("hybrid_ai_trading.data.clients.news_client")


# ---------------------------------------------------------------------
# Normalization Helpers
# ---------------------------------------------------------------------
def _normalize_article(article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert API response dict into News table schema.

    Returns:
        dict with keys (article_id, created, title, url, symbols),
        or None if parsing fails.
    """
    try:
        return {
            "article_id": str(article.get("id") or article.get("article_id")),
            "created": (
                datetime.fromisoformat(
                    article.get("published_utc").replace("Z", "+00:00")
                )
                if article.get("published_utc")
                else utc_now()
            ),
            "title": article.get("title", "") or "",
            "url": article.get("url", "") or "",
            "symbols": ",".join(article.get("tickers", []) or []),
        }
    except Exception as e:
        logger.error(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Failed to normalize article: %s",
            e,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------
def fetch_polygon_news(
    limit: int = 10, ticker: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch latest news from Polygon.io.

    Args:
        limit: number of articles to fetch (default=10)
        ticker: optional symbol filter (e.g., "AAPL")

    Returns:
        list of article dicts (raw API response)
    """
    polygon_key = os.getenv("POLYGON_KEY")  # dynamic lookup
    if not polygon_key:
        logger.warning(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â POLYGON_KEY not set ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ skipping Polygon news fetch"
        )
        return []

    url = "https://api.polygon.io/v2/reference/news"
    params: Dict[str, Any] = {"apiKey": polygon_key, "limit": limit}
    if ticker:
        params["ticker"] = ticker

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        logger.info(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Polygon news fetched | count=%s",
            len(results),
        )
        return results
    except Exception as e:
        logger.error(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Polygon news fetch failed: %s",
            e,
            exc_info=True,
        )
        return []


def fetch_benzinga_news(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch latest news from Benzinga (if API key is available).

    Args:
        symbol: ticker symbol (e.g., "AAPL")
        limit: number of articles

    Returns:
        list of article dicts (raw API response)
    """
    benzinga_key = os.getenv("BENZINGA_KEY")  # dynamic lookup
    if not benzinga_key:
        logger.warning(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¸Ãƒâ€šÃ‚Â BENZINGA_KEY not set ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ skipping Benzinga news fetch"
        )
        return []

    url = "https://api.benzinga.com/api/v2/news"
    params: Dict[str, Any] = {"token": benzinga_key, "symbols": symbol, "limit": limit}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            logger.info(
                "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Benzinga news fetched | symbol=%s count=%s",
                symbol,
                len(data),
            )
            return data.get("articles", [])
        logger.error(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Benzinga response invalid format: %s",
            type(data),
        )
        return []
    except Exception as e:
        logger.error(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Benzinga news fetch failed: %s",
            e,
            exc_info=True,
        )
        return []


# ---------------------------------------------------------------------
# DB Integration
# ---------------------------------------------------------------------
def save_articles(articles: List[Dict[str, Any]]) -> int:
    """
    Upsert list of normalized articles into News table.

    Args:
        articles: list of article dicts (raw API responses)

    Returns:
        number of successfully saved new articles
    """
    session = SessionLocal()
    count = 0
    try:
        for art in articles:
            norm = _normalize_article(art)
            if not norm:
                continue
            news = News(**norm)
            try:
                session.add(news)
                session.commit()
                count += 1
            except IntegrityError:
                session.rollback()  # already exists
        logger.info("ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã¢â‚¬Å“ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ Saved %d new articles", count)
        return count
    except Exception as e:
        logger.error(
            "ÃƒÆ’Ã‚Â¢Ãƒâ€šÃ‚ÂÃƒâ€¦Ã¢â‚¬â„¢ Failed saving articles: %s", e, exc_info=True
        )
        session.rollback()
        return count
    finally:
        session.close()


def get_latest_headlines(
    limit: int = 10, symbol: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query latest headlines from DB for sentiment filter.

    Args:
        limit: maximum number of headlines to return
        symbol: optional ticker filter

    Returns:
        list of headline dicts
    """
    session = SessionLocal()
    try:
        q = session.query(News).order_by(News.created.desc())
        if symbol:
            q = q.filter(News.symbols.contains(symbol))
        rows = q.limit(limit).all()
        return [
            {"title": r.title, "symbols": r.symbols, "url": r.url, "created": r.created}
            for r in rows
        ]
    finally:
        session.close()
