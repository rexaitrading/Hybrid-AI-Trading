from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Any, Dict, List

JSONL_PATH = Path("logs") / "SPY_phase5_paperlive_results.jsonl"
CSV_PATH   = Path("logs") / "spy_phase5_paper_for_notion.csv"

FIELDS = [
    "ts",
    "symbol",
    "regime",
    "side",
    "realized_pnl",
    "ev",
]


def _load_ev_from_config() -> float:
    cfg_path = Path("config") / "phase5" / "ev_simple.json"
    fallback = 0.0075
    try:
        text = cfg_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception:
        return fallback

    for key in ("SPY_ORB_LIVE", "spy_orb_live", "SPY", "spy"):
        cfg = data.get(key)
        if isinstance(cfg, dict):
            for ev_key in ("ev_per_trade", "ev", "ev_mu", "expected_value"):
                v = cfg.get(ev_key)
                if v is not None:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        pass

    return fallback


_SPY_EV_PER_TRADE = _load_ev_from_config()


def _get_realized(rec: Dict[str, Any]) -> float | None:
    v = rec.get("realized_pnl")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _get_ev(rec: Dict[str, Any]) -> float:
    """
    EV priority:
    1) Use existing rec["ev"] if present and numeric AND not 0.0 (old EV rows like 1.5).
    2) Otherwise, use EV per trade from ev_simple.json (or fallback 0.0075).
    """
    v = rec.get("ev")
    if v is not None:
        try:
            v_f = float(v)
            if v_f != 0.0:
                return v_f
        except (TypeError, ValueError):
            pass

    return _SPY_EV_PER_TRADE


def convert() -> None:
    if not JSONL_PATH.exists():
        print(f"Source: {JSONL_PATH}")
        print("  SKIP: source JSONL not found.")
        return

    print(f"Source: {JSONL_PATH}")
    print(f"[SPY] Using EV per trade (from ev_simple or fallback): {_SPY_EV_PER_TRADE}")

    rows: List[Dict[str, Any]] = []

    with JSONL_PATH.open("r", encoding="utf-8") as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            if rec.get("symbol") != "SPY":
                continue
            if rec.get("regime") != "SPY_ORB_LIVE":
                continue
            if rec.get("side") != "SELL":
                continue

            ts     = rec.get("ts") or rec.get("entry_ts")
            symbol = rec.get("symbol", "SPY")
            regime = rec.get("regime", "SPY_ORB_LIVE")
            side   = rec.get("side", "SELL")

            realized = _get_realized(rec)
            ev_val   = _get_ev(rec)

            row = {
                "ts":           ts,
                "symbol":       symbol,
                "regime":       regime,
                "side":         side,
                "realized_pnl": realized,
                "ev":           ev_val,
            }
            rows.append(row)

    print(f"  Rows extracted for SPY_ORB_LIVE: {len(rows)}")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


if __name__ == "__main__":
    convert()