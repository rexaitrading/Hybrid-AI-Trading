import os
import json
from datetime import datetime, timezone

import requests


# --- Notion Trading Journal property names (from schema dump) ---
PROP_NAME_SYMBOLS  = "symbol"   # exact Notion property name
PROP_NAME_APPROVED = "RiskOK"   # exact Notion property name
def main():
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_TRADE_ID")  # still useful for reference
    ds_id = (
        os.environ.get("NOTION_TRADE_DATA_SOURCE_ID")
        or os.environ.get("NOTION_TRADE_DS")
    )

    if not token:
        raise SystemExit("NOTION_TOKEN is not set in environment.")
    if not ds_id:
        raise SystemExit(
            "NOTION_TRADE_DATA_SOURCE_ID / NOTION_TRADE_DS is not set in environment "
            "(child data_source_id required for multi-data-source DB)."
        )

    notion_version = os.environ.get("NOTION_VERSION", "2025-09-03")

    ts = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "ts": ts,
        "symbol_universe": ["AAPL", "MSFT"],
        "px": 100.0,
        "usdcad": 1.35,
        "orb": {
            "orb_high": 101.0,
            "orb_low": 99.0,
            "breakout": "none",
            "confidence": 0.3,
            "reason": "smoke_test",
        },
        "vwap": {
            "vwap": 100.0,
            "distance": 0.0,
            "slope": 0.0,
            "regime": "neutral",
            "confidence": 0.3,
        },
        "kelly_f": 0.05,
        "sentiment_score": 0.0,
        "regime_conf": 0.5,
        PROP_NAME_APPROVED: False,
        "confidence": 0.23,
        "reason": "weak_edge_smoke_test",
    }

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    }

    # IMPORTANT: property names must match your Trading Journal DB properties
    body = {
        "parent": {"data_source_id": ds_id},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"PHASE-7 Hybrid Smoke {snapshot['ts']}"
                        }
                    }
                ]
            },
            "ts_trade": {
                "date": {"start": snapshot["ts"]}
            },
                    PROP_NAME_SYMBOLS: {
            "rich_text": [
                {
                    "text": {
                        "content": ", ".join(
                            snapshot.get("symbols", snapshot.get("Symbols", []))
                        )
                    }
                }
            ],
        },
            "confidence": {
                "number": snapshot["confidence"]
            },
            "reason": {
                "rich_text": [
                    {"text": {"content": snapshot["reason"][:100]}}
                ]
            },
        },
    }

    print("HEADERS:", headers)
    print("PARENT:", body["parent"])

    resp = requests.post(url, headers=headers, json=body)
    print("STATUS:", resp.status_code)
    try:
        data = resp.json()
    except Exception:
        print("RAW:", resp.text[:400])
        return

    print(json.dumps(data, indent=2)[:1200])


if __name__ == "__main__":
    main()