from __future__ import annotations

import sys
from pathlib import Path

from hybrid_ai_trading.execution.blockg_contract import load_blockg_status
from hybrid_ai_trading.gatescore.io import append_jsonl
from hybrid_ai_trading.gatescore.quality import evaluate_quality


def main(argv: list[str] | None = None) -> int:
    logs = Path("logs")
    try:
        st = load_blockg_status("logs/blockg_status_stub.json")
    except Exception as e:
        out = {
            "as_of_date": "",
            "symbol": "NVDA",
            "gatescore_value": 0.0,
            "gatescore_samples": 0,
            "gatescore_min_required": 0.0,
            "gatescore_min_samples": 0,
            "ok_today": False,
            "reason": f"blockg_status_missing:{e}",
            "producer": "unknown",
        }
        append_jsonl(logs / "gatescore_daily_build.jsonl", out)
        print("[gatescore.daily_build]", out)
        return 2

    value = float(st.get("gatescore_value", 0.0) or 0.0)
    samples = int(st.get("gatescore_samples", 0) or 0)
    min_required = float(st.get("gatescore_min_required", 0.0) or 0.0)
    min_samples = int(st.get("gatescore_min_samples", 0) or 0)

    q = evaluate_quality(value=value, samples=samples, min_required=min_required, min_samples=min_samples)

    out = {
        "as_of_date": str(st.get("as_of_date", ""))[:10],
        "symbol": "NVDA",
        "gatescore_value": q.value,
        "gatescore_samples": q.samples,
        "gatescore_min_required": q.min_required,
        "gatescore_min_samples": q.min_samples,
        "ok_today": q.ok,
        "reason": q.reason,
        "producer": str(st.get("micro_score_source", "unknown")),
    }
    append_jsonl(logs / "gatescore_daily_build.jsonl", out)
    print("[gatescore.daily_build]", out)
    return 0 if q.ok else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))