from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# --------- env-configurable prop names ---------
def _get_title_prop() -> str:
    return os.getenv("NOTION_TITLE_PROP", "Name")


def _get_ts_prop() -> Optional[str]:
    # leave blank '' to skip writing a date; your DB uses created_time for ts
    v = os.getenv("NOTION_TS_PROP", "")
    return v if v else None


def _get_bid_prop() -> str:
    # your DB shows "Bid" (capital B)
    return os.getenv("NOTION_BID_PROP", "Bid")


def _get_ask_prop() -> str:
    return os.getenv("NOTION_ASK_PROP", "ask")


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
        out["sentiment_val"] = sen if isinstance(sen, (int, float, str)) else None
        out["sent_conf"] = out.get("sent_conf")

    ks = out.get("kelly_size") or {}
    if out.get("kelly_f") is None:
        out["kelly_f"] = ks.get("f")
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


def _sentiment_to_select_name(v: Any) -> Optional[str]:
    # If text, pass through; if number, bucketize; else None
    if isinstance(v, str):
        return v
    try:
        f = float(v)
        if f > 0.15:
            return "positive"
        if f < -0.15:
            return "negative"
        return "neutral"
    except Exception:
        return None


# --------- DB schema helpers (for safety) ---------
def _fetch_db_schema(token: str, db_id: str) -> dict:
    try:
        import requests  # type: ignore

        hdr = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
        r = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=hdr, timeout=10)
        if getattr(r, "ok", False):
            return r.json().get("properties", {}) or {}
    except Exception:
        pass
    return {}


def _coerce_prop_value(name: str, value: dict, target_type: str) -> dict | None:
    if target_type == "title":
        return value if "title" in value else None
    if target_type == "rich_text":
        if "rich_text" in value:
            return value
        if "select" in value:
            nm = (value["select"] or {}).get("name")
            return {"rich_text": [{"text": {"content": str(nm or "")}}]}
        if "number" in value:
            return {"rich_text": [{"text": {"content": str(value.get("number"))}}]}
        return None
    if target_type == "select":
        if "select" in value:
            return value
        if "rich_text" in value:
            txt = "".join([t.get("text", {}).get("content", "") for t in value["rich_text"]])
            return {"select": {"name": txt}} if txt else None
        if "number" in value:
            return {"select": {"name": str(value.get("number"))}}
        return None
    if target_type == "multi_select":
        if "multi_select" in value:
            return value
        if "rich_text" in value:
            txt = "".join([t.get("text", {}).get("content", "") for t in value["rich_text"]])
            return {"multi_select": [{"name": txt}]} if txt else {"multi_select": []}
        return {"multi_select": []}
    if target_type == "number":
        if "number" in value:
            return value
        if "select" in value:
            nm = (value["select"] or {}).get("name")
            try:
                return {"number": float(nm)}
            except Exception:
                return None
        if "rich_text" in value:
            txt = "".join([t.get("text", {}).get("content", "") for t in value["rich_text"]])
            try:
                return {"number": float(txt)}
            except Exception:
                return None
        return None
    if target_type == "date":
        if "date" in value:
            return value
        return None
    key = target_type
    return value if key in value else None


def _filter_to_db_schema(mapped_props: dict, db_props: dict) -> dict:
    out = {}
    for name, val in (mapped_props or {}).items():
        sch = db_props.get(name)
        if not sch:
            continue
        target_type = sch.get("type")
        coerced = _coerce_prop_value(name, val, target_type)
        if coerced is not None:
            out[name] = coerced
    return out


# --------- Notion mapping ---------
def _map_item_to_properties(item: Dict[str, Any]) -> Dict[str, Any]:
    sym = item.get("symbol", "")
    d = _flatten(item.get("decision", {}) or {})
    title_prop = _get_title_prop()
    ts_prop = _get_ts_prop()
    bid_prop = _get_bid_prop()
    ask_prop = _get_ask_prop()

    reg_name = d.get("regime_name") or d.get("regime")
    sen_name = _sentiment_to_select_name(d.get("sentiment_val"))

    props: Dict[str, Any] = {
        title_prop: {"title": [{"text": {"content": str(sym or d.get("setup") or "trade")}}]},
        "setup_tag": {"multi_select": ([{"name": str(d.get("setup"))}] if d.get("setup") else [])},
        "side": {"select": ({"name": str(d.get("side"))} if d.get("side") else None)},
        "entry_px": {"number": d.get("entry_px")},
        "stop_px": {"number": d.get("stop_px")},
        "target_px": {"number": d.get("target_px")},
        "qty": {"number": d.get("qty")},
        "kelly_f": {"number": d.get("kelly_f")},
        # your DB expects select for regime & sentiment
        "regime": {"select": ({"name": str(reg_name)} if reg_name else None)},
        "regime_conf": {"number": d.get("regime_conf")},
        "sentiment": {"select": ({"name": str(sen_name)} if sen_name else None)},
        "sent_conf": {"number": d.get("sent_conf")},
        "reason_code": {"rich_text": [{"text": {"content": str(d.get("reason_code") or "")}}]},
        "price": {"number": d.get("price")},
        bid_prop: {"number": d.get("bid")},
        ask_prop: {"number": d.get("ask")},
        "status": {"select": {"name": _status_of(d)}},
    }
    if ts_prop:
        props[ts_prop] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}

    return props


# --------- Public entry (schema-aware, with HTTP error logging) ---------
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

    db_props = _fetch_db_schema(notion_token, db_id) if (db_id and notion_token) else {}

    for body in mapped:
        try:
            if db_props:
                body["properties"] = _filter_to_db_schema(body.get("properties", {}), db_props)
            r = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            if not getattr(r, "ok", False):
                try:
                    os.makedirs("logs", exist_ok=True)
                    with open("logs/notion_http_errors.jsonl", "a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                {
                                    "status": getattr(r, "status_code", None),
                                    "text": getattr(r, "text", None),
                                    "body": body,
                                },
                                ensure_ascii=False,
                            )
                            + "\\n"
                        )
                except Exception:
                    pass
                _dry_write([body])
        except Exception:
            _dry_write([body])


def _dry_write(payload: List[Dict[str, Any]], path: str = "logs/notion_last_payload.json") -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"items": payload}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
