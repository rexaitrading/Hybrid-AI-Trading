from __future__ import annotations

import os, csv, math, argparse
from typing import List, Dict, Any
from statistics import mean, pstdev
from collections import defaultdict

"""
Pattern Miner:
- Reads replay_journal.sim.csv
- Aggregates by "setup" (and by symbol) to compute hit-rate, expectancy, net PnL, drawdown-like metric.
- Writes reports/repeatable_setups.md with a compact ranking.
"""

def _read_csv(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for rec in r:
            out.append(rec)
    return out

def miner_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-journal", default="logs/replay_journal.sim.csv")
    ap.add_argument("--out-md", default="reports/repeatable_setups.md")
    ap.add_argument("--min-trades", type=int, default=15)
    ap.add_argument("--min-hit", type=float, default=0.53)
    ap.add_argument("--min-exp", type=float, default=0.0)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_md) or ".", exist_ok=True)
    rows = _read_csv(args.sim_journal)
    if not rows:
        print("[miner] empty sim journal.")
        return 0

    group: Dict[tuple, List[float]] = defaultdict(list)
    for r in rows:
        setup = r.get("setup","(na)")
        sym   = r.get("symbol","(na)")
        try:
            net = float(r.get("net_pnl") or 0.0)
        except Exception:
            net = 0.0
        group[(setup, sym)].append(net)

    # Compute stats
    results: List[Dict[str, Any]] = []
    for (setup, sym), pnl in group.items():
        n = len(pnl)
        if n < args.min_trades:
            continue
        wins = sum(1 for x in pnl if x > 0)
        hit  = wins / n
        exp  = mean(pnl)
        vol  = pstdev(pnl) if n > 1 else 0.0
        score = (exp / (vol + 1e-6)) * math.sqrt(n)  # simple Sharpe-like with support for count
        if hit >= args.min_hit and exp >= args.min_exp:
            results.append({"setup": setup, "symbol": sym, "n": n, "hit": hit, "exp": exp, "vol": vol, "score": score, "sum": sum(pnl)})

    # Rank
    results.sort(key=lambda x: (x["score"], x["exp"], x["hit"], x["n"]), reverse=True)

    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write("# Repeatable Setups (Bar Replay Mining)\n\n")
        if not results:
            f.write("_No setups met the filters._\n")
        else:
            f.write("| Setup | Symbol | N | Hit% | Exp/Trade | Vol | Score | Sum PnL |\n")
            f.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
            for r in results[:200]:
                f.write(f"| {r['setup']} | {r['symbol']} | {r['n']} | {r['hit']*100:.1f}% | {r['exp']:.2f} | {r['vol']:.2f} | {r['score']:.2f} | {r['sum']:.2f} |\n")

    print(f"[miner] wrote {args.out_md} with {len(results)} setups.")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(miner_main())
