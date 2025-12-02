from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.risk.ev_band_flags import evaluate_ev_band_for_trade


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a trade JSONL log, add EV-band flags using "
            "evaluate_ev_band_for_trade(), and write a new JSONL."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input trade JSONL file (e.g. logs/nvda_phase5_paperlive_results.jsonl)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSONL file with EV-band fields appended.",
    )
    parser.add_argument(
        "--default-regime",
        default=None,
        help="Optional regime to use if a row has no 'regime' field.",
    )
    return parser.parse_args()


def process_line(record: Dict[str, Any], default_regime: str | None) -> Dict[str, Any]:
    """
    Given a single JSON record, call evaluate_ev_band_for_trade()
    and merge the resulting flags into the record.
    """
    regime = record.get("regime") or default_regime
    ev = record.get("ev")

    flags: Dict[str, Any]
    if regime is None:
        # No regime available -> just log reason; no veto
        flags = {
            "ev_band_allowed": None,
            "ev_band_reason": "regime_missing",
            "ev_band_veto_applied": False,
            "ev_band_veto_reason": None,
            "locked_by_ev_band": False,
        }
    else:
        flags = evaluate_ev_band_for_trade(regime=regime, ev=ev)

    record.update(flags)
    return record


def main() -> None:
    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count_in = 0
    count_out = 0

    with input_path.open("r", encoding="utf-8") as fin, \
            output_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            count_in += 1
            try:
                record: Dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines but keep going.
                continue

            updated = process_line(record, default_regime=args.default_regime)
            fout.write(json.dumps(updated, sort_keys=True) + "\n")
            count_out += 1

    print(f"Processed {count_in} lines, wrote {count_out} lines to {output_path}")


if __name__ == "__main__":
    main()