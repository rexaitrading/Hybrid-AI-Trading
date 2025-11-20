"""
Enrich NVDA B+ replay JSONL with session / regime / kelly_f / bar_replay_tag
and assign ranking / buckets, plus screenshot_path.

Pipeline:
  - Input: JSONL with raw trades (from replay or synthetic expansion).
  - For each trade:
      * session       (PRE / RTH / POST)
      * regime        (NVDA_BPLUS_REPLAY if missing)
      * kelly_f       (simple EV-based guess, >= 0)
      * bar_replay_tag (e.g. NVDA_BPLUS_2025-01-01)
      * replay_id     (same as bar_replay_tag if missing)
      * screenshot_path (e.g. charts/NVDA_BPLUS_2025-01-01.png)
  - Then:
      * gate_rank     (1 = best gate_score_v2)
      * gate_bucket   (A/B/C tiers)
      * pnl_rank      (1 = best gross_pnl_pct)
  - Output: enriched JSONL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# HAT path patch: add repo/src to sys.path so hybrid_ai_trading imports work
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from hybrid_ai_trading.replay.nvda_bplus_gate_score import compute_ev_from_trade




def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_ts(trade: Dict[str, Any]) -> datetime | None:
    ts = (
        trade.get("entry_ts")
        or trade.get("ts_entry")
        or trade.get("ts_trade")
    )
    if not ts:
        return None
    try:
        # Handles "YYYY-MM-DDTHH:MM:SS" style
        return datetime.fromisoformat(str(ts))
    except Exception:
        return None


def _infer_session(dt: datetime | None) -> str:
    """Simple session classifier based on hour-of-day.

    PRE  : before 09:30
    RTH  : 09:30 - 16:00
    POST : after 16:00
    """
    if dt is None:
        return "unknown"

    hm = dt.hour + dt.minute / 60.0
    if hm < 9.5:
        return "PRE"
    if hm < 16.0:
        return "RTH"
    return "POST"


def enrich_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Attach session/regime/kelly/tag/replay_id/screenshot_path to a trade dict copy."""
    t = dict(trade)

    # Session inference
    if not t.get("session"):
        dt = _parse_ts(t)
        t["session"] = _infer_session(dt)

    # Regime
    if not t.get("regime"):
        t["regime"] = "NVDA_BPLUS_REPLAY"

    # Kelly f (very simple EV-based guess; non-negative)
    if "kelly_f" not in t:
        ev = _safe_float(compute_ev_from_trade(t), 0.0)
        if ev < 0.0:
            ev = 0.0
        t["kelly_f"] = ev

    # Bar replay tag / replay_id
    if not t.get("bar_replay_tag") or not isinstance(t.get("bar_replay_tag"), str):
        dt = _parse_ts(t)
        if dt is not None:
            date_str = dt.date().isoformat()
        else:
            date_str = "unknown_date"
        tag = f"NVDA_BPLUS_{date_str}"
        t["bar_replay_tag"] = tag
        if not t.get("replay_id"):
            t["replay_id"] = tag

    # Screenshot path (local chart file path)  only if not already set
    if not t.get("screenshot_path") and t.get("bar_replay_tag"):
        t["screenshot_path"] = f"charts/{t['bar_replay_tag']}.png"

    return t


def load_trades(path: Path) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[ENRICH] [WARN] Skipping invalid JSON line")
                continue
            trades.append(obj)
    return trades


def write_trades(path: Path, trades: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for t in trades:
            f.write(json.dumps(t, ensure_ascii=False))
            f.write("\n")


def run(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        print(f"[ENRICH] Input JSONL not found: {input_path}")
        return

    trades = load_trades(input_path)
    print(f"[ENRICH] Loaded {len(trades)} trades from {input_path}")

    enriched: List[Dict[str, Any]] = []
    for t in trades:
        enriched.append(enrich_trade(t))

    # --- OPTION B analytics: ranking + bucket assignments ---

    # gate_rank (1=best) - we use EV as proxy if no gate_score field
    sorted_by_gate = sorted(
        enriched,
        key=lambda tr: float(tr.get("_gate_score_v2", tr.get("gate_score_v2", _safe_float(compute_ev_from_trade(tr), 0.0)))),
        reverse=True,
    )
    N_gate = len(sorted_by_gate)
    if N_gate > 0:
        for idx, tr in enumerate(sorted_by_gate, start=1):
            tr["gate_rank"] = idx
            # buckets: top 1/3 = A, next 1/3 = B, bottom 1/3 = C
            if idx <= N_gate / 3:
                tr["gate_bucket"] = "A"
            elif idx <= (2 * N_gate) / 3:
                tr["gate_bucket"] = "B"
            else:
                tr["gate_bucket"] = "C"

    # pnl_rank (1=best pnl%)
    sorted_by_pnl = sorted(
        enriched,
        key=lambda tr: float(tr.get("gross_pnl_pct", 0.0)),
        reverse=True,
    )
    for idx, tr in enumerate(sorted_by_pnl, start=1):
        tr["pnl_rank"] = idx

    write_trades(output_path, enriched)
    print(f"[ENRICH] Wrote {len(enriched)} trades to {output_path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Enrich NVDA B+ replay JSONL with session/regime/kelly_f/bar_replay_tag/screenshot_path and rankings."
    )
    ap.add_argument(
        "--input",
        required=True,
        help="Input JSONL path (existing replay trades).",
    )
    ap.add_argument(
        "--output",
        required=True,
        help="Output JSONL path (enriched trades).",
    )
    args = ap.parse_args()

    run(
        input_path=Path(args.input),
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()