from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, Optional

_RESERVED = {
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


def _ts() -> str:
    # ISO8601 with seconds; monotonic not needed for simple JSONL
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


class JsonlLogger:
    """
    Lightweight JSON-lines logger used by paper runners.
    Usage:
        log = JsonlLogger("logs/runner_paper.jsonl")
        log.info("run_start", cfg=cfg, symbols=symbols)
        log.error("route_error", error="...")
    Each call writes one compact JSON object per line.
    """

    def __init__(self, path: str, flush: bool = True) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # open in append text mode; encoding utf-8
        self._fh = open(self.path, "a", encoding="utf-8")
        self._lock = threading.Lock()
        self._flush = flush

    def _write(self, level: str, event: str, **kwargs: Any) -> None:
        # keep payload small and safe
        data: Dict[str, Any] = {}
        for k, v in (kwargs or {}).items():
            if k in _RESERVED:
                data[f"data_{k}"] = v
            else:
                data[k] = v
        rec = {"ts": _ts(), "level": level, "event": event, **({"data": data} if data else {})}
        line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._fh.write(line + "\n")
            if self._flush:
                self._fh.flush()

    def info(self, event: str, **kwargs: Any) -> None:
        self._write("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._write("WARN", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._write("ERROR", event, **kwargs)

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass

    def __del__(self):
        try:
            self._fh.close()
        except Exception:
            pass
