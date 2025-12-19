from __future__ import annotations

import argparse
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
    ap = argparse.ArgumentParser(prog="hybrid_ai_trading.gatescore.daily_build")
    ap.add_argument("--symbol", default="NVDA", help="Symbol (NVDA/SPY/QQQ/...)")
    args = ap.parse_args(argv)

    sym = str(args.symbol).upper().strip() or "NVDA"

    logs = Path("logs")
    logs.mkdir(parents=True, exist_ok=True)
    status_path = logs / "blockg_status_stub.json"

    # Fail-closed, deterministic: write a record and exit 2 (do not crash).
    if not status_path.exists():
        out = {
            "as_of_date": "",
            "symbol": sym,
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

    # Typed view (contract)
    s = load_blockg_status(str(status_path))

    # Raw JSON view for optional fields like producer/micro_score_source
    raw = _read_status_json(status_path)
    producer = str(raw.get("micro_score_source", raw.get("producer", "unknown")))

    q = evaluate_quality(
        value=float(getattr(s, "gatescore_value", 0.0) or 0.0),
        samples=int(getattr(s, "gatescore_samples", 0) or 0),
        min_required=float(getattr(s, "gatescore_min_required", 0.0) or 0.0),
        min_samples=int(getattr(s, "gatescore_min_samples", 0) or 0),
    )

    out = {
        "as_of_date": str(getattr(s, "as_of_date", ""))[:10],
        "symbol": sym,
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