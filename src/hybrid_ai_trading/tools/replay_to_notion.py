"""
Replay to Notion Journaling Stub

- Intended entrypoint:
    python -m hybrid_ai_trading.tools.replay_to_notion --symbol AAPL --session 2025-11-01

- For now it just logs parameters into .logs and exits cleanly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay to Notion journaling stub")
    parser.add_argument("--symbol", required=True, help="Symbol, e.g. AAPL")
    parser.add_argument("--session", required=True, help="Session date, e.g. 2025-11-01")
    parser.add_argument("--summary-json", help="Optional path to replay summary JSON")
    return parser.parse_args(argv)


def _load_summary(path: str | None) -> dict:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        # Keep this message ASCII-only to avoid encoding issues on Windows consoles.
        print("[replay_to_notion] WARN: failed to load summary JSON.", file=sys.stderr)
        return {}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = _load_summary(args.summary_json)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    logs_dir = os.path.join(root, ".logs")
    os.makedirs(logs_dir, exist_ok=True)

    # NOTE: datetime.utcnow() is fine for a stub;
    # when you wire this fully, consider timezone-aware timestamps.
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_name = "replay_to_notion_{sym}_{sess}_{ts}.log".format(
        sym=args.symbol, sess=args.session.replace("-", ""), ts=ts
    )
    log_path = os.path.join(logs_dir, log_name)

    payload = {
        "ts_utc": ts,
        "symbol": args.symbol,
        "session": args.session,
        "summary": summary,
        "note": "stub only - wire real Notion API in a later phase",
    }

    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # ASCII-only console message to avoid Windows "charmap" issues with non-ASCII paths.
        print("[replay_to_notion] stub log written.")
    except Exception as exc:  # noqa: BLE001
        # Keep error message ASCII-only as well.
        print("[replay_to_notion] ERROR: failed to write log.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
