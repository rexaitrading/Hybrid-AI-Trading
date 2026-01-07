"""
Intel News Bridge (Phase6/Phase7 wiring)
Reads local intel feeds first and normalizes to NewsAggregator-like story schema:
{created,title,url,source,stocks:[{name:SYM},...]}

Priority order:
  logs/.intel/* -> logs/* -> src/.intel/*
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for ln in path.read_text(encoding="utf-8").splitlines():
            s = (ln or "").strip()
            if not s:
                continue
            try:
                j = json.loads(s)
                if isinstance(j, dict):
                    out.append(j)
            except Exception:
                continue
    except Exception:
        return []
    return out

def _try_iso_to_utc(s: str) -> Optional[datetime]:
    if not s:
        return None
    ss = s.strip()
    if not ss:
        return None
    try:
        if ss.endswith("Z"):
            ss = ss[:-1] + "+00:00"
        dt = datetime.fromisoformat(ss)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _date_ge(created: str, date_from_yyyy_mm_dd: str) -> bool:
    if not date_from_yyyy_mm_dd:
        return True
    dt = _try_iso_to_utc(created or "")
    if dt is None:
        return True
    try:
        df = datetime.fromisoformat(date_from_yyyy_mm_dd + "T00:00:00+00:00")
    except Exception:
        return True
    return dt >= df

def _norm_symbols(rec: Dict[str, Any]) -> List[str]:
    syms: List[str] = []
    if isinstance(rec.get("symbols"), list):
        for x in rec["symbols"]:
            if isinstance(x, str) and x.strip():
                syms.append(x.strip().upper())
    if isinstance(rec.get("stocks"), list):
        for x in rec["stocks"]:
            if isinstance(x, dict):
                nm = (x.get("name") or "").strip().upper()
                if nm:
                    syms.append(nm)
    for k in ("symbol", "ticker"):
        v = (rec.get(k) or "").strip().upper()
        if v:
            syms.append(v)

    seen = set()
    out: List[str] = []
    for s in syms:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

def _to_story(rec: Dict[str, Any], source_label: str) -> Optional[Dict[str, Any]]:
    title = (rec.get("title") or rec.get("headline") or "").strip()
    if not title:
        return None
    created = (rec.get("created") or rec.get("published_at") or rec.get("ts_utc") or "").strip()
    url = (rec.get("url") or rec.get("link") or "").strip()
    stocks = [{"name": s} for s in _norm_symbols(rec)]
    return {
        "created": created,
        "title": title,
        "url": url,
        "source": (rec.get("source") or source_label or "").strip(),
        "stocks": stocks,
    }

def aggregate_news_intel(symbols_csv: str, limit: int, date_from: str) -> List[Dict[str, Any]]:
    watch = {s.strip().upper() for s in (symbols_csv or "").split(",") if s.strip()}
    if not watch:
        return []

    root = _repo_root()
    candidates = [
        root / "logs" / ".intel" / "news_feed.jsonl",
        root / "logs" / "news_feed.jsonl",
        root / "src" / ".intel" / "news_feed.jsonl",
        root / "logs" / ".intel" / "youtube_feed.jsonl",
        root / "logs" / "youtube_feed.jsonl",
        root / "src" / ".intel" / "youtube_feed.jsonl",
    ]

    out: List[Dict[str, Any]] = []
    for p in candidates:
        rows = _read_jsonl(p)
        if not rows:
            continue
        for r in rows:
            st = _to_story(r, source_label=p.name)
            if not st:
                continue
            syms = [x.get("name","").upper() for x in st.get("stocks", []) if isinstance(x, dict)]
            if not any(s in watch for s in syms):
                continue
            if not _date_ge(st.get("created",""), date_from):
                continue
            out.append(st)
            if limit and len(out) >= limit:
                return out
        if out:
            break
    return out
