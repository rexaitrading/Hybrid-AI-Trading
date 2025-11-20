import csv
import math
from collections import defaultdict
import matplotlib.pyplot as plt

def sniff_delimiter(path):
    with open(path, "r", encoding="utf-8") as f:
        sample = f.read(1024)
        dialect = csv.Sniffer().sniff(sample, delimiters=[",",";","|","\t"])
        return dialect

def load_sweep(path: str):
    dialect = sniff_delimiter(path)
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, dialect=dialect)
        for r in reader:
            rows.append({
                "date": r["date"],
                "orb_minutes": int(r["orb_minutes"]),
                "tp_r": float(r["tp_r"]),
                "trades": int(r["trades"]),
                "win_rate": float(r["win_rate"]),
                "ev": float(r["ev"]),
                "mean_pnl_pct": float(r["mean_pnl_pct"]),
                "mean_r": float(r["mean_r"]),
            })
    print(f"[PLOT] Loaded {len(rows)} rows using delimiter '{dialect.delimiter}'")
    return rows

def aggregate_ev(rows):
    sums = defaultdict(float)
    counts = defaultdict(int)
    for r in rows:
        k = (r["orb_minutes"], r["tp_r"])
        if math.isnan(r["ev"]): continue
        sums[k]+=r["ev"]
        counts[k]+=1
    return {k:sums[k]/counts[k] for k in sums if counts[k]}

def main():
    path="research/spy_orb_multi_day_sweep.csv"
    rows = load_sweep(path)
    if not rows:
        print("[PLOT] No rows.")
        return

    evmap = aggregate_ev(rows)
    tp_vals = sorted({k[1] for k in evmap})
    orb_vals= sorted({k[0] for k in evmap})

    plt.figure(figsize=(8,5))
    for tp in tp_vals:
        xs,ys=[],[]
        for orb in orb_vals:
            if (orb,tp) in evmap:
                xs.append(orb); ys.append(evmap[(orb,tp)])
        if xs:
            plt.plot(xs,ys,marker='o',label=f'TP {tp}R')

    plt.title("SPY ORB Mean EV vs ORB window")
    plt.xlabel("ORB minutes")
    plt.ylabel("Mean EV (R)")
    plt.grid(True,alpha=0.4)
    plt.legend()
    plt.tight_layout()
    out="research/spy_orb_ev_by_orb_window.png"
    plt.savefig(out,dpi=150)
    print("[PLOT] Saved:", out)

if __name__=="__main__":
    main()