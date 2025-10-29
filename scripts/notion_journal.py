from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# --------- helpers for DB schema ---------
def _get_title_prop() -> str:
    # default to Notion's usual title column name
    return os.getenv("NOTION_TITLE_PROP", "Name")


def _get_ts_prop() -> Optional[str]:
    # set NOTION_TS_PROP to your Date property name to write a timestamp; default "ts"
    return os.getenv("NOTION_TS_PROP", "ts")


# --------- decision flattening & status ---------
def _flatten(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(d or {})
    reg = out.get("regime")
    if isinstance(reg, dict):
        out["regime_name"], out["regime_conf"] = reg.get("regime"), reg.get("confidence")
    else:
        out["regime_name"] = reg if isinstance(reg, str) else None
        out["regime_conf"] = out.get("regime_conf")

    sen = out.get("sentiment")
    if isinstance(sen, dict):
        out["sentiment_val"], out["sent_conf"] = sen.get("sentiment"), sen.get("confidence")
    else:
        out["sentiment_val"] = sen if isinstance(sen, (int, float)) else None
        out["sent_conf"] = out.get("sent_conf")

    ks = out.get("kelly_size") or {}
    if out.get("kelly_f") is None:
        out["kelly_f"] = ks.get("f")
    # Only backfill qty when it's missing, not when guardrails set it to 0
    if out.get("qty") is None:
        out["qty"] = ks.get("qty")

    ra = out.get("risk_approved") or {}
    out["reason_code"] = ra.get("reason")
    return out


def _is_trade_ready(d: Dict[str, Any]) -> bool:
    side = d.get("side")
    qty = int(d.get("qty") or 0)
    return (
        bool(side)
        and d.get("entry_px") is not None
        and d.get("stop_px") is not None
        and d.get("target_px") is not None
        and qty > 0
    )


def _status_of(d: Dict[str, Any]) -> str:
    if _is_trade_ready(d):
        return "ready"
    if int(d.get("qty") or 0) == 0 and d.get("reason_code"):
        return "blocked"
    return "stub"


# --------- Notion mapping ---------
def _map_item_to_properties(item: Dict[str, Any]) -> Dict[str, Any]:
    sym = item.get("symbol", "")
    d = _flatten(item.get("decision", {}) or {})
    title_prop = _get_title_prop()
    ts_prop = _get_ts_prop()

    props: Dict[str, Any] = {
        title_prop: {"title": [{"text": {"content": str(sym or d.get("setup") or "trade")}}]},
        "setup_tag": {"multi_select": ([{"name": str(d.get("setup"))}] if d.get("setup") else [])},
        "side": {"select": ({"name": str(d.get("side"))} if d.get("side") else None)},
        "entry_px": {"number": d.get("entry_px")},
        "stop_px": {"number": d.get("stop_px")},
        "target_px": {"number": d.get("target_px")},
        "qty": {"number": d.get("qty")},
        "kelly_f": {"number": d.get("kelly_f")},
        "regime": {"rich_text": [{"text": {"content": str(d.get("regime_name") or "")}}]},
        "regime_conf": {"number": d.get("regime_conf")},
        "sentiment": {"number": d.get("sentiment_val")},
        "sent_conf": {"number": d.get("sent_conf")},
        "reason_code": {"rich_text": [{"text": {"content": str(d.get("reason_code") or "")}}]},
        "price": {"number": d.get("price")},
        "bid": {"number": d.get("bid")},
        "ask": {"number": d.get("ask")},
        "status": {"select": {"name": _status_of(d)}},
    }
    if ts_prop:
        props[ts_prop] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}
    return props


def _dry_write(payload: List[Dict[str, Any]], path: str = "logs/notion_last_payload.json") -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"items": payload}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# --------- Public entry ---------
def journal_batch(
    items: List[Dict[str, Any]], db_id: Optional[str], notion_token: Optional[str]
) -> None:
    items = items or []
    if not items:
        return

    include_stubs = os.getenv("NOTION_INCLUDE_STUBS") == "1"
    mapped = []
    for it in items:
        props = _map_item_to_properties(it)
        status = (props.get("status") or {}).get("select", {}).get("name")
        if include_stubs or status == "ready":
            mapped.append({"parent": {"database_id": db_id or "<missing>"}, "properties": props})

    if not mapped:
        _dry_write([{"note": "nothing to write (no ready items and NOTION_INCLUDE_STUBS!=1)"}])
        return

    if not db_id or not notion_token or os.getenv("NOTION_DRY_RUN") == "1":
        _dry_write(mapped)
        return

    try:
        import requests  # type: ignore
    except Exception:
        _dry_write(mapped)
        return

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    url = "https://api.notion.com/v1/pages"

    for body in mapped:
        try:
            requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        except Exception:
            _dry_write([body])
