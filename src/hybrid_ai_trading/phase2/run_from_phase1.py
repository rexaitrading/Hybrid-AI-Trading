# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import os

def _load_micro_mult(repo_root: pathlib.Path) -> float:
    """
    Phase-2 micro multiplier from logs/phase2_micro_cost_snapshot.json.
    Fail-soft: returns 1.0 if missing/invalid.
    """
    try:
        p = repo_root / "logs" / "phase2_micro_cost_snapshot.json"
        if not p.exists():
            return 1.0
        j = json.loads(p.read_text(encoding="utf-8"))
        if not j.get("ok"):
            return 1.0
        spy = float(((j.get("inputs") or {}).get("spy") or {}).get("micro_avg") or 0.0)
        qqq = float(((j.get("inputs") or {}).get("qqq") or {}).get("micro_avg") or 0.0)
        base = (spy + qqq) / 2.0 if (spy > 0 or qqq > 0) else (spy or qqq or 0.0)
        m = 1.0 + max(0.0, min(base, 1.0))
        return max(1.0, min(m, 2.0))
    except Exception:
        return 1.0

from datetime import datetime, timedelta


def _parse_ts(ts: str) -> datetime:
    s = (ts or "").strip()

    # 1) ISO (existing behavior)
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass

    # 2) Compact bars: yyyyMMdd  HH:mm:ss (double space) or single space
    for fmt in ("%Y%m%d  %H:%M:%S", "%Y%m%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass

    raise SystemExit("Phase2: bad ts '{}'".format(ts))


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
    session_symbol = (sess.get("symbol") or "").strip().upper()
    if not session_symbol:
        raise SystemExit("Phase2: session missing symbol (fail-closed)")
    bars_source = sess.get("bars_source")
    bars_path = sess.get("bars_path")
    if bars_source != "csv" or not bars_path:
        raise SystemExit(f"Phase2: session not REAL csv-backed (bars_source={bars_source}, bars_path={bars_path})")

    csv_path = pathlib.Path(bars_path)
    if not csv_path.exists():
        raise SystemExit(f"Phase2: bars_path missing: {csv_path}")

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    micro_mult = _load_micro_mult(pathlib.Path('.').resolve())

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

                sym = (row.get("symbol") or session_symbol).strip().upper()
                ts_raw = (row.get("ts") or "").strip()
                px_raw = row.get("price") or row.get("last") or row.get("close") or row.get("vwap")
                if not sym or not ts_raw or px_raw is None:
                    continue

                try:
                    mid = float(px_raw)

                    # volatility proxy from bar range (bps)
                    hi_raw = row.get("high")
                    lo_raw = row.get("low")
                    range_bps = 0.0
                    try:
                        hi = float(hi_raw) if hi_raw is not None else mid
                        lo = float(lo_raw) if lo_raw is not None else mid
                        if mid > 0 and hi >= lo:
                            range_bps = ((hi - lo) / mid) * 10000.0
                    except Exception:
                        range_bps = 0.0
                except Exception:
                    continue
                if mid <= 0:
                    raise SystemExit(f"Phase2: invalid mid price <=0 for {sym} ts={ts_raw}")

                ts = _parse_ts(ts_raw)
                fill_ts = ts + timedelta(milliseconds=latency_ms)

                # Apply micro multiplier + volatility-scaled slippage
                spread_bps_eff = spread_bps * micro_mult
                slip_bps_eff = slip_bps * micro_mult * (1.0 + min(range_bps, 50.0) / 10.0)

                spread = mid * (spread_bps_eff / 10000.0)
                bid = mid - spread / 2.0
                ask = mid + spread / 2.0

                qty = 1.0
                notional = mid * qty

                fee = notional * (fee_bps / 10000.0)
                slip = notional * (slip_bps_eff / 10000.0)

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
                    "spread_bps_eff": spread_bps_eff,
                    "slip_bps_eff": slip_bps_eff,
                    "range_bps": range_bps,
                    "micro_mult": micro_mult,
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
