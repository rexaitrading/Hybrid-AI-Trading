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
    TRUE ORB+VWAP GateScore (deterministic, replay-driven).

    - ORB window: strict minutes but bounded by available bars (min(15, available-1))
    - VWAP deviation bands
    - Regime hook (use existing module if present; else deterministic fallback)
    - Exports honest diagnostics: _NVDA_GS_COUNT_SIGNALS / _NVDA_GS_PNL_SAMPLES
    """
    from pathlib import Path
    import math
    import pandas as pd

    rr = repo_root or Path(__file__).resolve().parents[3]
    csv_path = rr / "data" / "nvda_1min_sample.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Replay NVDA CSV not found at {csv_path}")

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("Replay NVDA CSV empty")

    # normalize columns
    need_cols = {"timestamp","open","high","low","close","volume"}
    if not need_cols.issubset(set(df.columns)):
        raise ValueError(f"Replay NVDA CSV missing cols: {sorted(list(need_cols - set(df.columns)))}")

    # index
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()
    df = df.set_index("timestamp").sort_index()
    if len(df) < 3:
        raise ValueError("Not enough replay bars for ORB+VWAP (need >=3)")

    # VWAP
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"].fillna(0.0).astype(float)
    w = vol.where(vol > 0.0, 1.0)
    df["vwap"] = (tp * w).cumsum() / w.cumsum().clip(lower=1e-9)

    # Strict ORB minutes, bounded by available bars
    from hybrid_ai_trading.strategies.orb_vwap import ORBVWAPStrategy, ORBVWAPConfig
    orb_minutes = int(min(15, max(1, len(df)-1)))
    cfg = ORBVWAPConfig(open_range_minutes=orb_minutes, vwap_confirm=True)
    strat = ORBVWAPStrategy(cfg)

    session_open = df.index.min()
    sigdf = strat.generate_signals(df[["open","high","low","close","vwap"]], session_open=session_open)

    # Honest diagnostics
    # count_signals: number of post-ORB bars that touch ORH/ORL (potential triggers)
    end_or = session_open + pd.Timedelta(minutes=orb_minutes)
    post = sigdf.index >= end_or
    orh = float(sigdf.attrs.get("orb_high", float("nan")))
    orl = float(sigdf.attrs.get("orb_low", float("nan")))
    touches = 0
    if not math.isnan(orh) and not math.isnan(orl):
        touches = int(((post) & ((sigdf["high"] >= orh) | (sigdf["low"] <= orl))).sum())
    count_signals = max(0, touches)
    pnl_samples = int(max(0, post.sum()))
    globals()["_NVDA_GS_COUNT_SIGNALS"] = int(count_signals)
    globals()["_NVDA_GS_PNL_SAMPLES"] = int(pnl_samples)

    # Determine signal direction (first breakout only per strategy)
    if "signal" not in sigdf.columns:
        return 0.0
    sidx = sigdf.index[sigdf["signal"] != 0]
    if len(sidx) < 1:
        return 0.0
    entry_ts = sidx[0]
    direction = int(sigdf.loc[entry_ts, "signal"])

    # VWAP deviation at entry
    entry_close = float(sigdf.loc[entry_ts, "close"])
    entry_vwap  = float(sigdf.loc[entry_ts, "vwap"])
    vwap_dev = (entry_close - entry_vwap) / max(1e-9, entry_vwap)

    # Breakout strength band (normalized to OR range)
    orb_range = max(1e-9, (orh - orl))
    orb_mid = (orh + orl) / 2.0
    orb_strength = (entry_close - orb_mid) / orb_range

    # VWAP deviation bands
    # band0: |dev| < 0.10% ; band1: 0.10%-0.25% ; band2: >0.25%
    adev = abs(vwap_dev)
    if adev < 0.001:
        dev_band = 0.25
    elif adev < 0.0025:
        dev_band = 0.60
    else:
        dev_band = 1.00

    # Regime hook (best-effort). Fallback: trend+vol penalty.
    regime_mult = 1.0
    try:
        # If you have a regime detector, map it to a multiplier deterministically
        from hybrid_ai_trading.regime.regime_detector import RegimeDetector
        rd = RegimeDetector()
        reg = rd.detect(sigdf)  # expected to be deterministic on df
        # example mapping
        if str(reg).lower().find("trend") >= 0:
            regime_mult = 1.05
        elif str(reg).lower().find("chop") >= 0:
            regime_mult = 0.85
    except Exception:
        # fallback vol penalty
        closes = sigdf["close"].astype(float).tolist()
        xs = closes[-min(20, len(closes)):]
        rets = []
        for i in range(1, len(xs)):
            if xs[i-1] > 0:
                rets.append((xs[i]-xs[i-1]) / xs[i-1])
        if len(rets) >= 2:
            m = sum(rets) / len(rets)
            var = sum((x-m)*(x-m) for x in rets) / max(1, (len(rets)-1))
            vol = math.sqrt(max(0.0, var))
            if vol > 0.02:
                regime_mult = 0.5

    # Score combine (directional)
    raw = (0.60 * orb_strength) + (2.00 * dev_band) + (0.20 * (1.0 if direction > 0 else -1.0))
    score = float(max(-1.0, min(1.0, raw * regime_mult)))
    return score

