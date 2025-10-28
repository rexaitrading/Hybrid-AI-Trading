from __future__ import annotations
import csv, os
from typing import List, Dict
def _to_f(x, default=None):
    try:
        return float(x)
    except Exception:
        return default
def _read_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
def pnl_simulate_v2(csv_in: str, csv_out: str, equity_csv: str, default_slip_bps: float = 8.0):
    rows = _read_csv(csv_in)
    if not rows:
        print(f"[pnl-v2] empty input: {csv_in}")
        return
    os.makedirs(os.path.dirname(csv_out) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(equity_csv) or ".", exist_ok=True)
    # group by symbol preserving order
    sym_rows: Dict[str, List[Dict]] = {}
    for r in rows:
        sym_rows.setdefault(r.get("symbol",""), []).append(r)
    out_rows: List[List[str]] = []
    equity = 100000.0
    eq = []
    header = list(rows[0].keys())
    for col in ("entry_px","exit_px","mae","mfe","R","gross_pnl","slippage","fees","net_pnl"):
        if col not in header: header.append(col)
    for sym, seq in sym_rows.items():
        for i in range(len(seq)-1):
            cur, nxt = seq[i], seq[i+1]
            side = (cur.get("side") or "BUY").upper()
            qty  = _to_f(cur.get("qty"), 0.0) or 0.0
            if qty <= 0:
                continue
            px_open = _to_f(nxt.get("price")) or _to_f(nxt.get("close"))
            px_close= _to_f(nxt.get("close")) or px_open
            if px_open is None or px_close is None:
                continue
            spread_bps = _to_f(cur.get("spread_bps"), default_slip_bps) or default_slip_bps
            half_spread = (spread_bps/10000.0) * px_open / 2.0
            entry_px = (px_open + half_spread) if side == "BUY" else (px_open - half_spread)
            stop_px   = _to_f(cur.get("stop_px"))
            target_px = _to_f(cur.get("target_px"))
            hi = _to_f(nxt.get("high"), px_open)
            lo = _to_f(nxt.get("low"),  px_open)
            mae = mfe = 0.0
            if side == "BUY":
                if lo is not None: mae = max(0.0, entry_px - lo)
                if hi is not None: mfe = max(0.0, hi - entry_px)
            else:
                if hi is not None: mae = max(0.0, hi - entry_px)
                if lo is not None: mfe = max(0.0, entry_px - lo)
            exit_px = px_close
            if stop_px is not None and target_px is not None:
                if side == "BUY":
                    if lo is not None and lo <= stop_px:   exit_px = stop_px
                    elif hi is not None and hi >= target_px: exit = target_px
                else:
                    if hi is not None and hi >= stop_px:   exit_px = stop_px
                    elif lo is not None and lo <= target_px: exit_px = target_px
            slip_val = 2*half_spread*abs(qty)
            gross = (entry_px - exit_px)*qty*(-1 if side=="BUY" else 1)
            fees  = 0.005*abs(qty)
            net   = gross - slip_val - fees
            equity += net
            R = None
            if stop_px is not None and stop_px != entry_px:
                risk = abs(entry_px - stop_px)
                if risk > 1e-9:
                    R = ((exit_px - entry_px) * (1 if side=="BUY" else -1))/risk
            row = [cur.get(h,"") for h in header if h not in ("entry_px","exit_px","mae","mfe","R","gross_pnl","slippage","fees","net_pnl")]
            extras = {
                "entry_px":f"{entry_px:.6g}","exit_px":f"{exit_px:.6g}",
                "mae":f"{mae:.6g}","mfe":f"{mfe:.6g}","R":("" if R is None else f"{R:.6g}"),
                "gross_pnl":f"{gross:.6g}","slippage":f"{(slip_val):.6g}","fees":f"{fees:.6g}","net_pnl":f"{net:.6g}"
            }
            row.extend([extras[k] for k in ("entry_px","exit_px","mae","mfe","R","gross_pnl","slippage","fees","net_pnl")])
            out_rows.append(row)
            eq.append(f"{equity:.2f}")
    with open(csv_out, "w", newline="") as fo:
        wr = csv.writer(fo); wr.writerow(header); wr.writerows(out_rows)
    with open(equity_csv,"w",newline="") as fe:
        fe.write("equity\n"); fe.write("\n".join(eq))
    print(f"[pnl-v2] wrote {len(out_rows)} rows -> {csv_out}")
    print(f"[pnl-v2] equity -> {equity_csv}")
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in",  dest="inp", required=True, help="input CSV (replay_journal.csv)")
    p.add_argument("--out", dest="out", required=True, help="output CSV (pnl v2)")
    p.add_argument("--equity", dest="eq", required=True, help="equity curve csv")
    p.add_argument("--slip", type=float, default=8.0)
    a = p.parse_args()
    pnl_simulate_v2(a.inp, a.out, a.eq, a.slip)
