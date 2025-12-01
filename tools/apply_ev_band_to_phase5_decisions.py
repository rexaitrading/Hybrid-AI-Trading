from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# We reuse the same JSON shape logic as phase5_gating_helpers,
# but keep this tool standalone so it can be run from PowerShell.
from phase5_gating_helpers import apply_ev_band_to_decision


SYMBOL_TO_REGIME = {
    "NVDA": "NVDA_BPLUS_LIVE",
    "SPY": "SPY_ORB_LIVE",
    "QQQ": "QQQ_ORB_LIVE",
}


def _find_first_list(obj: Any, depth: int = 0, max_depth: int = 5) -> Optional[List[Any]]:
    """Recursively search for the first list anywhere in the JSON structure."""
    if depth > max_depth:
        return None
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_first_list(v, depth + 1, max_depth)
            if found is not None:
                return found
    return None


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    """
    Load JSON file using the same conventions as phase5_gating_helpers:

      - top-level list
      - nested list inside a dict
      - single dict -> treated as one-row list
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    rows = _find_first_list(data)
    if rows is None:
        if isinstance(data, dict):
            rows = [data]
        else:
            raise SystemExit(
                f"Unexpected JSON shape in {path}, expected a list or a dict representing a single row."
            )

    if not isinstance(rows, list):
        raise SystemExit(
            f"Unexpected JSON shape in {path}, expected rows to be a list."
        )

    result: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            result.append(row)
    return result


def _write_rows(path: Path, rows: List[Dict[str, Any]]) -> None:
    """
    Write rows back in a simple list form.

    We do not try to reconstruct any exotic wrapper shape; consuming tools
    (phase5_gating_helpers, CSV converters) only care that it's a list of dicts.
    """
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, sort_keys=True)


def process_symbol(symbol: str) -> None:
    symbol_u = symbol.upper()
    if symbol_u not in SYMBOL_TO_REGIME:
        raise SystemExit(f"Unsupported symbol for EV-band annotation: {symbol_u}")

    regime = SYMBOL_TO_REGIME[symbol_u]
    fname = f"{symbol_u.lower()}_phase5_decisions.json"
    path = Path("logs") / fname

    if not path.exists():
        print(f"[EV-BAND] {symbol_u}: {path} does not exist, nothing to do.")
        return

    print(f"[EV-BAND] {symbol_u}: annotating EV-band in {path} (regime={regime})")

    rows = _load_rows(path)
    updated: List[Dict[str, Any]] = []

    for row in rows:
        # Ensure regime/symbol fields are present for the helper.
        row.setdefault("symbol", symbol_u)
        row.setdefault("regime", regime)

        # Let apply_ev_band_to_decision mutate the dict in-place.
        apply_ev_band_to_decision(row)
        updated.append(row)

    _write_rows(path, updated)
    print(f"[EV-BAND] {symbol_u}: completed, {len(updated)} rows updated.")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Annotate Phase-5 NVDA/SPY/QQQ decision JSON with EV-band fields."
    )
    parser.add_argument(
        "--symbol",
        choices=["NVDA", "SPY", "QQQ", "ALL"],
        default="ALL",
        help="Which symbol to process (default: ALL).",
    )
    args = parser.parse_args(argv)

    if args.symbol == "ALL":
        for sym in ["NVDA", "SPY", "QQQ"]:
            process_symbol(sym)
    else:
        process_symbol(args.symbol)


if __name__ == "__main__":
    main()