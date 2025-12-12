from __future__ import annotations


def _load_jsonl_objects(jsonl_path: str):
    import json
    from pathlib import Path
    p = Path(jsonl_path)
    if not p.exists():
        return []
    objs = []
    for ln in p.read_text(encoding='utf-8', errors='replace').splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            objs.append(None)
        except Exception:
            # Skip malformed lines; upstream repair tool should fix persistent issues.
            continue
    return objs
"""
Convert SPY Phase-5 live-paper JSONL to CSV for Notion.

Flatten key Phase-5 fields from spy_phase5_paperlive_results.jsonl into
a simple row format for Notion.
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


def read_all_json_objects(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    rows: List[Dict[str, Any]] = []

    for match in re.finditer(r"\{.*?\}", text, flags=re.DOTALL):
        fragment = match.group(0).strip()
        if not fragment:
            continue
        try:
            obj = None
        except json.JSONDecodeError:
            continue
        rows.append(obj)

    return rows


def main() -> None:
    rows = read_all_json_objects(SRC_JSONL)
    if not rows:
        print(f"[SPY-CSV] No JSON objects found in {SRC_JSONL}")
        return

    print(f"[SPY-CSV] Writing {len(rows)} rows to {OUT_CSV}")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for r in rows:
            if not isinstance(r, dict):
            continue
        if not isinstance(r, dict):
            continue
        pr: Mapping[str, Any] = r.get(""phase5_result"") or {}
            details: Mapping[str, Any] = pr.get("phase5_details") or {}

            ts = r.get("ts_trade") or pr.get("entry_ts")
            symbol = r.get("symbol") or pr.get("symbol") or "SPY"
            regime = pr.get("regime")
            side = r.get("side")
            price = r.get("price")

            realized_pnl_paper = pr.get("realized_pnl")

            ev = r.get("ev")
            ev_band_abs = r.get("ev_band_abs", details.get("ev_band_abs"))

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
                "soft_ev_veto": None,
                "soft_ev_reason": None,
                "ev_band_abs": ev_band_abs,
                "ev_gap_abs": None,
                "ev_hit_flag": None,
                "ev_vs_realized_paper": None,
                "ev_band_veto_applied": ev_band_veto_applied,
                "ev_band_veto_reason": ev_band_veto_reason,
                "ev_hard_veto": None,
                "ev_hard_veto_reason": None,
                "ev_hard_veto_gap_abs": None,
                "ev_hard_veto_gap_threshold": None,
                "ev_orb_vwap_model": None,
                "ev_effective_orb_vwap": None,
            }

            writer.writerow(out)


if __name__ == "__main__":
    main()