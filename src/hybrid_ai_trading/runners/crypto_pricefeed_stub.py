from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(path: Path, msg: str) -> None:
    try:
        p = path.parent / "pricefeed_err.log"
        with p.open("a", encoding="utf-8") as f:
            f.write(f"[{_ts()}] {msg}\n")
    except Exception:
        pass


def read_prices_from_json(path: Path) -> Optional[Dict[str, float]]:
    if not path.exists():
        _log(path, f"missing path={path}")
        return None

    try:
        raw = path.read_text(encoding="utf-8-sig")
        _log(path, f"read_ok path={path} len={len(raw)} head={raw[:80].replace(chr(10),' ').replace(chr(13),' ')}")
        obj = json.loads(raw)
        out: Dict[str, float] = {}
        for k, v in (obj or {}).items():
            out[str(k)] = float(v)
        if not out:
            _log(path, f"empty_obj path={path}")
            return None
        return out
    except Exception as e:
        try:
            raw2 = path.read_text(encoding="utf-8-sig")
            _log(path, f"parse_fail path={path} len={len(raw2)} err={type(e).__name__}:{e} head={raw2[:80].replace(chr(10),' ').replace(chr(13),' ')}")
        except Exception as e2:
            _log(path, f"parse_fail path={path} err={type(e).__name__}:{e} (and reread failed {type(e2).__name__}:{e2})")
        return None

