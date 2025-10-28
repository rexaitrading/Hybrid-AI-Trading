# === HAT-GLOBAL LOGGER SAFETY via sitecustomize (idempotent) ===
from __future__ import annotations
import importlib, os, sys, types

_MARKER = "__hat_safe_logger_patched__"

def _ensure_report_dir(base: str | None = None) -> str:
    base = base or os.environ.get("HAT_REPORT_DIR") or os.environ.get("GITHUB_WORKSPACE") or ""
    report_dir = os.path.join(base, ".ci") if base else ".ci"
    os.makedirs(report_dir, exist_ok=True)
    return report_dir

def _normalize_log_path(path):
    if path is None or (isinstance(path, str) and not path.strip()):
        return os.path.join(_ensure_report_dir(), "paper_runner.log")
    p = os.fspath(path)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    return p

def _patch_paper_logger():
    try:
        m = importlib.import_module("hybrid_ai_trading.runners.paper_logger")
    except Exception:
        class _FallbackJsonlLogger:
            def __init__(self, path=None, *a, **kw):
                self.path = _normalize_log_path(path)
                self._fh = open(self.path, "a", encoding="utf-8", buffering=1)
            def write(self, obj):
                import json
                try: s = json.dumps(obj, ensure_ascii=False)
                except Exception: s = '{"log_error":"non-serializable object","repr":%r}' % (obj,)
                self._fh.write(s + "\n")
            def close(self):
                try: self._fh.close()
                except Exception: pass
        sys.modules["hybrid_ai_trading.runners.paper_logger"] = types.SimpleNamespace(
            JsonlLogger=_FallbackJsonlLogger,
            __dict__={_MARKER: True}
        )
        print("[sitecustomize] HAT: paper_logger fallback active", file=sys.stderr)
        return

    if getattr(m, _MARKER, False):
        return  # idempotent

    base_cls = getattr(m, "JsonlLogger", None)
    if base_cls is not None:
        class _SafeJsonlLogger(base_cls):  # type: ignore[misc]
            def __init__(self, path=None, *a, **kw):
                path = _normalize_log_path(path)
                super().__init__(path, *a, **kw)
        m.JsonlLogger = _SafeJsonlLogger  # type: ignore[misc]

    setattr(m, _MARKER, True)
    print("[sitecustomize] HAT: paper_logger patched (global-safe)", file=sys.stderr)

try:
    _patch_paper_logger()
except Exception as e:
    print("[sitecustomize] HAT: patch failed:", repr(e), file=sys.stderr)