# tools/orb_replay_quick.py  explicit, verbose ORB test (for 1-day CSV)
import argparse
import csv
from datetime import datetime


def parse_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for w in r:
            ts = w.get("timestamp") or w.get("Timestamp") or w.get("ts") or w.get("datetime")
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
            rows.append(
                {
                    "ts": t,
                    "open": float(w.get("open") or w.get("Open")),
                    "high": float(w.get("high") or w.get("High")),
                    "low": float(w.get("low") or w.get("Low")),
                    "close": float(w.get("close") or w.get("Close")),
                    "volume": float(w.get("volume") or w.get("Volume") or 0),
                }
            )
    rows.sort(key=lambda x: x["ts"])
    return rows


def write_csv(path, rows):
    if not rows:
        with open(path, "w", newline="") as f:
            f.write("ts,symbol,side,entry_px,exit_px,qty,gross_pnl,fees,net_pnl,outcome\n")
        return
    cols = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--journal-csv", required=True)
    ap.add_argument("--pnl-csv", required=True)
    ap.add_argument("--orb-minutes", type=int, default=5)
    ap.add_argument("--entry", choices=["high", "close", "either"], default="either")
    args = ap.parse_args()

    rows = parse_rows(args.csv)
    om = max(1, min(args.orb_minutes, len(rows) - 2))
    orb = rows[:om]
    rest = rows[om:]
    orb_high = max(x["high"] for x in orb)
    orb_low = min(x["low"] for x in orb)
    print(f"DEBUG ORB: high={orb_high:.4f} low={orb_low:.4f} bars={len(rows)} om={om}")

    journal = []
    pnl = []

    def long_hit(b):
        return (b["high"] >= orb_high) or (
            args.entry in ("close", "either") and b["close"] >= orb_high
        )

    entered = False
    for i, b in enumerate(rest, start=om):
        print(
            f"DEBUG BAR {i} {b['ts'].isoformat()} H={b['high']:.2f} L={b['low']:.2f} C={b['close']:.2f}"
        )
        if not entered and long_hit(b):
            entry = orb_high
            stop = orb_low
            target = entry + (orb_high - orb_low)
            qty = 1  # fixed 1 for proof-of-life
            print(f"DEBUG ENTER LONG @{entry:.2f} stop={stop:.2f} tgt={target:.2f} qty={qty}")
            journal.append(
                {
                    "ts": b["ts"].isoformat(sep=" "),
                    "symbol": "SIM",
                    "side": "long",
                    "entry_px": f"{entry:.4f}",
                    "stop_px": f"{stop:.4f}",
                    "target_px": f"{target:.4f}",
                    "qty": qty,
                    "setup": "ORB",
                }
            )
            # exit: next bar close or EOD
            exit_px = rest[(i - om) + 1]["close"] if (i - om + 1) < len(rest) else b["close"]
            pnl.append(
                {
                    "ts": b["ts"].isoformat(sep=" "),
                    "symbol": "SIM",
                    "side": "long",
                    "entry_px": f"{entry:.4f}",
                    "exit_px": f"{exit_px:.4f}",
                    "qty": qty,
                    "gross_pnl": f"{(exit_px-entry)*qty:.2f}",
                    "fees": "0.00",
                    "net_pnl": f"{(exit_px-entry)*qty:.2f}",
                    "outcome": ("nextbar_close" if (i - om + 1) < len(rest) else "eod"),
                }
            )
            print(f"DEBUG EXIT @{exit_px:.2f}")
            break

    write_csv(args.journal_csv, journal)
    write_csv(args.pnl_csv, pnl)
    print(f"WROTE journal={len(journal)} pnl={len(pnl)}")


if __name__ == "__main__":
    main()
