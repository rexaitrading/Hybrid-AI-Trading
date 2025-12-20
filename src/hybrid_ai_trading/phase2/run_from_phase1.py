# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import pathlib
from typing import Any, Dict, List


def main() -> None:
    ap = argparse.ArgumentParser("Phase2: run from Phase1 replay_session")
    ap.add_argument("--session", default="logs/replay/replay_session.json")
    ap.add_argument("--outdir", default="logs/phase2")
    ap.add_argument("--max_rows", type=int, default=0, help="0 = all rows")
    args = ap.parse_args()

    session_path = pathlib.Path(args.session)
    if not session_path.exists():
        raise SystemExit(f"Phase2: missing session: {session_path}")

    sess = json.loads(session_path.read_text(encoding="utf-8"))
    bars_source = sess.get("bars_source")
    bars_path = sess.get("bars_path")
    if bars_source != "csv" or not bars_path:
        raise SystemExit(f"Phase2: session not REAL csv-backed (bars_source={bars_source}, bars_path={bars_path})")

    csv_path = pathlib.Path(bars_path)
    if not csv_path.exists():
        raise SystemExit(f"Phase2: bars_path missing: {csv_path}")

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Deterministic models (seed): reuse replay models if present; else fall back to simple constants
    fee_bps = 1.0
    slip_bps = 2.0
    latency_ms = 130

    fills_path = outdir / "phase2_fills.jsonl"
    summary_path = outdir / "phase2_summary.json"

    n = 0
    total_cost = 0.0
    total_notional = 0.0

    with fills_path.open("w", encoding="utf-8", newline="\n") as f_out:
        with csv_path.open("r", encoding="utf-8") as f_in:
            reader = csv.DictReader(f_in)
            for row in reader:
                if args.max_rows and n >= args.max_rows:
                    break

                sym = (row.get("symbol") or "").strip().upper()
                ts = (row.get("ts") or "").strip()
                px_raw = row.get("price") or row.get("last") or row.get("close") or row.get("vwap")
                if not sym or not ts or px_raw is None:
                    continue
                try:
                    px = float(px_raw)
                except Exception:
                    continue

                # Phase2: apply deterministic slippage + fee to create an "effective fill price"
                # For now, assume a 1-share fill (qty=1) to produce REAL cost artifacts.
                qty = 1.0
                notional = px * qty

                fee = notional * (fee_bps / 10000.0)
                slip = notional * (slip_bps / 10000.0)
                cost = fee + slip

                total_cost += cost
                total_notional += notional

                rec = {
                    "ts": ts,
                    "symbol": sym,
                    "mid_price": px,
                    "qty": qty,
                    "latency_ms": latency_ms,
                    "fee_bps": fee_bps,
                    "slip_bps": slip_bps,
                    "cost": cost,
                    "effective_price": px + (cost / max(qty, 1e-9)),
                }
                f_out.write(json.dumps(rec, separators=(",", ":")) + "\n")
                n += 1

    if n < 1:
        raise SystemExit("Phase2: produced zero fills (fail-closed)")

    summary = {
        "rows_in": n,
        "total_notional": total_notional,
        "total_cost": total_cost,
        "avg_cost_bps": (total_cost / total_notional) * 10000.0 if total_notional else None,
        "models": {
            "latency_ms": latency_ms,
            "fee_bps": fee_bps,
            "slip_bps": slip_bps,
        },
        "source": {
            "bars_source": bars_source,
            "bars_path": str(csv_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"phase2": "ok", "fills": n, "outdir": str(outdir)}, indent=2))


if __name__ == "__main__":
    main()