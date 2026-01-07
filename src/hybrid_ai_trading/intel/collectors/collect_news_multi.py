from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._writer import normalize_record, load_existing_ids, dedupe_new, filter_fresh, write_jsonl_atomic_append

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]

def _watchlist() -> List[str]:
    s = (os.getenv("HAT_INTEL_WATCHLIST") or "NVDA,SPY,QQQ").strip()
    out = [x.strip().upper() for x in s.split(",") if x.strip()]
    return sorted(set(out))

def _tag_symbols_from_text(text: str, watch: List[str]) -> List[str]:
    t = (text or "").upper()
    syms: List[str] = []
    for sym in watch:
        if re.search(rf"(?<![A-Z0-9]){re.escape(sym)}(?![A-Z0-9])", t):
            syms.append(sym)
    return syms

def _env_providers() -> List[str]:
    s = (os.getenv("HAT_NEWS_PROVIDERS") or "").strip().lower()
    if not s:
        return ["polygon","benzinga","alpaca","rss"]
    return [x.strip() for x in s.split(",") if x.strip()]

def _collect_polygon(watch: List[str], limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    from hybrid_ai_trading.data.clients.polygon_news_client import PolygonNewsClient  # type: ignore
    c = PolygonNewsClient()
    for sym in watch:
        items = None
        for name in ("get_news","get_ticker_news","fetch_news","list_news"):
            if hasattr(c, name):
                items = getattr(c, name)(sym, limit=limit)
                break
        if items is None:
            continue
        for it in (items or []):
            title = (it.get("title") if isinstance(it, dict) else "") or ""
            url = (it.get("url") if isinstance(it, dict) else "") or ""
            created = (it.get("published_utc") if isinstance(it, dict) else "") or (it.get("created") if isinstance(it, dict) else "") or ""
            syms = [sym] if sym else _tag_symbols_from_text(title, watch)
            rows.append(normalize_record(
                kind="news", provider="polygon",
                title=title, url=url, created=str(created),
                symbols=syms,
                raw={"provider":"polygon"},
            ))
    return rows

def _collect_benzinga(watch: List[str], limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient  # type: ignore
    c = BenzingaClient()
    for sym in watch:
        items = None
        for name in ("get_news","fetch_news","list_news"):
            if hasattr(c, name):
                items = getattr(c, name)(sym, limit=limit)
                break
        if items is None:
            continue
        for it in (items or []):
            title = (it.get("title") if isinstance(it, dict) else "") or ""
            url = (it.get("url") if isinstance(it, dict) else "") or ""
            created = (it.get("created") if isinstance(it, dict) else "") or (it.get("published") if isinstance(it, dict) else "") or ""
            syms = [sym] if sym else _tag_symbols_from_text(title, watch)
            rows.append(normalize_record(
                kind="news", provider="benzinga",
                title=title, url=url, created=str(created),
                symbols=syms,
                raw={"provider":"benzinga"},
            ))
    return rows

def _collect_alpaca(watch: List[str], limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    from hybrid_ai_trading.data.clients.alpaca_news_client import AlpacaNewsClient  # type: ignore
    c = AlpacaNewsClient()
    for sym in watch:
        items = None
        for name in ("get_news","fetch_news","list_news"):
            if hasattr(c, name):
                items = getattr(c, name)(sym, limit=limit)
                break
        if items is None:
            continue
        for it in (items or []):
            title = (it.get("headline") if isinstance(it, dict) else "") or (it.get("title") if isinstance(it, dict) else "") or ""
            url = (it.get("url") if isinstance(it, dict) else "") or ""
            created = (it.get("created_at") if isinstance(it, dict) else "") or (it.get("created") if isinstance(it, dict) else "") or ""
            syms = [sym] if sym else _tag_symbols_from_text(title, watch)
            rows.append(normalize_record(
                kind="news", provider="alpaca",
                title=title, url=url, created=str(created),
                symbols=syms,
                raw={"provider":"alpaca"},
            ))
    return rows

def _collect_rss(watch: List[str], limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        from hybrid_ai_trading.data.clients.rss_client import RssClient  # type: ignore
    except Exception:
        return rows
    c = RssClient()
    items = None
    for name in ("get_items","fetch","fetch_items","get_news"):
        if hasattr(c, name):
            items = getattr(c, name)(limit=limit)
            break
    if not items:
        return rows
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        url = (it.get("url") or it.get("link") or "").strip()
        created = (it.get("published") or it.get("pubDate") or it.get("created") or "")
        syms = it.get("symbols") or _tag_symbols_from_text(title, watch)
        if not syms:
            continue
        rows.append(normalize_record(
            kind="news", provider="rss",
            title=title, url=url, created=str(created),
            symbols=list(syms),
            raw={"provider":"rss"},
        ))
    return rows

def collect(hours_back: int = 24, limit_total: int = 80) -> Tuple[bool, str, int]:
    repo = _repo_root()
    out_path = repo / "src" / ".intel" / "news_feed.jsonl"
    watch = _watchlist()
    providers = _env_providers()

    existing = load_existing_ids(out_path)
    rows: List[Dict[str, Any]] = []
    per = max(5, int(limit_total // max(1, len(providers))))

    try:
        for p in providers:
            try:
                if p == "polygon":
                    rows.extend(_collect_polygon(watch, per))
                elif p == "benzinga":
                    rows.extend(_collect_benzinga(watch, per))
                elif p == "alpaca":
                    rows.extend(_collect_alpaca(watch, per))
                elif p == "rss":
                    rows.extend(_collect_rss(watch, per))
            except Exception as e:
                return (False, f"provider_fail:{p}:{type(e).__name__}:{e}", 0)
    except Exception as e:
        return (False, f"news_multi_error:{type(e).__name__}:{e}", 0)

    rows = filter_fresh(rows, hours_back=hours_back)
    rows = dedupe_new(rows, existing)

    if rows:
        write_jsonl_atomic_append(out_path, rows)

    return (True, "ok", len(rows))
