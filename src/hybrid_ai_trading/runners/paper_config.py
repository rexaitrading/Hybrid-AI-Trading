# Stable parser + loader for Hybrid AI Quant Pro Paper Runner

from __future__ import annotations

import argparse
import pathlib
from typing import Any, Dict, List, Optional

import yaml


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="Hybrid AI Quant Pro Paper Runner")

    ap.add_argument(
        "--config",
        type=str,
        default="config/paper_runner.yaml",
        help="Path to runner config YAML.",
    )
    ap.add_argument(
        "--once", action="store_true", help="Run a single tick/batch and exit."
    )
    ap.add_argument(
        "--universe",
        type=str,
        default="AAPL,MSFT",
        help="Comma-separated symbols list.",
    )
    ap.add_argument(
        "--mdt", type=int, default=3, help="Market data throttle / cadence setting."
    )
    ap.add_argument("--client-id", type=int, default=3021, help="IBKR clientId.")
    ap.add_argument(
        "--log-file", type=str, default=None, help="Optional JSONL log file path."
    )
    ap.add_argument(
        "--dry-drill",
        action="store_true",
        help="Don't place/route orders; dry run signals only.",
    )
    ap.add_argument(
        "--snapshots-when-closed",
        action="store_true",
        help="When market is CLOSED and preflight is forced, still proceed to IB snapshots + QuantCore eval.",
    )
    ap.add_argument(
        "--enforce-riskhub",
        action="store_true",
        help="If set, deny actions when RiskHub returns ok=false (paper-safe gate).",
    )
    ap.add_argument(
        "--prefer-providers",
        action="store_true",
        help="Use provider prices to override IB snapshots when available.",
    )
    ap.add_argument(
        "--provider-only",
        action="store_true",
        help="Skip IB session and use provider prices only.",
    )
    return ap


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = build_parser()
    args, _ = ap.parse_known_args(argv)
    # Normalize convenience fields here if callers want them:
    # attach a parsed list view of universe (uppercased, stripped)
    u = getattr(args, "universe", "") or ""
    args.universe_list = [s.strip().upper() for s in u.split(",") if s.strip()]
    return args


def load_config(path: str) -> Dict[str, Any]:
    """Simple YAML loader used by runner/trader (resilient)."""
    try:
        pp = pathlib.Path(path)
        if not pp.exists():
            return {}
        txt = pp.read_text(encoding="utf-8")
        if not txt.strip():
            return {}
        data = yaml.safe_load(txt)
        return data or {}
    except Exception as e:
        # keep runner resilient
        return {"_error": f"load_config_failed: {e}"}
