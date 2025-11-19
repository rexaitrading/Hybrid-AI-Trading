from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


REQUIRED_FIELDS = {
    "no_averaging_down": bool,
    "min_add_cushion_bp": (int, float),
    "daily_loss_cap_pct": (int, float),
    "daily_loss_cap_notional": (int, float),
    "symbol_daily_loss_cap_bp": (int, float),
    "symbol_max_trades_per_day": int,
    "max_open_positions": int,
}


def validate_phase5_sketch(sketch: Dict[str, Any], *, symbol: str, path: Path) -> List[str]:
    """Validate a phase5_risk_sketch object and return a list of error strings."""

    errors: List[str] = []

    # Required fields and basic type checks
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in sketch:
            errors.append(f"{path} [{symbol}]: missing required field '{field}'")
            continue
        value = sketch[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"{path} [{symbol}]: field '{field}' has wrong type {type(value).__name__}, "
                f"expected {expected_type}"
            )

    # Optional notes
    notes = sketch.get("notes")
    if notes is not None:
        if not isinstance(notes, list):
            errors.append(f"{path} [{symbol}]: 'notes' must be a list of strings if present")
        else:
            for i, item in enumerate(notes):
                if not isinstance(item, str):
                    errors.append(
                        f"{path} [{symbol}]: notes[{i}] has type {type(item).__name__}, expected str"
                    )

    # Simple semantic checks (non-strict: warnings only)
    dl_pct = sketch.get("daily_loss_cap_pct")
    if isinstance(dl_pct, (int, float)) and dl_pct > 0:
        errors.append(
            f"{path} [{symbol}]: daily_loss_cap_pct={dl_pct!r} > 0; "
            "Phase5 caps are usually negative (loss threshold)."
        )

    dl_notional = sketch.get("daily_loss_cap_notional")
    if isinstance(dl_notional, (int, float)) and dl_notional > 0:
        errors.append(
            f"{path} [{symbol}]: daily_loss_cap_notional={dl_notional!r} > 0; "
            "Phase5 caps are usually negative (loss threshold)."
        )

    symbol_cap = sketch.get("symbol_daily_loss_cap_bp")
    if isinstance(symbol_cap, (int, float)) and symbol_cap > 0:
        errors.append(
            f"{path} [{symbol}]: symbol_daily_loss_cap_bp={symbol_cap!r} > 0; "
            "Phase5 symbol loss caps are usually negative (loss threshold)."
        )

    return errors


def validate_config_file(path: Path) -> Tuple[bool, List[str]]:
    """Validate a single thresholds JSON file for Phase5 sketch consistency."""

    if not path.exists():
        return False, [f"{path}: file not found"]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, [f"{path}: failed to parse JSON: {exc!r}"]

    if not isinstance(raw, dict):
        return False, [f"{path}: expected top-level JSON object, got {type(raw).__name__}"]

    symbol = raw.get("symbol", "UNKNOWN")
    strategy = raw.get("strategy", "UNKNOWN")

    sketch = raw.get("phase5_risk_sketch")
    if sketch is None:
        # Not an error for all symbols: SPY/QQQ may intentionally omit
        # Phase5 sketch while Phase5 is disabled for them.
        return True, [f"{path} [{symbol}/{strategy}]: no phase5_risk_sketch (OK if Phase5 disabled)."]

    if not isinstance(sketch, dict):
        return False, [f"{path} [{symbol}/{strategy}]: phase5_risk_sketch must be an object"]

    errors = validate_phase5_sketch(sketch, symbol=str(symbol), path=path)

    if errors:
        return False, errors

    return True, [f"{path} [{symbol}/{strategy}]: phase5_risk_sketch OK"]


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Phase5 risk sketch JSON for ORB/VWAP configs."
    )
    parser.add_argument(
        "configs",
        nargs="+",
        help="Paths to threshold JSON files (e.g. config/orb_vwap_aapl_thresholds.json)",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    any_errors = False

    for cfg_path_str in args.configs:
        path = Path(cfg_path_str)
        ok, messages = validate_config_file(path)
        for msg in messages:
            print(msg)
        if not ok:
            any_errors = True

    return 1 if any_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())