from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Optional

from .io import append_event, read_daily_summary_rows
from .quality import evaluate_daily_summary_row, load_thresholds
from .schemas import GateScoreEventRow


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="hybrid_ai_trading.gatescore.daily_build")
    ap.add_argument("--summary-csv", default="logs/gatescore_daily_summary.csv")
    ap.add_argument("--thresholds-json", default="docs/thresholds/gatescore_thresholds.json")
    ap.add_argument("--events-jsonl", default="logs/gatescore_quality_events.jsonl")
    ap.add_argument("--symbol", default=None, help="optional filter, e.g. NVDA")
    args = ap.parse_args(argv)

    try:
        thresholds = load_thresholds(args.thresholds_json)
        rows = read_daily_summary_rows(args.summary_csv)
    except Exception as e:
        ev = GateScoreEventRow(
            ts_utc=_now_utc_iso(),
            symbol=str(args.symbol or "ALL"),
            event_type="gatescore_quality_eval",
            ok=False,
            reasons=f"exception:{type(e).__name__}",
            metrics={"error": str(e)},
        )
        append_event(args.events_jsonl, ev)
        return 2

    selected = []
    for r in rows:
        if args.symbol and r.symbol.upper() != str(args.symbol).upper():
            continue
        selected.append(r)

    if not selected:
        ev = GateScoreEventRow(
            ts_utc=_now_utc_iso(),
            symbol=str(args.symbol or "ALL"),
            event_type="gatescore_quality_eval",
            ok=False,
            reasons="no_rows",
            metrics={"summary_csv": args.summary_csv},
        )
        append_event(args.events_jsonl, ev)
        return 3

    rc = 0
    for r in selected:
        dec = evaluate_daily_summary_row(r, thresholds=thresholds, require_real_source=True)
        ev = GateScoreEventRow(
            ts_utc=_now_utc_iso(),
            symbol=r.symbol,
            event_type="gatescore_quality_eval",
            ok=bool(dec.ok),
            reasons=",".join(dec.reasons) if dec.reasons else "",
            metrics=dec.metrics,
        )
        append_event(args.events_jsonl, ev)
        if not dec.ok:
            rc = 10  # fail-closed if any fails

    return rc


if __name__ == "__main__":
    raise SystemExit(main())