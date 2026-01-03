from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

@dataclass
class Bar:
    ts: str
    o: float
    h: float
    l: float
    c: float
    v: float

def read_bars_csv(path: Path) -> List[Bar]:
    bars: List[Bar] = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                bars.append(Bar(
                    ts=str(row.get("ts") or row.get("time") or row.get("timestamp") or ""),
                    o=float(row.get("open") or row.get("o") or 0.0),
                    h=float(row.get("high") or row.get("h") or 0.0),
                    l=float(row.get("low") or row.get("l") or 0.0),
                    c=float(row.get("close") or row.get("c") or 0.0),
                    v=float(row.get("volume") or row.get("v") or 0.0),
                ))
            except Exception:
                continue
    return bars

def vwap_series(bars: List[Bar]) -> List[float]:
    out: List[float] = []
    pv = 0.0
    vv = 0.0
    for b in bars:
        tp = (b.h + b.l + b.c) / 3.0
        pv += tp * b.v
        vv += b.v
        out.append((pv / vv) if vv > 0 else b.c)
    return out

def gen_bplus_signals(bars: List[Bar], orb_minutes: int = 5, cooldown_bars: int = 5) -> List[int]:
    # B+ long: breakout above ORB high and above VWAP, cooldown to avoid spam
    if len(bars) <= orb_minutes + 1:
        return []
    orb = bars[:orb_minutes]
    orb_hi = max(b.h for b in orb)
    vw = vwap_series(bars)

    sigs: List[int] = []
    cd = 0
    for i in range(orb_minutes, len(bars)):
        if cd > 0:
            cd -= 1
            continue
        if bars[i].c > orb_hi and bars[i].c > vw[i]:
            sigs.append(i)
            cd = cooldown_bars
    return sigs

def score_signals_v0(
    bars: List[Bar],
    signal_idx: List[int],
    risk_unit_usd: float = 100.0,
    fee_per_trade_usd: float = 0.35,
    slip_bps: float = 1.5,
    hold_bars: int = 10,
) -> List[Dict]:
    # 1-share toy PnL but real costs; edge_ratio normalized by risk_unit_usd
    events: List[Dict] = []
    if not bars:
        return events

    for i in signal_idx:
        entry = bars[i].c
        j = min(len(bars) - 1, i + max(1, hold_bars))
        exitp = bars[j].c

        slip = (entry * (slip_bps / 10000.0)) + (exitp * (slip_bps / 10000.0))
        fees = 2.0 * fee_per_trade_usd
        gross = (exitp - entry)
        net = gross - slip - fees

        edge_ratio = net / max(1e-9, risk_unit_usd)
        micro_cost = (slip + fees) / max(1e-9, risk_unit_usd)
        micro_score = max(0.0, min(1.0, 1.0 - micro_cost))

        events.append({
            "count_signals": 1,
            "pnl_samples": 1,
            "realized_pnl": float(net),
            "edge_ratio": float(edge_ratio),
            "micro_score": float(micro_score),
            "edge_source": "edge_model_v0",
            "micro_score_source": "edge_model_v0",
        })
    return events