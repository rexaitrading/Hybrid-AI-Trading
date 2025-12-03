from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from hybrid_ai_trading.risk.risk_phase5_ev_soft_veto import (
    phase5_ev_soft_veto_from_flags,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an EV-band enriched JSONL file into a flat CSV "
            "suitable for Notion / spreadsheet import, including soft EV veto fields."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file (e.g. logs/nvda_phase5_paperlive_with_ev_band.jsonl)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV file path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8") as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                rec: Dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Flatten the fields we care about for EV-band debugging.
            row: Dict[str, Any] = {
                # time / index
                "ts": rec.get("ts") or rec.get("entry_ts"),
                "idx": rec.get("idx"),

                # identity
                "symbol": rec.get("symbol"),
                "regime": rec.get("regime"),
                "side": rec.get("side"),
                "price": rec.get("price"),
                "qty": rec.get("qty"),
                "position_after": rec.get("position_after"),

                # PnL
                "realized_pnl": rec.get("realized_pnl"),
                "realized_pnl_phase5": (
                    (rec.get("phase5_result") or {}).get("realized_pnl")
                    if isinstance(rec.get("phase5_result"), dict)
                    else None
                ),

                # EV & EV-band info
                "ev": rec.get("ev"),
                "ev_band_abs": rec.get("ev_band_abs"),
                "ev_band_allowed": rec.get("ev_band_allowed"),
                "ev_band_reason": rec.get("ev_band_reason"),
                "ev_band_veto_applied": rec.get("ev_band_veto_applied"),
                "ev_band_veto_reason": rec.get("ev_band_veto_reason"),
                "locked_by_ev_band": rec.get("locked_by_ev_band"),
            }

            # Derive soft EV veto flags from EV-band flags.
            ev_flags: Dict[str, Any] = {
                "ev_band_allowed": row["ev_band_allowed"],
                "ev_band_reason": row["ev_band_reason"],
                "ev_band_veto_applied": row["ev_band_veto_applied"],
                "ev_band_veto_reason": row["ev_band_veto_reason"],
                "locked_by_ev_band": row["locked_by_ev_band"],
            }
            soft = phase5_ev_soft_veto_from_flags(ev_flags)
            row["soft_ev_veto"] = soft.get("soft_ev_veto")
            row["soft_ev_reason"] = soft.get("soft_ev_reason")

            rows.append(row)

    # Determine CSV field order
    fieldnames = [
        "ts",
        "idx",
        "symbol",
        "regime",
        "side",
        "price",
        "qty",
        "position_after",
        "realized_pnl",
        "realized_pnl_phase5",
        "ev",
        "ev_band_abs",
        "ev_band_allowed",
        "ev_band_reason",
        "ev_band_veto_applied",
        "ev_band_veto_reason",
        "locked_by_ev_band",
        "soft_ev_veto",
        "soft_ev_reason",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()