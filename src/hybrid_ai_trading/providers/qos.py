import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def log_provider_qos(
    name: str,
    *,
    ok: bool,
    latency_s: float,
    status_code: Optional[int],
    extra: Optional[Dict[str, Any]] = None,
    base_dir: Optional[str] = None,
) -> None:
    """
    Append a single QoS measurement for a provider into a JSONL file.

    Fields:
      - ts:        unix timestamp (float)
      - provider:  logical provider name, e.g. "coinbase"
      - ok:        whether the call succeeded
      - latency_s: wall-clock latency in seconds
      - status_code: HTTP status, if applicable
      - extra:     any additional metadata (endpoint, error_type, etc.)
    """
    base = Path(base_dir or os.path.join(os.getcwd(), "logs", "providers"))
    base.mkdir(parents=True, exist_ok=True)

    path = base / f"{name}_qos.jsonl"

    entry: Dict[str, Any] = {
        "ts": time.time(),
        "provider": name,
        "ok": ok,
        "latency_s": float(latency_s),
        "status_code": status_code,
    }

    if extra:
        entry.update(extra)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")