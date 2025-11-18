# === provider_qos.py (COMMAND TEAM PHASE-5) ===

import time
import json
from pathlib import Path

class ProviderQoS:
    """
    Tracks latency, stale-age, error rate, provider failures.
    Writes JSON lines to .intel/provider_qos.jsonl
    """

    def __init__(self, provider_name: str, path="intel/provider_qos.jsonl"):
        self.provider_name = provider_name
        self.path = Path(path)
        self.failures = 0
        self.success = 0
        self.last_price_ts = None
        self.last_latency = None

    def record(
        self,
        latency_ms: float,
        ok: bool,
        price_ts: float = None,
        error: str = None,
    ):
        ts = time.time()

        if ok:
            self.success += 1
        else:
            self.failures += 1

        self.last_latency = latency_ms

        if price_ts:
            self.last_price_ts = price_ts
            stale_ms = max(0, (ts - price_ts) * 1000)
        else:
            stale_ms = None

        payload = {
            "ts": ts,
            "provider": self.provider_name,
            "latency_ms": latency_ms,
            "ok": ok,
            "failures": self.failures,
            "success": self.success,
            "error": error,
            "stale_ms": stale_ms,
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

        return payload