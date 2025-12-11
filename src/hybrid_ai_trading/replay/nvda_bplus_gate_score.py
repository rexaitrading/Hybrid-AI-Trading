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