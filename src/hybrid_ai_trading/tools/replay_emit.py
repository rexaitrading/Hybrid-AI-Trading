from __future__ import annotations

import datetime
import json
import os
import pathlib
from typing import Any, Dict, Iterable, Optional


class ReplayEmitter:
    PATH = os.environ.get("HAT_REPLAY_LOG", r"data/replay_log.ndjson")

    @staticmethod
    def _now_z() -> str:
        return (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _to_bar_dict(b: Any) -> Dict[str, Any]:
        if b is None:
            return {}
        if isinstance(b, dict):
            d = b
        else:
            d = {
                k: getattr(b, k, None)
                for k in ("open", "high", "low", "close", "volume")
            }
        return {
            "open": float(d.get("open")) if d.get("open") is not None else None,
            "high": float(d.get("high")) if d.get("high") is not None else None,
            "low": float(d.get("low")) if d.get("low") is not None else None,
            "close": float(d.get("close")) if d.get("close") is not None else None,
            "volume": float(d.get("volume")) if d.get("volume") is not None else None,
        }

    @classmethod
    def emit(
        cls,
        symbol: str,
        bar: Any,
        window: Optional[Iterable[Any]] = None,
        hypo_r: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            ev: Dict[str, Any] = {
                "ts": cls._now_z(),
                "symbol": symbol,
                "bar": cls._to_bar_dict(bar),
                "window": [
                    cls._to_bar_dict(w)
                    for w in (list(window) if window is not None else [])
                ][:60],
            }
            if hypo_r is not None:
                ev["hypo"] = {"r": float(hypo_r)}
            if extra:
                ev.update(dict(extra))
            path = pathlib.Path(cls.PATH)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except Exception:
            # never break replay on logging failures
            pass
