"""RSS client (optional feedparser).

This client fetches RSS/Atom feeds when `feedparser` is available.
If the dependency is missing, constructor raises ImportError,
and `fetch` will early-return [] to allow optional usage in tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import feedparser  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    feedparser = None  # type: ignore[attr-defined]


class RSSClient:
    """Thin wrapper around `feedparser.parse` with optional dependency guard."""

    def __init__(self, user_agent: str = "HybridAITrading/1.0 (RSSClient)") -> None:
        if feedparser is None:
            raise ImportError(
                "feedparser not installed; RSS features are optional. "
                "Install with: pip install feedparser"
            )
        self.user_agent = user_agent

    def fetch(self, url: str, timeout: int = 10) -> List[Dict[str, Any]]:
        """Fetch and normalize entries from an RSS/Atom feed.

        Returns an empty list if feedparser is unavailable or parsing fails.
        """
        if feedparser is None:
            return []

        try:
            parsed = feedparser.parse(
                url,
                request_headers={"User-Agent": self.user_agent},
            )
        except Exception:
            return []

        entries: List[Dict[str, Any]] = []
        for e in getattr(parsed, "entries", []) or []:
            entries.append(
                {
                    "title": getattr(e, "title", None),
                    "link": getattr(e, "link", None),
                    "published": getattr(e, "published", None),
                    "summary": getattr(e, "summary", None),
                }
            )
        return entries
