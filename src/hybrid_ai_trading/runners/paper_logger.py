from __future__ import annotations

import json
import os
from typing import Optional, Union

# === HAT-SAFE-LOGGER v3 ===
def _ensure_report_dir(base: Optional[str] = None) -> str:
    base = base or os.environ.get("HAT_REPORT_DIR") or os.environ.get("GITHUB_WORKSPACE") or ""
    report_dir = os.path.join(base, ".ci") if base else ".ci"
    os.makedirs(report_dir, exist_ok=True)
    return report_dir

def _normalize_log_path(path: Optional[Union[str, os.PathLike]]) -> str:
    if path is None or (isinstance(path, str) and not path.strip()):
        return os.path.join(_ensure_report_dir(), "paper_runner.log")
    p = os.fspath(path)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    return p

class JsonlLogger:
    """Minimal JSONL logger for CI + local; robust to None/empty paths."""
    def __init__(self, path: Optional[Union[str, os.PathLike]] = None):
        self.path = _normalize_log_path(path)
        self._fh = open(self.path, "a", encoding="utf-8", buffering=1)

    def write(self, obj) -> None:
        try:
            line = json.dumps(obj, ensure_ascii=False)
        except Exception:
            line = json.dumps({"log_error": "non-serializable object", "repr": repr(obj)}, ensure_ascii=False)
        self._fh.write(line + "\n")

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass