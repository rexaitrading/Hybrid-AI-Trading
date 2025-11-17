import argparse
import json
import os
import time
from typing import List, Dict, Any

import requests

from tools.notion_nvda_bplus_helpers import build_nvda_bplus_properties


NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2025-09-03"


def load_trades(jsonl_path: str, limit: int) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                trades.append(obj)
                if 0 < limit <= len(trades):
                    break
            except json.JSONDecodeError:
                print("[WARN] Skipping invalid JSON line")
    return trades


def build_parent() -> Dict[str, Any]:
    ds_id = os.environ.get("NOTION_TRADE_DATA_SOURCE_ID", "").strip()
    db_id = os.environ.get("NOTION_TRADE_ID", "").strip()

    if ds_id:
        print("[NOTION] Using parent.data_source_id =", ds_id)
        return {"type": "data_source_id", "data_source_id": ds_id}
    if db_id:
        print("[NOTION] Using parent.database_id =", db_id)
        return {"type": "database_id", "database_id": db_id}

    raise SystemExit(
        "Set NOTION_TRADE_DATA_SOURCE_ID (preferred) or NOTION_TRADE_ID in environment."
    )


def build_properties(trade: Dict[str, Any]) -> Dict[str, Any]:
    # Core fields from JSONL
    symbol = str(trade.get("symbol", "NVDA"))
    side = str(trade.get("side", "long")).upper()
    entry_ts = str(trade.get("entry_ts", ""))
    outcome = str(trade.get("outcome", "")).upper()
    gross_pnl_pct = float(trade.get("gross_pnl_pct", 0.0))
    r_multiple = float(trade.get("r_multiple", 0.0))

    # New fields (Kelly / regime / session / bar-replay tag / replay_id)
    # If the JSONL already has these keys, use them; otherwise use sensible defaults.
    kelly_f = float(trade.get("kelly_f", 0.01))  # 1% risk fraction as placeholder
    regime = str(trade.get("regime", "REPLAY_TEST"))
    session = str(trade.get("session", "US_OPEN"))
    bar_replay_tag = str(trade.get("bar_replay_tag", "NVDA_BPLUS_REPLAY_V1"))
    replay_id = str(trade.get("replay_id", "")).strip()
    if not replay_id:
        # Fallback replay_id if not provided in JSONL
        replay_id = f"{symbol}_REPLAY_{entry_ts or 'UNKNOWN'}"

    title_txt = f"REPLAY {symbol} {entry_ts} {outcome}"

    # Base Notion properties (generic trading info)
    props: Dict[str, Any] = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": title_txt,
                    }
                }
            ]
        },
        "ts_trade": {
            "date": {
                # ISO8601 preferred, but Notion will try to parse strings too
                "start": entry_ts or None
            }
        },
        "symbol": {
            "rich_text": [
                {
                    "text": {
                        "content": symbol,
                    }
                }
            ]
        },
        "side": {
            "select": {
                "name": side,
            }
        },
        "gross_pnl_pct": {
            "number": gross_pnl_pct
        },
        "r_multiple": {
            "number": r_multiple
        },
        "outcome": {
            "select": {
                "name": outcome,
            }
        },
    }

    # NVDA B+ / replay-specific GateScore fields via helper.
    # This returns:
    # - source (REPLAY_NVDA_BPLUS)
    # - bar_replay_tag (NVDA_BPLUS_REPLAY_V1 or overridden)
    # - kelly_f, regime, session, mode, replay_id
    nvda_props = build_nvda_bplus_properties(
        kelly_f=kelly_f,
        regime=regime,
        session=session,
        replay_id=replay_id,
        bar_replay_tag=bar_replay_tag,
    )

    # Merge helper-returned fields into the main props dict
    props.update(nvda_props)

    return props


def push_to_notion(trades: List[Dict[str, Any]], dry_run: bool, sleep_sec: float = 0.3) -> None:
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        raise SystemExit("NOTION_TOKEN is not set in environment.")

    parent = build_parent()

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    created = 0
    for idx, t in enumerate(trades, start=1):
        props = build_properties(t)
        payload = {
            "parent": parent,
            "properties": props,
        }

        title = props.get("Name", {}).get("title", [])
        if title and isinstance(title, list):
            name_text = title[0].get("text", {}).get("content", "REPLAY TRADE")
        else:
            name_text = "REPLAY TRADE"

        print(f"[NOTION] Trade {idx}/{len(trades)}: {name_text}")

        if dry_run:
            print("[NOTION] DRY-RUN payload preview (no request sent).")
            # Uncomment if you want to see the full JSON:
            # print(json.dumps(payload, indent=2))
            continue

        resp = requests.post(NOTION_API_URL, headers=headers, data=json.dumps(payload))
        if not resp.ok:
            print("[ERROR] Notion returned status", resp.status_code, resp.text)
            continue

        created += 1
        time.sleep(sleep_sec)

    print(f"[NOTION] Done. Created {created} pages (dry_run={dry_run}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Push replay trades JSONL to Notion Trading Journal.")
    parser.add_argument("--jsonl", required=True, help="Path to replay trades JSONL.")
    parser.add_argument("--limit", type=int, default=50, help="Max trades to push (default 50).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, do not call Notion; just print payload previews.",
    )
    args = parser.parse_args()

    trades = load_trades(args.jsonl, limit=args.limit)
    if not trades:
        print("[NOTION] No trades loaded from", args.jsonl)
        return

    print(f"[NOTION] Loaded {len(trades)} trades from {args.jsonl}")
    push_to_notion(trades, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
