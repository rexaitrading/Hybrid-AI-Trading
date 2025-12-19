from __future__ import annotations

import json
import sys
from pathlib import Path

from hybrid_ai_trading.execution.blockg_contract import load_blockg_status
from hybrid_ai_trading.gatescore.io import append_jsonl
from hybrid_ai_trading.gatescore.quality import evaluate_quality


def _read_status_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def main(argv: list[str] | None = None) -> int:
    logs = Path("logs")
    status_path = logs / "blockg_status_stub.json"

    # Fail-closed, but do not crash: write a deterministic record and exit 2.
    if not status_path.exists():
        out = {
            "as_of_date": "",
            "symbol": "NVDA",
            "gatescore_value": 0.0,
            "gatescore_samples": 0,
            "gatescore_min_required": 0.0,
            "gatescore_min_samples": 0,
            "ok_today": False,
            "reason": "blockg_status_missing",
            "producer": "unknown",
        }
        append_jsonl(logs / "gatescore_daily_build.jsonl", out)
        print("[gatescore.daily_build]", out)
        return 2

    # Dataclass view (typed)
    s = load_blockg_status(str(status_path))

    # Raw JSON view (optional fields like producer/micro_score_source)
    raw = _read_status_json(status_path)
    producer = str(raw.get("micro_score_source", raw.get("producer", "unknown")))

    q = evaluate_quality(
        value=float(s.gatescore_value),
        samples=int(s.gatescore_samples),
        min_required=float(s.gatescore_min_required),
        min_samples=int(s.gatescore_min_samples),
    )

    out = {
        "as_of_date": str(s.as_of_date)[:10],
        "symbol": "NVDA",
        "gatescore_value": q.value,
        "gatescore_samples": q.samples,
        "gatescore_min_required": q.min_required,
        "gatescore_min_samples": q.min_samples,
        "ok_today": q.ok,
        "reason": q.reason,
        "producer": producer,
    }
    append_jsonl(logs / "gatescore_daily_build.jsonl", out)
    print("[gatescore.daily_build]", out)
    return 0 if q.ok else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))