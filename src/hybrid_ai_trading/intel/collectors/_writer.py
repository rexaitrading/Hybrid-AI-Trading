from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _try_parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    ss = str(s).strip()
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
        # RSS pubDate etc. may not be ISO; treat as unknown
        return None

def _sha1(s: str) -> str:
    return "sha1:" + hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def make_id(kind: str, title: str, url: str, created_iso: str, symbols: List[str]) -> str:
    day = (created_iso or "")[:10]
    sym = ",".join(sorted({(x or "").upper() for x in (symbols or []) if (x or "").strip()}))
    base = f"{kind}|{(title or '').strip().lower()}|{(url or '').strip()}|{day}|{sym}"
    return _sha1(base)

def normalize_record(
    *,
    kind: str,
    provider: str,
    title: str,
    url: str,
    created: str,
    symbols: List[str],
    raw: Dict[str, Any],
) -> Dict[str, Any]:
    created_dt = _try_parse_iso(created) or _utc_now()
    created_iso = _iso(created_dt)
    syms = sorted({(s or "").strip().upper() for s in (symbols or []) if (s or "").strip()})
    return {
        "ts_utc": _iso(_utc_now()),
        "kind": kind,
        "provider": (provider or "").strip(),
        "id": make_id(kind, title, url, created_iso, syms),
        "created": created_iso,
        "title": (title or "").strip(),
        "url": (url or "").strip(),
        "symbols": syms,
        "raw": raw or {},
    }

def load_existing_ids(path: Path, max_lines_scan: int = 20000) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for ln in lines[-max_lines_scan:]:
            s = (ln or "").strip()
            if not s:
                continue
            try:
                j = json.loads(s)
                if isinstance(j, dict):
                    rid = (j.get("id") or "").strip()
                    if rid:
                        ids.add(rid)
            except Exception:
                continue
    except Exception:
        return set()
    return ids

def write_jsonl_atomic_append(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def filter_fresh(rows: List[Dict[str, Any]], hours_back: int) -> List[Dict[str, Any]]:
    if hours_back <= 0:
        return rows
    cutoff = _utc_now() - timedelta(hours=hours_back)
    out: List[Dict[str, Any]] = []
    for r in rows:
        dt = _try_parse_iso((r.get("created") or ""))
        if dt is None or dt >= cutoff:
            out.append(r)
    return out

def dedupe_new(rows: List[Dict[str, Any]], existing_ids: set[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        rid = (r.get("id") or "").strip()
        if not rid:
            continue
        if rid in existing_ids:
            continue
        existing_ids.add(rid)
        out.append(r)
    return out
