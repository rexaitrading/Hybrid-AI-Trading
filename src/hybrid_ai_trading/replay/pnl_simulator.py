from __future__ import annotations

import os, csv, argparse, math
from typing import List, Dict, Any
from statistics import mean

"""
PNL Simulator:
- Reads replay_journal.csv (flat decisions).
- Applies a simple fill model: enter at next-bar close +/- slippage_bps.
- Exit rule: if journal has "exit_px" columns later, we honor them; else default 1-bar hold.
- Writes equity_curve.csv and replay_journal.sim.csv (with PnL columns).
"""

def _read_csv(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for rec in r:
            out.append(rec)
    return out

def _ensure_header(path: str, cols: List[str]):
    need = not os.path.exists(path) or os.path.getsize(path) == 0
    if need:
        with open(path, "w", newline="") as f:
            w = csv.writer(f); w.writerow(cols)

def _writelines(path: str, rows: List[List[Any]]):
    with open(path, "a", newline="") as f:
        w = csv.writer(f); w.writerows(rows)

def pnl_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal-csv", default="logs/replay_journal.csv")
    ap.add_argument("--bars-csv", default="logs/replay_bars.csv", help="Optional: per-step close px for each symbol (future)")
    ap.add_argument("--slippage-bps", type=float, default=8.0)
    ap.add_argument("--fee-per-share", type=float, default=0.005)
    ap.add_argument("--equity", type=float, default=100000.0)
    ap.add_argument("--out-journal", default="logs/replay_journal.sim.csv")
    ap.add_argument("--out-equity", default="logs/equity_curve.csv")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_journal) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.out_equity) or ".", exist_ok=True)

    rows = _read_csv(args.journal_csv)
    if not rows:
        print("[pnl] empty journal; nothing to do.")
        return 0

    # We assume journal rows are time-ordered.
    # 1-bar hold model: entry at next row for same symbol, exit at the following row; if unavailable, skip.
    # For a tight simulation, you'd snapshot bars per symbol per step. Here we keep it simple.

    # Build per-symbol ordered index
    per_sym: Dict[str, List[int]] = {}
    for i, r in enumerate(rows):
        sym = r["symbol"]
        per_sym.setdefault(sym, []).append(i)

    # Output augmented journal rows
    out_header = list(rows[0].keys()) + ["entry_px", "exit_px", "side_dir", "gross_pnl", "slippage", "fees", "net_pnl"]
    _ensure_header(args.out_journal, out_header)
    out_rows: List[List[Any]] = []

    equity = float(args.equity)
    eq_header = ["idx","equity"]
    _ensure_header(args.out_equity, eq_header)
    eq_rows: List[List[Any]] = []

    for sym, idxs in per_sym.items():
        for j in range(len(idxs)-1):
            i0 = idxs[j]
            i1 = idxs[j+1]
            r0 = rows[i0]; r1 = rows[i1]
            side = (r0.get("side") or "BUY").upper()
            qty = int(float(r0.get("qty") or 0))
            if qty <= 0:
                continue

            entry_ref = float(r1.get("price") or 0.0)  # next decision's close as proxy for next bar close
            if entry_ref <= 0:
                continue
            # 1-bar exit: naive proxy (use same next bar as exit), can be replaced by real bar feed later
            exit_ref = entry_ref

            slip = (args.slippage_bps / 10000.0) * entry_ref
            side_dir = 1 if side == "BUY" else -1
            entry_px = entry_ref + (slip if side == "BUY" else -slip)
            exit_px  = exit_ref - (slip if side == "BUY" else -slip)

            gross = side_dir * (exit_px - entry_px) * qty
            fees  = args.fee_per_share * qty * 2
            net   = gross - fees
            equity += net

            out_line = [r0.get(k,"") for k in rows[0].keys()] + [f"{entry_px:.4f}", f"{exit_px:.4f}", side_dir, f"{gross:.4f}", f"{(2*slip):.4f}", f"{fees:.4f}", f"{net:.4f}"]
            out_rows.append(out_line)
            eq_rows.append([len(eq_rows), f"{equity:.2f}"])

    _writelines(args.out_journal, out_rows)
    _writelines(args.out_equity, eq_rows)

    print(f"[pnl] wrote {len(out_rows)} rows -> {args.out_journal}")
    print(f"[pnl] equity points: {len(eq_rows)} -> {args.out_equity}")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(pnl_main())
