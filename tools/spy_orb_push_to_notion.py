"""
Push SPY ORB replay trades from JSONL into Notion Trading Journal.

Uses:
  - NOTION_TOKEN
  - NOTION_TRADING_JOURNAL_DATA_SOURCE_ID
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_trades(jsonl_path: Path, limit: int) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[SPY_ORB_NOTION] [WARN] Skipping invalid JSON line")
                continue
            trades.append(obj)
            if 0 < limit <= len(trades):
                break
    return trades


def build_notion_properties(trade: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Notion properties for a Trading Journal-style row for SPY ORB.

    Properties:
      - Name (title)
      - symbol (rich_text)
      - ts_trade (date)
      - side (select)
      - gross_pnl_pct (number)
      - r_multiple (number)
      - orb_high (number)
      - orb_low (number)
      - tp_price (number)
      - sl_price (number)
      - session (select)
      - regime (select)
      - source (select: SPY_ORB_REPLAY)
    """
    symbol = trade.get("symbol", "SPY")
    entry_ts = trade.get("entry_ts") or trade.get("ts_trade")
    side = trade.get("side", "NA")

    pnl_pct = _safe_float(trade.get("gross_pnl_pct", 0.0))
    r_mult = _safe_float(trade.get("r_multiple", 0.0))
    orb_high = _safe_float(trade.get("orb_high", 0.0))
    orb_low = _safe_float(trade.get("orb_low", 0.0))
    tp_price = _safe_float(trade.get("tp_price", 0.0))
    sl_price = _safe_float(trade.get("sl_price", 0.0))

    session = trade.get("session", "RTH")
    regime = trade.get("regime", "SPY_ORB_REPLAY")

    title_content = f"{symbol} SPY ORB {entry_ts or ''}".strip()

    props: Dict[str, Any] = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": title_content or "SPY ORB trade",
                    }
                }
            ]
        },
        "symbol": {
            "rich_text": [
                {
                    "text": {
                        "content": str(symbol),
                    }
                }
            ]
        },
        "side": {
            "select": {
                "name": str(side),
            }
        },
        "gross_pnl_pct": {
            "number": pnl_pct,
        },
        "r_multiple": {
            "number": r_mult,
        },
        "orb_high": {
            "number": orb_high,
        },
        "orb_low": {
            "number": orb_low,
        },
        "tp_price": {
            "number": tp_price,
        },
        "sl_price": {
            "number": sl_price,
        },
        "source": {
            "select": {
                "name": "SPY_ORB_REPLAY",
            }
        },
    }

    if entry_ts:
        props["ts_trade"] = {
            "date": {
                "start": str(entry_ts),
            }
        }

    if session:
        props["session"] = {
            "select": {
                "name": str(session),
            }
        }
    if regime:
        props["regime"] = {
            "select": {
                "name": str(regime),
            }
        }

    return props


def post_to_notion(
    token: str,
    data_source_id: str,
    properties: Dict[str, Any],
    dry_run: bool = False,
) -> Optional[str]:
    body: Dict[str, Any] = {
        "parent": {
            "type": "data_source_id",
            "data_source_id": data_source_id,
        },
        "properties": properties,
    }

    if dry_run:
        print("[SPY_ORB_NOTION] [DRY-RUN] Would create page with properties:")
        print(json.dumps(body, indent=2, ensure_ascii=False))
        return None

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code != 200:
        print(f"[SPY_ORB_NOTION] [ERROR] Status {resp.status_code}: {resp.text}")
        return None

    data = resp.json()
    page_id = data.get("id")
    print(f"[SPY_ORB_NOTION] Created page: {page_id}")
    return page_id


def run(
    jsonl_path: Path,
    limit: int,
    max_pages: int,
    dry_run: bool,
) -> None:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("[SPY_ORB_NOTION] NOTION_TOKEN is not set.")
        return

    data_source_id = os.environ.get("NOTION_TRADING_JOURNAL_DATA_SOURCE_ID")
    if not data_source_id:
        print("[SPY_ORB_NOTION] NOTION_TRADING_JOURNAL_DATA_SOURCE_ID is not set.")
        return

    if not jsonl_path.exists():
        print(f"[SPY_ORB_NOTION] JSONL not found: {jsonl_path}")
        return

    trades = load_trades(jsonl_path, limit=limit)
    print(f"[SPY_ORB_NOTION] Loaded {len(trades)} trades from {jsonl_path}")
    if not trades:
        return

    count = 0
    for trade in trades:
        if max_pages > 0 and count >= max_pages:
            print(f"[SPY_ORB_NOTION] Reached max_pages={max_pages}, stopping.")
            break

        props = build_notion_properties(trade)
        _ = post_to_notion(
            token=token,
            data_source_id=data_source_id,
            properties=props,
            dry_run=dry_run,
        )
        count += 1

    print(f"[SPY_ORB_NOTION] Done. Processed {count} trades (dry_run={dry_run}).")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Push SPY ORB replay trades from JSONL into Notion."
    )
    ap.add_argument(
        "--jsonl",
        required=True,
        help="Path to SPY ORB replay trades JSONL.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max trades to load from JSONL (0 = no limit).",
    )
    ap.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Max pages to create in Notion (0 = no limit).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, only print payloads instead of calling Notion.",
    )
    args = ap.parse_args()

    jsonl_path = Path(args.jsonl)
    run(
        jsonl_path=jsonl_path,
        limit=args.limit,
        max_pages=args.max_pages,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    main()