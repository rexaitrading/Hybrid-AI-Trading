from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import requests


# Property names based on Trading Journal schema
PROP_NAME_SYMBOL = "symbol"      # rich_text
PROP_NAME_NAME = "Name"          # title
PROP_NAME_TRADE_TS = "ts_trade"  # date


@dataclass
class HybridSnapshot:
    name: str
    ts_trade: datetime
    symbols: List[str]
    confidence: Optional[float] = None
    reason: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class NotionHybridWriter:
    def __init__(self) -> None:
        token = os.environ.get("NOTION_TOKEN")
        version = os.environ.get("NOTION_VERSION", "2025-09-03")
        data_source_id = os.environ.get("NOTION_TRADE_DATA_SOURCE_ID")

        if not token:
            raise RuntimeError("NOTION_TOKEN is not set.")
        if not data_source_id:
            raise RuntimeError("NOTION_TRADE_DATA_SOURCE_ID is not set.")

        self._token = token
        self._version = version
        self._data_source_id = data_source_id
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": version,
                "Content-Type": "application/json",
            }
        )

    def _build_properties(self, snapshot: HybridSnapshot) -> Dict[str, Any]:
        name_text = snapshot.name or "Hybrid Snapshot"
        ts = snapshot.ts_trade.astimezone(timezone.utc).isoformat()

        props: Dict[str, Any] = {
            PROP_NAME_NAME: {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": name_text},
                    }
                ]
            },
            PROP_NAME_TRADE_TS: {
                "date": {
                    "start": ts,
                }
            },
            PROP_NAME_SYMBOL: {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": ", ".join(snapshot.symbols),
                        },
                    }
                ]
            },
        }

        if snapshot.confidence is not None:
            props["confidence"] = {
                "number": float(snapshot.confidence),
            }

        if snapshot.reason:
            props["reason"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": snapshot.reason},
                    }
                ]
            }

        # TODO: map snapshot.extra into other properties if needed

        return props

    def write_snapshot(self, snapshot: HybridSnapshot) -> Dict[str, Any]:
        body = {
            "parent": {
                "data_source_id": self._data_source_id,
            },
            "properties": self._build_properties(snapshot),
        }
        url = "https://api.notion.com/v1/pages"
        resp = self._session.post(url, data=json.dumps(body))
        resp.raise_for_status()
        return resp.json()