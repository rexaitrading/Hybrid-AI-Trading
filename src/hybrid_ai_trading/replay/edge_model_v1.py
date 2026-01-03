from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


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
                bars.append(
                    Bar(
                        ts=str(row.get("ts") or row.get("time") or row.get("timestamp") or ""),
                        o=float(row.get("open") or row.get("o") or 0.0),
                        h=float(row.get("high") or row.get("h") or 0.0),
                        l=float(row.get("low") or row.get("l") or 0.0),
                        c=float(row.get("close") or row.get("c") or 0.0),
                        v=float(row.get("volume") or row.get("v") or 0.0),
                    )
                )
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


def score_signals_v1(
    bars: List[Bar],
    signal_idx: List[int],
    risk_unit_usd: float = 100.0,
    fee_per_trade_usd: float = 0.35,
    slip_bps: float = 1.5,
    hold_bars: int = 30,
    orb_minutes: int = 5,
    r_mult_tp: float = 1.2,
    max_shares: int = 500,
) -> List[Dict]:
    """
    Risk-sized 1R model:
      - size = floor(risk_unit_usd / stop_distance)
      - stop_distance = max(orb_range, 0.10)  (simple proxy; later upgrade to ATR)
      - exit: stop/target, VWAP-fail, or time stop
      - costs: slippage on entry+exit + roundtrip fees
    """
    events: List[Dict] = []
    if not bars or not signal_idx:
        return events

    vw = vwap_series(bars)
    orb = bars[:max(1, orb_minutes)]
    orb_hi = max(b.h for b in orb)
    orb_lo = min(b.l for b in orb)
    orb_range = max(0.0001, orb_hi - orb_lo)
    stop_dist = max(0.10, orb_range)

    for i in signal_idx:
        entry = bars[i].c

        # shares sized to risk_unit_usd, capped
        shares = int(max(1.0, min(float(max_shares), (risk_unit_usd / max(1e-9, stop_dist)))))
        stop = entry - stop_dist
        tgt = entry + (r_mult_tp * stop_dist)

        j_end = min(len(bars) - 1, i + max(1, hold_bars))
        exit_px: Optional[float] = None

        # simulate forward
        for j in range(i + 1, j_end + 1):
            # stop/target intrabar
            if bars[j].l <= stop:
                exit_px = stop
                break
            if bars[j].h >= tgt:
                exit_px = tgt
                break
            # VWAP fail exit (close back under VWAP after entry)
            if bars[j].c < vw[j]:
                exit_px = bars[j].c
                break

        if exit_px is None:
            exit_px = bars[j_end].c

        # costs
        slip = (entry * (slip_bps / 10000.0)) + (exit_px * (slip_bps / 10000.0))
        fees = 2.0 * fee_per_trade_usd

        gross = (exit_px - entry) * shares
        net = gross - (slip * shares) - fees

        edge_ratio = net / max(1e-9, risk_unit_usd)
        micro_cost = ((slip * shares) + fees) / max(1e-9, risk_unit_usd)
        micro_score = max(0.0, min(1.0, 1.0 - micro_cost))

        events.append(
            {
                "count_signals": 1,
                "pnl_samples": 1,
                "realized_pnl": float(net),
                "edge_ratio": float(edge_ratio),
                "micro_score": float(micro_score),
                "edge_source": "edge_model_v1",
                "micro_score_source": "edge_model_v1",
            }
        )

    return events