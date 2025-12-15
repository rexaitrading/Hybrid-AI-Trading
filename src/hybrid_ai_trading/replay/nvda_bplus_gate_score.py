from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Optional


@dataclass
class GateScoreHealth:
    symbol: str
    count_signals: int
    pnl_samples: int
    mean_edge_ratio: float
    mean_micro_score: float
    mean_pnl: float


def _parse_int(row: dict, key: str, default: int = 0) -> int:
    try:
        val = row.get(key)
        if val is None or val == "":
            return default
        return int(val)
    except (TypeError, ValueError):
        return default


def _parse_float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        val = row.get(key)
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def load_nvda_gatescore_health(repo_root: Optional[Path] = None) -> GateScoreHealth:
    """
    Load the latest GateScore summary for NVDA from logs/gatescore_pnl_summary.csv.

    This is used by tools/_nvda_gate_score_smoke.py and Phase-3 diagnostics.
    """
    if repo_root is None:
        # .../src/hybrid_ai_trading/replay/nvda_bplus_gate_score.py -> repo root = parents[3]
        repo_root = Path(__file__).resolve().parents[3]

    csv_path = repo_root / "logs" / "gatescore_pnl_summary.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"GateScore PnL summary not found at {csv_path}")

    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        nvda_rows = [row for row in reader if row.get("symbol") == "NVDA"]

    if not nvda_rows:
        raise ValueError("No NVDA rows found in gatescore_pnl_summary.csv")

    # Use the last row for NVDA as the current summary
    row = nvda_rows[-1]

    return GateScoreHealth(
        symbol="NVDA",
        count_signals=_parse_int(row, "count_signals", 0),
        pnl_samples=_parse_int(row, "pnl_samples", 0),
        mean_edge_ratio=_parse_float(row, "mean_edge_ratio", 0.0),
        mean_micro_score=_parse_float(row, "mean_micro_score", 0.0),
        mean_pnl=_parse_float(row, "mean_pnl", 0.0),
    )

def compute_nvda_gatescore_today(repo_root: Optional[Path] = None) -> float:
    """
    GO REPLAY SCORE – ORB

    Deterministic GateScore from Phase-1 replay CSV (no trades dependency).
    Works with small replay sets by using min() windows (reduced confidence).

    CSV schema: timestamp,symbol,open,high,low,close,volume

    Components (bounded):
      1) ORB strength: (last_close - ORB_mid) / ORB_range
      2) VWAP deviation: (last_close - vwap) / vwap
      3) Regime filter: trend sign + volatility penalty

    Returns score in [-1, +1].
    Fail-closed: raises if replay CSV missing/unreadable/insufficient rows.
    """
    from pathlib import Path
    import csv
    import math

    rr = repo_root or Path(__file__).resolve().parents[3]
    csv_path = rr / "data" / "nvda_1min_sample.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Replay NVDA CSV not found at {csv_path}")

    bars = []  # (o,h,l,c,v)
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                o = float(row["open"]); h = float(row["high"]); l = float(row["low"]); c = float(row["close"])
                v = float(row.get("volume") or 0.0)
            except Exception:
                continue
            bars.append((o,h,l,c,v))

    if len(bars) < 3:
        raise ValueError("Not enough replay bars to compute ORB score (need >=3)")

    # ORB window: min(15, available)
    orb_n = min(15, len(bars))
    orb = bars[:orb_n]
    orb_high = max(x[1] for x in orb)
    orb_low  = min(x[2] for x in orb)
    orb_range = max(1e-9, orb_high - orb_low)
    orb_mid = (orb_high + orb_low) / 2.0

    last_close = bars[-1][3]

    # VWAP (typical price * volume)
    num = 0.0; den = 0.0
    for (o,h,l,c,v) in bars:
        w = v if v > 0 else 1.0
        tp = (h + l + c) / 3.0
        num += tp * w
        den += w
    vwap = num / max(1e-9, den)

    orb_strength = (last_close - orb_mid) / orb_range
    orb_strength = max(-2.0, min(2.0, orb_strength))

    vwap_dev = (last_close - vwap) / max(1e-9, vwap)
    vwap_dev = max(-0.05, min(0.05, vwap_dev))

    # Trend sign from last min(10, available) bars
    look = min(10, len(bars))
    base = bars[-look][3]
    trend = 0.0
    if base > 0:
        trend = (last_close - base) / base
    trend_sign = 1.0 if trend > 0 else (-1.0 if trend < 0 else 0.0)

    # Vol penalty from last min(20, available) returns
    win = min(20, len(bars)-1)
    xs = [b[3] for b in bars[-(win+1):]]
    rets = []
    for i in range(1, len(xs)):
        p0 = xs[i-1]; p1 = xs[i]
        if p0 > 0:
            rets.append((p1 - p0) / p0)
    if len(rets) < 2:
        raise ValueError("Not enough returns for vol estimate")
    m = sum(rets) / len(rets)
    var = sum((x - m)*(x - m) for x in rets) / max(1, (len(rets)-1))
    vol = math.sqrt(max(0.0, var))
    vol_penalty = 1.0 if vol <= 0.02 else 0.5

    # Combine (ORB dominates; VWAP confirms; trend stabilizes)
    score = (0.60 * orb_strength) + (8.0 * vwap_dev) + (0.20 * trend_sign)
    score *= vol_penalty

    if score > 1.0: score = 1.0
    if score < -1.0: score = -1.0
    return float(score)

