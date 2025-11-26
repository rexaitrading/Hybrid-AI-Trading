from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay to Notion journaling stub (JSON-aware)")
    parser.add_argument("--symbol", required=True, help="Symbol, e.g. AAPL")
    parser.add_argument("--session", required=True, help="Session date, e.g. 2025-11-01")
    parser.add_argument(
        "--summary-json",
        help="Path to replay summary JSON produced by the replay engine.",
    )
    return parser.parse_args(argv)


def _load_summary(path: str | None) -> Dict[str, Any]:
    """
    Best-effort JSON loader.

    Expected shape (example):

    {
      "symbol": "AAPL",
      "session": "2025-11-01",
      "stats": {
        "trades": 25,
        "win_rate": 0.56,
        "avg_r": 0.45,
        "max_dd": -0.08,
        "gross_pnl": 1234.56,
        "net_pnl": 1180.12
      },
      "trades": [
        {"ts": "...", "side": "BUY", "qty": 100, "entry": 110.5, "exit": 111.2, "r": 0.7},
        ...
      ]
    }

    But the loader is tolerant: missing keys are simply omitted.
    """
    if not path:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as exc:  # noqa: BLE001
        # Keep this message ASCII-only to avoid encoding issues on Windows consoles.
        print(
            "[replay_to_notion] WARN: failed to load summary JSON:", 
            str(exc),
            file=sys.stderr,
        )
        return {}

    # We only keep JSON-serializable data; if raw is not a dict, wrap it.
    if not isinstance(raw, dict):
        return {"_raw": raw}
    return raw


def _normalize_summary(raw: Dict[str, Any], symbol: str, session: str) -> Dict[str, Any]:
    """
    Normalize raw summary JSON into a compact, predictable dict.

    We do not enforce a rigid schema here; we just extract common fields
    if present and keep the original under 'raw' for later evolution.
    """
    stats = raw.get("stats") or {}
    if not isinstance(stats, dict):
        stats = {}

    trades = raw.get("trades") or []
    if not isinstance(trades, list):
        trades = []

    norm: Dict[str, Any] = {
        "symbol": raw.get("symbol", symbol),
        "session": raw.get("session", session),
        "stats": {
            "trades": stats.get("trades"),
            "win_rate": stats.get("win_rate"),
            "avg_r": stats.get("avg_r"),
            "max_dd": stats.get("max_dd"),
            "gross_pnl": stats.get("gross_pnl"),
            "net_pnl": stats.get("net_pnl"),
        },
        "trades_sample": trades[:5],  # small sample to keep logs light
        "raw": raw,
    }
    return norm


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw_summary = _load_summary(args.summary_json)
    normalized = _normalize_summary(raw_summary, args.symbol, args.session)

    # Resolve repo root and logs dir
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    logs_dir = os.path.join(root, ".logs")
    os.makedirs(logs_dir, exist_ok=True)

    # NOTE: datetime.utcnow() is fine for this stub; later we may move to timezone-aware.
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_name = "replay_to_notion_{sym}_{sess}_{ts}.log".format(
        sym=args.symbol,
        sess=args.session.replace("-", ""),
        ts=ts,
    )
    log_path = os.path.join(logs_dir, log_name)

    payload = {
        "ts_utc": ts,
        "symbol": args.symbol,
        "session": args.session,
        "summary": normalized,
        "note": "JSON-aware stub  next phase will push into Notion.",
    }

    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # ASCII-only console message to avoid Windows charmap issues.
        print("[replay_to_notion] stub log written.")
        print("[replay_to_notion] log path:", log_path)
    except Exception:
        print("[replay_to_notion] ERROR: failed to write log.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())