from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def main() -> int:
    base_url = "https://api.kraken.com"
    endpoint = "/0/public/Time"
    url = base_url + endpoint

    t0 = time.perf_counter()
    status_code = None
    ok = False
    error: str | None = None

    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=5) as resp:
            status_code = resp.getcode()
            _body = resp.read()
        ok = status_code is not None and 200 <= status_code < 300
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        error = str(exc)
    except Exception as exc:  # very defensive
        error = f"unexpected: {exc!r}"

    latency = time.perf_counter() - t0
    ts = time.time()

    log_dir = Path("logs") / "providers"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "kraken_qos.jsonl"

    payload = {
        "ts": ts,
        "provider": "kraken",
        "ok": bool(ok),
        "latency_s": float(latency),
        "status_code": status_code,
        "endpoint": endpoint,
    }
    if error is not None:
        payload["error"] = error

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

    print("Kraken QoS probe entry:", payload)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())