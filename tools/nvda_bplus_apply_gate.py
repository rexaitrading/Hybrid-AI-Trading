from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

from hybrid_ai_trading.replay.nvda_bplus_gate_score import (
    compute_gate_score_v2,
    passes_micro_gate,
)


def _iter_trades(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # skip malformed lines
                continue


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply NVDA B+ micro-mode gate to replay JSONL."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file (e.g. research/nvda_bplus_replay_trades.jsonl)",
    )
    parser.add_argument(
        "--output",
        help="Output JSONL file. Default: <input_stem>_g{min_gate_score:.2f}.jsonl",
    )
    parser.add_argument(
        "--min-gate-score",
        type=float,
        default=0.04,
        help="Minimum gate_score_v2 for a trade to be kept (default: 0.04)",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[GATE] input not found: {in_path}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = in_path.with_name(
            f"{in_path.stem}_g{args.min_gate_score:.2f}.jsonl"
        )

    total = 0
    kept = 0

    with out_path.open("w", encoding="utf-8") as out:
        for trade in _iter_trades(in_path):
            total += 1

            # ensure gate_score_v2 present
            try:
                score = trade.get("gate_score_v2", None)
            except Exception:
                score = None

            if score is None:
                try:
                    score = compute_gate_score_v2(trade)
                    trade["gate_score_v2"] = score
                except Exception:
                    # cannot compute score, drop this trade
                    continue

            if not passes_micro_gate(trade, args.min_gate_score):
                continue

            out.write(json.dumps(trade, ensure_ascii=False) + "\n")
            kept += 1

    print(
        f"[GATE] kept {kept}/{total} trades at min_gate_score={args.min_gate_score:.4f}"
    )
    print(f"[GATE] wrote gated file: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
