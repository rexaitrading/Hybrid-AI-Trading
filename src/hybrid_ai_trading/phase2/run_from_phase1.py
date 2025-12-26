# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import pathlib
from datetime import datetime, timedelta


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except Exception as e:
        raise SystemExit(f"Phase2: bad ts '{ts}': {e}")


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def main() -> None:
    ap = argparse.ArgumentParser("Phase2: run from Phase1 replay_session (hardened realism v2)")
    ap.add_argument("--session", default="logs/replay/replay_session.json")
    ap.add_argument("--outdir", default="logs/phase2")
    ap.add_argument("--max_rows", type=int, default=0, help="0 = all rows")
    ap.add_argument("--fee_bps", type=float, default=1.0)
    ap.add_argument("--slip_bps", type=float, default=2.0)
    ap.add_argument("--latency_ms", type=int, default=130)
    ap.add_argument("--spread_bps", type=float, default=5.0)
    ap.add_argument("--side", choices=["BUY", "SELL"], default="BUY")
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

    fee_bps = float(args.fee_bps)
    slip_bps = float(args.slip_bps)
    spread_bps = float(args.spread_bps)
    latency_ms = int(args.latency_ms)
    side = str(args.side)

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
                ts_raw = (row.get("ts") or "").strip()
                px_raw = row.get("price") or row.get("last") or row.get("close") or row.get("vwap")
                if not sym or not ts_raw or px_raw is None:
                    continue

                try:
                    mid = float(px_raw)
                except Exception:
                    continue
                if mid <= 0:
                    raise SystemExit(f"Phase2: invalid mid price <=0 for {sym} ts={ts_raw}")

                ts = _parse_ts(ts_raw)
                fill_ts = ts + timedelta(milliseconds=latency_ms)

                spread = mid * (spread_bps / 10000.0)
                bid = mid - spread / 2.0
                ask = mid + spread / 2.0

                qty = 1.0
                notional = mid * qty

                fee = notional * (fee_bps / 10000.0)
                slip = notional * (slip_bps / 10000.0)

                if side == "BUY":
                    fill_price = ask + (slip / max(qty, 1e-9))
                else:
                    fill_price = bid - (slip / max(qty, 1e-9))

                cost = fee + slip
                total_cost += cost
                total_notional += notional

                rec = {
                    "ts": ts_raw,
                    "fill_ts": _iso(fill_ts),
                    "symbol": sym,
                    "side": side,
                    "mid_price": mid,
                    "bid": bid,
                    "ask": ask,
                    "spread_bps": spread_bps,
                    "qty": qty,
                    "latency_ms": latency_ms,
                    "fee_bps": fee_bps,
                    "slip_bps": slip_bps,
                    "fee": fee,
                    "slip": slip,
                    "cost": cost,
                    "fill_price": fill_price,
                    "effective_price": fill_price,
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
            "spread_bps": spread_bps,
            "side": side,
        },
        "source": {
            "bars_source": bars_source,
            "bars_path": str(csv_path),
        },
        "version": "phase2.1",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"phase2": "ok", "version": "phase2.1", "fills": n, "outdir": str(outdir)}, indent=2))


if __name__ == "__main__":
    main()