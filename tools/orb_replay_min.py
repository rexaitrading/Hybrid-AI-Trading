from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _get_key(keys_lower: Dict[str, str], variants) -> Optional[str]:
    for v in variants:
        if v in keys_lower:
            return keys_lower[v]
    return None


def _parse_ts(x) -> Optional[datetime]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        v = float(s)
        if v > 1e12:
            return datetime.fromtimestamp(v / 1000, tz=timezone.utc).replace(tzinfo=None)
        if v > 1e9:
            return datetime.fromtimestamp(v, tz=timezone.utc).replace(tzinfo=None)
    except:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except:
                pass
    return None


def read_csv(path: str) -> List[Dict]:
    out = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise ValueError("CSV has no header row.")
        keys = {k.lower(): k for k in r.fieldnames}
        k_ts = _get_key(
            keys, ["timestamp", "datetime", "ts", "time", "date_time", "datetime_utc", "dt"]
        )
        k_o = _get_key(keys, ["open", "o"])
        k_h = _get_key(keys, ["high", "h"])
        k_l = _get_key(keys, ["low", "l"])
        k_c = _get_key(keys, ["close", "c"])
        k_v = _get_key(keys, ["volume", "vol", "v"])
        for row in r:
            ts_val = row.get(k_ts)
            dt = _parse_ts(ts_val)
            if not dt:
                continue
            try:
                o = float(row[k_o])
                h = float(row[k_h])
                l = float(row[k_l])
                c = float(row[k_c])
            except:
                continue
            v = 0.0
            if k_v and row.get(k_v) not in (None, ""):
                try:
                    v = float(row[k_v])
                except:
                    v = 0.0
            out.append({"ts": dt, "open": o, "high": h, "low": l, "close": c, "volume": v})
    out.sort(key=lambda x: x["ts"])
    return out


def group_by_day(rows):
    days = {}
    for r in rows:
        d = datetime(r["ts"].year, r["ts"].month, r["ts"].day)
        days.setdefault(d, []).append(r)
    return days


def intrabar_fill(is_long, bar, stop, target):
    lo, hi = bar["low"], bar["high"]
    if is_long:
        if lo <= stop and hi >= target:
            return "stop"
        if hi >= target:
            return "target"
        if lo <= stop:
            return "stop"
    else:
        if hi >= stop and lo <= target:
            return "stop"
        if lo <= target:
            return "target"
        if hi >= stop:
            return "stop"
    return "none"


def orb_replay(
    rows,
    orb_minutes=5,
    max_trades_per_day=2,
    kelly_f=0.5,
    f_max=0.02,
    equity=100000.0,
    fee_per_share=0.0035,
    debug=False,
):
    journal, pnl = [], []
    for _, bars in group_by_day(rows).items():
        if len(bars) < 3:
            continue
        om = max(1, min(orb_minutes, len(bars) - 2))
        orb_high = max(b["high"] for b in bars[:om])
        orb_low = min(b["low"] for b in bars[:om])
        range_sz = max(orb_high - orb_low, 1e-6)
        if debug:
            print(f"DEBUG ORB high={orb_high:.4f} low={orb_low:.4f}")
        in_pos = False
        side = None
        trades = 0
        for i, bar in enumerate(bars[om:], start=om):
            if not in_pos:
                lg = (bar["high"] >= orb_high) or (bar["close"] >= orb_high)
                sh = (bar["low"] <= orb_low) or (bar["close"] <= orb_low)
                if debug:
                    print(f"DEBUG BAR {i} {bar['ts']} lg={lg} sh={sh}")
                if lg:
                    side = "long"
                    entry = orb_high
                    stop = orb_low
                    target = entry + range_sz
                elif sh:
                    side = "short"
                    entry = orb_low
                    stop = orb_high
                    target = entry - range_sz
                else:
                    continue
                rps = abs(entry - stop)
                risk_cap = equity * min(kelly_f, f_max)
                qty = max(1, int(risk_cap / max(1e-6, rps)))
                journal.append(
                    {
                        "ts": bar["ts"].isoformat(sep=" "),
                        "symbol": "SIM",
                        "side": side,
                        "entry_px": f"{entry:.4f}",
                        "stop_px": f"{stop:.4f}",
                        "target_px": f"{target:.4f}",
                        "qty": qty,
                        "setup": "ORB",
                    }
                )
                in_pos = True
                trades += 1
                continue
            hit = intrabar_fill(side == "long", bar, stop, target)
            if hit == "none" and i == len(bars) - 1:
                exit_px = bar["close"]
            elif hit == "target":
                exit_px = target
            elif hit == "stop":
                exit_px = stop
            else:
                continue
            gross = (exit_px - entry) * (1 if side == "long" else -1) * qty
            fees = fee_per_share * qty
            net = gross - fees
            pnl.append(
                {
                    "ts": bar["ts"].isoformat(sep=" "),
                    "symbol": "SIM",
                    "side": side,
                    "entry_px": f"{entry:.4f}",
                    "exit_px": f"{exit_px:.4f}",
                    "qty": qty,
                    "gross_pnl": f"{gross:.2f}",
                    "fees": f"{fees:.2f}",
                    "net_pnl": f"{net:.2f}",
                    "outcome": hit,
                }
            )
            in_pos = False
            side = None
    return journal, pnl


def write_csv(path, rows):
    if not rows:
        with open(path, "w", newline="") as f:
            f.write("ts,symbol,side,entry_px,exit_px,qty,gross_pnl,fees,net_pnl,outcome\n")
        return
    cols = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        [w.writerow(r) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--journal-csv", required=True)
    ap.add_argument("--pnl-csv", required=True)
    ap.add_argument("--orb-minutes", type=int, default=5)
    ap.add_argument("--kelly", type=float, default=0.5)
    ap.add_argument("--f-max", type=float, default=0.02)
    ap.add_argument("--equity", type=float, default=100000.0)
    ap.add_argument("--fee-per-share", type=float, default=0.0035)
    ap.add_argument("--max-trades-per-day", type=int, default=2)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    rows = read_csv(args.csv)
    journal, pnl = orb_replay(
        rows,
        orb_minutes=args.orb_minutes,
        max_trades_per_day=args.max_trades_per_day,
        kelly_f=args.kelly,
        f_max=args.f_max,
        equity=args.equity,
        fee_per_share=args.fee_per_share,
        debug=args.debug,
    )
    write_csv(args.journal_csv, journal)
    write_csv(args.pnl_csv, pnl)
    print(f"Wrote {len(journal)} journal rows and {len(pnl)} pnl rows.")


if __name__ == "__main__":
    main()
