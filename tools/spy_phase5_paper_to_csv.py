from __future__ import annotations


def _load_jsonl_objects(jsonl_path: str):
    import json
    from pathlib import Path
    p = Path(jsonl_path)
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding='utf-8', errors='replace').splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        if obj is not None:
            out.append(obj)
    return out
"""
Convert SPY Phase-5 live-paper JSONL to CSV for Notion.

- Reads ALL JSON objects from logs/spy_phase5_paperlive_results.jsonl,
  even if multiple JSON objects end up on one physical line.
- Flattens key Phase-5 fields (regime, reason, EV band veto) into
  simple columns so Notion views can filter/sort cleanly.
"""

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping

ROOT = Path(".").resolve()
SRC_JSONL = ROOT / "logs" / "spy_phase5_paperlive_results.jsonl"
OUT_CSV   = ROOT / "logs" / "spy_phase5_paper_for_notion.csv"


FIELDS: List[str] = [
    "ts",
    "symbol",
    "regime",
    "side",
    "price",
    "realized_pnl_paper",
    "ev",
    "phase5_allowed",
    "phase5_reason",
    # soft EV diagnostics (not wired yet)
    "soft_ev_veto",
    "soft_ev_reason",
    "ev_band_abs",
    "ev_gap_abs",
    "ev_hit_flag",
    "ev_vs_realized_paper",
    "ev_band_veto_applied",
    "ev_band_veto_reason",
    # hard EV veto suggestion (log-only, not wired yet)
    "ev_hard_veto",
    "ev_hard_veto_reason",
    "ev_hard_veto_gap_abs",
    "ev_hard_veto_gap_threshold",
    # ORB+VWAP model EV (log-only, not wired yet)
    "ev_orb_vwap_model",
    "ev_effective_orb_vwap",
]


def read_all_json_objects(path):
    """
    Strict JSONL reader: 1 JSON object per line.
    Returns list[dict]. Skips blank lines. Skips corrupt lines.
    """
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return []

    rows = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows
def main() -> None:
    rows = read_all_json_objects(SRC_JSONL)
    if not rows:
        print(f"[SPY-CSV] No JSON objects found in {SRC_JSONL}")
        return

    print(f"[SPY-CSV] Flattening {len(rows)} rows from {SRC_JSONL} into {OUT_CSV}")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for r in rows:
            pr: Mapping[str, Any] = (r.get("phase5_result") if isinstance(r, dict) else {}) or {}
            details: Mapping[str, Any] = pr.get("phase5_details") or {}

            # Core fields
            ts = r.get("ts") or r.get("ts_trade") or pr.get("entry_ts")
            symbol = r.get("symbol") or pr.get("symbol") or "SPY"
            regime = pr.get("regime")
            side = r.get("side") or pr.get("side")
            price = r.get("price")

            # PnL normalization
            realized_pnl_paper = r.get("realized_pnl_paper", pr.get("realized_pnl"))

            # EV fields
            ev = r.get("ev", pr.get("ev"))
            ev_band_abs = r.get("ev_band_abs", pr.get("ev_band_abs", details.get("ev_band_abs")))

            # Phase-5 gating flags
            phase5_status = pr.get("status")
            phase5_allowed = bool(phase5_status == "ok")
            phase5_reason = pr.get("phase5_reason")

            ev_band_veto_applied = pr.get("phase5_ev_band_veto")
            ev_band_veto_reason = pr.get("phase5_ev_band_reason")

            out: Dict[str, Any] = {
                "ts": ts,
                "symbol": symbol,
                "regime": regime,
                "side": side,
                "price": price,
                "realized_pnl_paper": realized_pnl_paper,
                "ev": ev,
                "phase5_allowed": phase5_allowed,
                "phase5_reason": phase5_reason,
                # soft EV diagnostics (not wired yet)
                "soft_ev_veto": None,
                "soft_ev_reason": None,
                "ev_band_abs": ev_band_abs,
                "ev_gap_abs": None,
                "ev_hit_flag": None,
                "ev_vs_realized_paper": None,
                "ev_band_veto_applied": ev_band_veto_applied,
                "ev_band_veto_reason": ev_band_veto_reason,
                # hard EV veto suggestion (log-only, not wired yet)
                "ev_hard_veto": None,
                "ev_hard_veto_reason": None,
                "ev_hard_veto_gap_abs": None,
                "ev_hard_veto_gap_threshold": None,
                # ORB+VWAP model EV (log-only, not wired yet)
                "ev_orb_vwap_model": None,
                "ev_effective_orb_vwap": None,
            }

            writer.writerow(out)


if __name__ == "__main__":
    main()