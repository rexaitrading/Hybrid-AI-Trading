"""
Build NVDA Phase-5 decisions JSON by joining:

- logs/nvda_phase5_replay_gated.jsonl (decisions, no ts)
- logs/paper_trades.jsonl (NVDA trades with ts, price, qty, etc.)

Output:
  logs/nvda_phase5_decisions.json

Join strategy (simple, deterministic):
- Take NVDA rows from both files in file order.
- Sort paper_trades NVDA rows by ts ascending.
- Zip them by index: i-th decision row <- i-th trade row.
- Use trade.ts as ts_trade, plus entry_px/qty/side/etc from decisions file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_nvda_decisions_source() -> List[Dict[str, Any]]:
    path = Path("logs") / "nvda_phase5_replay_gated.jsonl"
    print("Decisions source:", path, "exists:", path.exists())
    if not path.exists():
        raise SystemExit("nvda_phase5_replay_gated.jsonl not found in logs/")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  WARN: JSON decode error in {path} at line {line_no}: {e}")
                continue
            if str(row.get("symbol", "")).upper() != "NVDA":
                continue
            rows.append(row)

    print(f"  Loaded {len(rows)} NVDA decision rows from {path}")
    return rows


def load_nvda_trades_source() -> List[Dict[str, Any]]:
    path = Path("logs") / "paper_trades.jsonl"
    print("Trades source:", path, "exists:", path.exists())
    if not path.exists():
        raise SystemExit("paper_trades.jsonl not found in logs/")

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  WARN: JSON decode error in {path} at line {line_no}: {e}")
                continue
            if str(row.get("symbol", "")).upper() != "NVDA":
                continue
            # Require a ts field for identity
            ts = row.get("ts")
            if not ts:
                continue
            rows.append(row)

    # Sort by timestamp string for deterministic pairing
    rows.sort(key=lambda r: str(r.get("ts")))
    print(f"  Loaded {len(rows)} NVDA trade rows with ts from {path}")
    return rows


def build_nvda_decisions() -> None:
    decisions_src = load_nvda_decisions_source()
    trades_src = load_nvda_trades_source()

    if not decisions_src:
        print("No NVDA decisions to build from. Exiting.")
        return
    if not trades_src:
        print("No NVDA trades with ts to build from. Exiting.")
        return

    n_pairs = min(len(decisions_src), len(trades_src))
    if len(decisions_src) != len(trades_src):
        print(
            f"WARNING: decisions={len(decisions_src)} vs trades={len(trades_src)}; "
            f"will pair only first {n_pairs} rows."
        )

    out_rows: List[Dict[str, Any]] = []
    for idx in range(n_pairs):
        dec = decisions_src[idx]
        trade = trades_src[idx]

        ts_val = str(trade.get("ts"))
        entry_px = dec.get("entry_px")
        if entry_px is None:
            entry_px = trade.get("price")

        decision_row: Dict[str, Any] = {
            "symbol": "NVDA",
            "ts_trade": ts_val,  # KEY: Phase-5 identity
            "entry_px": entry_px,
            "side": dec.get("side"),
            "side_raw": dec.get("side_raw", dec.get("side")),
            "qty": dec.get("qty") or trade.get("qty"),
            "gate_score_v2": dec.get("gate_score_v2"),
            "kelly_f": dec.get("kelly_f"),
            "phase5_sim_allow": dec.get("phase5_sim_allow"),
            "phase5_sim_reason": dec.get("phase5_sim_reason"),
        }

        out_rows.append(decision_row)

    dst = Path("logs") / "nvda_phase5_decisions.json"
    dst.write_text(json.dumps(out_rows, indent=2), encoding="utf-8")
    print(f"\nWrote {len(out_rows)} NVDA decision rows with ts_trade to {dst}")


def main() -> None:
    build_nvda_decisions()


if __name__ == "__main__":
    main()
