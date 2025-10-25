from __future__ import annotations
import os
from typing import List, Dict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def render_symbol_snapshot(symbol: str, bars: List[dict], out_path: str, width: int = 720, height: int = 320) -> str:
    if not bars:
        return ""
    xs   = list(range(len(bars)))
    close= [float(b.get("close", 0)) for b in bars]
    high = [float(b.get("high",  c)) for c,b in zip(close,bars)]
    low  = [float(b.get("low",   c)) for c,b in zip(close,bars)]

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
    for i,(lo,hi) in enumerate(zip(low,high)):
        ax.vlines(i, lo, hi, color="black", linewidth=1.0)
    ax.plot(xs, close, linewidth=1.2)
    ax.set_title(f"{symbol} | n={len(bars)} last={close[-1]:.2f}")
    ax.grid(True, alpha=0.25)
    ax.margins(x=0.02, y=0.1)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path