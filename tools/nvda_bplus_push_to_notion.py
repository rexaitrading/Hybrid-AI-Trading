"""
Push NVDA B+ replay trades from JSONL into Notion Trading Journal.

Uses:
  - NOTION_TOKEN
  - NOTION_TRADING_JOURNAL_DATA_SOURCE_ID
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
import requests

# HAT path patch: add repo/src to sys.path so hybrid_ai_trading imports work
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from hybrid_ai_trading.replay.nvda_bplus_gate_score import compute_ev_from_trade, compute_gate_score_v2



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
                print("[NOTION] [WARN] Skipping invalid JSON line")
                continue
            trades.append(obj)
            if 0 < limit <= len(trades):
                break
    return trades


def enrich_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    """Attach gate_score_v2 and ev to a trade dict copy."""
    t = dict(trade)
    t["_gate_score_v2"] = compute_gate_score_v2(trade)
    t["_ev"] = compute_ev_from_trade(trade)
    return t


def build_notion_properties(trade: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Notion properties for a Trading Journal-style row.

    We keep names simple so they either match or are auto-created (where allowed):
      - Name (title)
      - symbol (rich_text)
      - ts_trade (date)
      - side (select)
      - gross_pnl_pct (number)
      - r_multiple (number)
      - gate_score_v2 (number)
      - ev (number)
      - session (select, optional)
      - regime (select, optional)
      - kelly_f (number, optional)
      - bar_replay_tag (select, optional)
      - screenshot_note (rich_text, optional; human-readable path)
      - source (select: NVDA_BPLUS_REPLAY)
    """
    symbol = trade.get("symbol", "NVDA")
    entry_ts = trade.get("entry_ts") or trade.get("ts_entry") or trade.get("ts_trade")
    side = trade.get("side", "NA")

    pnl_pct = _safe_float(trade.get("gross_pnl_pct", 0.0))
    r_mult = _safe_float(trade.get("r_multiple", 0.0))
    score = _safe_float(trade.get("_gate_score_v2", 0.0))
    ev = _safe_float(trade.get("_ev", 0.0))

    session = trade.get("session")
    regime = trade.get("regime")
    kelly_f = _safe_float(trade.get("kelly_f", 0.0))
    bar_tag = trade.get("bar_replay_tag") or trade.get("replay_id")
    screenshot = trade.get("screenshot_path")  # path from enrich script

    title_content = f"{symbol} NVDA B+ replay {entry_ts or ''}".strip()

    props: Dict[str, Any] = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": title_content or "NVDA B+ replay trade",
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
        # side is SELECT in your Trading Journal schema
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
        "gate_score_v2": {
            "number": score,
        },
        "ev": {
            "number": ev,
        },
        "source": {
            "select": {
                "name": "NVDA_BPLUS_REPLAY",
            }
        },
    }

    # Optional timestamp -> ts_trade (date)
    if entry_ts:
        props["ts_trade"] = {
            "date": {
                "start": str(entry_ts),
            }
        }

    # Optional session / regime (select)
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

    # Optional kelly_f (number)
    if kelly_f != 0.0:
        props["kelly_f"] = {
            "number": kelly_f,
        }

    # Optional bar_replay_tag (SELECT)
    if bar_tag:
        props["bar_replay_tag"] = {
            "select": {
                "name": str(bar_tag),
            }
        }

    # Optional screenshot_note (TEXT) with the local charts path
    if screenshot:
        props["screenshot_note"] = {
            "rich_text": [
                {
                    "text": {
                        "content": str(screenshot),
                    }
                }
            ]
        }

    # NOTE: gate_rank / pnl_rank / gate_bucket are intentionally omitted for now
    # because the underlying Notion DB (data_source-based) rejects unknown props.

    return props


def post_to_notion(
    token: str,
    data_source_id: str,
    properties: Dict[str, Any],
    dry_run: bool = False,
) -> Optional[str]:
    """Create a Notion page. Returns page id on success, None otherwise."""
    body: Dict[str, Any] = {
        "parent": {
            "type": "data_source_id",
            "data_source_id": data_source_id,
        },
        "properties": properties,
    }

    if dry_run:
        print("[NOTION] [DRY-RUN] Would create page with properties:")
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
        print(f"[NOTION] [ERROR] Status {resp.status_code}: {resp.text}")
        return None

    data = resp.json()
    page_id = data.get("id")
    print(f"[NOTION] Created page: {page_id}")
    return page_id


def run(
    jsonl_path: Path,
    limit: int,
    max_pages: int,
    dry_run: bool,
) -> None:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("[NOTION] NOTION_TOKEN is not set.")
        return

    data_source_id = os.environ.get("NOTION_TRADING_JOURNAL_DATA_SOURCE_ID")
    if not data_source_id:
        print("[NOTION] NOTION_TRADING_JOURNAL_DATA_SOURCE_ID is not set.")
        return

    if not jsonl_path.exists():
        print(f"[NOTION] JSONL not found: {jsonl_path}")
        return

    trades = load_trades(jsonl_path, limit=limit)
    print(f"[NOTION] Loaded {len(trades)} trades from {jsonl_path}")
    if not trades:
        return

    count = 0
    for trade in trades:
        if max_pages > 0 and count >= max_pages:
            print(f"[NOTION] Reached max_pages={max_pages}, stopping.")
            break

        enriched = enrich_trade(trade)
        props = build_notion_properties(enriched)
        _ = post_to_notion(
            token=token,
            data_source_id=data_source_id,
            properties=props,
            dry_run=dry_run,
        )
        count += 1

    print(f"[NOTION] Done. Processed {count} trades (dry_run={dry_run}).")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Push NVDA B+ replay trades from JSONL into Notion."
    )
    ap.add_argument(
        "--jsonl",
        required=True,
        help="Path to NVDA B+ replay trades JSONL.",
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