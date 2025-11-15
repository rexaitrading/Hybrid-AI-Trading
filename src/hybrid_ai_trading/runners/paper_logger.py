from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Dict

from hybrid_ai_trading.utils.time_utils import utc_now


class JsonlLogger:
    """
    Minimal JSON-lines logger used by runner_paper.py.

    Supports:
      - info(event, **data)
      - warning(event, **data)
      - error(event, **data)
      - log(event)   # raw dict / dataclass fallback

    Writes one JSON object per line to the configured path.
    """

    def __init__(self, path: str = "logs/runner_paper.jsonl") -> None:
        self.path = Path(path)

    # --- low-level writer -------------------------------------------------

    def _write(self, payload: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")

    # --- helpers -----------------------------------------------------------

    def _event_dict(self, level: str, event: str, **data: Any) -> Dict[str, Any]:
        return {
            "ts": utc_now().isoformat(),
            "level": level.upper(),
            "event": event,
            "data": data,
        }

    def _to_dict(self, event: Any) -> Mapping[str, Any]:
        # Used by raw log(event)
        if isinstance(event, Mapping):
            return dict(event)
        if is_dataclass(event):
            try:
                return asdict(event)
            except Exception:
                return {"event": repr(event)}
        return {"event": repr(event)}

    # --- public API used by paper_trader ----------------------------------

    def info(self, event: str, **data: Any) -> None:
        self._write(self._event_dict("INFO", event, **data))

    def warning(self, event: str, **data: Any) -> None:
        self._write(self._event_dict("WARN", event, **data))

    def error(self, event: str, **data: Any) -> None:
        self._write(self._event_dict("ERROR", event, **data))

    # raw log (used by our NaN-guard tests earlier, safe to keep)
    def log(self, event: Any) -> None:
        self._write(self._to_dict(event))

# --- Patch: ensure JsonlLogger handles path=None safely ---
class _JsonlLoggerPatched(JsonlLogger):
    def __init__(self, path=None):
        if path is None:
            path = "logs/paper_session.jsonl"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

JsonlLogger = _JsonlLoggerPatched
