from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------- Env-configurable property names ----------
def _get_title_prop() -> str:
    return os.getenv("NOTION_TITLE_PROP", "Name")


def _get_ts_prop() -> Optional[str]:
    # default: skip writing ts; your DB uses Created time (read-only)
    v = os.getenv("NOTION_TS_PROP", "")
    return v or None


def _get_bid_prop() -> str:
    return os.getenv("NOTION_BID_PROP", "Bid")  # your DB: capital B


def _get_ask_prop() -> str:
    return os.getenv("NOTION_ASK_PROP", "ask")  # your DB: lower-case


# ---------- Decision helpers ----------
def _flatten_decision(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(d or {})
    reg = out.get("regime")
    if isinstance(reg, dict):
        out["regime_name"] = reg.get("regime")
        out["regime_conf"] = reg.get("confidence")
    else:
        out["regime_name"] = reg if isinstance(reg, str) else None
        out["regime_conf"] = out.get("regime_conf")
    sen = out.get("sentiment")
    if isinstance(sen, dict):
        out["sentiment_val"] = sen.get("sentiment")
        out["sent_conf"] = sen.get("confidence")
    else:
        out["sentiment_val"] = sen if isinstance(sen, (int, float, str)) else None
        out["sent_conf"] = out.get("sent_conf")
    ks = out.get("kelly_size")
    if isinstance(ks, dict):
        out.setdefault("kelly_f", ks.get("f"))
        out.setdefault("qty", ks.get("qty"))
    ra = out.get("risk_approved") or {}
    out["reason_code"] = ra.get("reason")
    return out


def _status_of(d: Dict[str, Any]) -> str:
    qty = int(d.get("qty") or 0)
    if (
        d.get("side")
        and d.get("entry_px") is not None
        and d.get("stop_px") is not None
        and d.get("target_px") is not None
        and qty > 0
    ):
        return "ready"
    if qty == 0 and d.get("reason_code"):
        return "blocked"
    return "stub"


def _sentiment_to_select_name(v: Any) -> Optional[str]:
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


# ---------- DB schema helpers ----------
def _fetch_db_schema(token: str, db_id: str) -> Dict[str, Any]:
    try:
        import requests  # type: ignore

        hdr = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
        r = requests.get(
            f"https://api.notion.com/v1/databases/{db_id}", headers=hdr, timeout=10
        )
        if getattr(r, "ok", False):
            return r.json().get("properties", {}) or {}
    except Exception:
        pass
    return {}


def _coerce(value: Dict[str, Any], target_type: str) -> Optional[Dict[str, Any]]:
    # value is already like {"number":..} / {"select":{"name":..}} / {"rich_text":[...]}/{"date":{...}}
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
            txt = "".join(
                [t.get("text", {}).get("content", "") for t in value["rich_text"]]
            )
            return {"select": {"name": txt}} if txt else None
        if "number" in value:
            return {"select": {"name": str(value.get("number"))}}
        return None
    if target_type == "multi_select":
        if "multi_select" in value:
            return value
        if "rich_text" in value:
            txt = "".join(
                [t.get("text", {}).get("content", "") for t in value["rich_text"]]
            )
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
            txt = (
                "".join(
                    [t.get("text", {}).get("content", "") for t in value["rich_text"]]
                )
                if isinstance(value["rich_text"], list)
                else ""
            )
            try:
                return {"number": float(txt)}
            except Exception:
                return None
        return None
    if target_type == "date":
        return value if "date" in value else None
    return value if target_type in value else None


def _filter_to_db(props: Dict[str, Any], db_props: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, val in (props or {}).items():
        sch = (db_props or {}).get(name)
        if not sch:
            continue
        coerced = _coerce(val, sch.get("type"))
        if coerced is not None:
            out[name] = coerced
    return out


# ---------- mapping ----------
def _map_item_to_properties(item: Dict[str, Any]) -> Dict[str, Any]:
    d = _flatten_decision(item.get("decision") or {})
    sym = item.get("symbol") or ""
    title_prop = _get_title_prop()
    bid_prop = _get_bid_prop()  # 'Bid'
    ask_prop = _get_ask_prop()  # 'ask'
    ts_prop = _get_ts_prop()

    def _num(v):
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    reg_name = d.get("regime_name") or d.get("regime")
    sen_name = _sentiment_to_select_name(d.get("sentiment_val"))

    props: Dict[str, Dict[str, Any]] = {
        title_prop: {
            "title": [{"text": {"content": str(sym or d.get("setup") or "trade")}}]
        },
        "setup_tag": {
            "multi_select": ([{"name": str(d.get("setup"))}] if d.get("setup") else [])
        },
        "side": {"select": ({"name": str(d.get("side"))} if d.get("side") else None)},
        "entry_px": {"number": _num(d.get("entry_px"))},
        "stop_px": {"number": _num(d.get("stop_px"))},
        "target_px": {"number": _num(d.get("target_px"))},
        "qty": {"number": _num(d.get("qty"))},
        "kelly_f": {"number": _num(d.get("kelly_f"))},
        "regime": {"select": ({"name": str(reg_name)} if reg_name else None)},
        "regime_conf": {"number": _num(d.get("regime_conf"))},
        "sentiment": {"select": ({"name": str(sen_name)} if sen_name else None)},
        "sent_conf": {"number": _num(d.get("sent_conf"))},
        "reason_code": {
            "rich_text": [{"text": {"content": str(d.get("reason_code") or "")}}]
        },
        "price": {"number": _num(d.get("price"))},
        "__BID__": {"number": _num(d.get("bid"))},
        "__ASK__": {"number": _num(d.get("ask"))},
        "status": {
            "select": {
                "name": (
                    "ready"
                    if (
                        d.get("side")
                        and d.get("entry_px") is not None
                        and d.get("stop_px") is not None
                        and d.get("target_px") is not None
                        and int(d.get("qty") or 0) > 0
                    )
                    else (
                        "blocked"
                        if (int(d.get("qty") or 0) == 0 and d.get("reason_code"))
                        else "stub"
                    )
                )
            }
        },
    }
    # optional Date write (we skip by default)
    if ts_prop:
        props[ts_prop] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}

    # swap placeholders to actual DB keys
    props[bid_prop] = props.pop("__BID__")
    props[ask_prop] = props.pop("__ASK__")
    return props


# ---------- Public API ----------
def journal_batch(
    items: List[Dict[str, Any]], db_id: Optional[str], notion_token: Optional[str]
) -> None:
    items = items or []
    if not items:
        return

    include_stubs = os.getenv("NOTION_INCLUDE_STUBS") in (
        "1",
        "true",
        "True",
        "YES",
        "yes",
    )
    mapped: List[Dict[str, Any]] = []
    for it in items:
        props = _map_item_to_properties(it)
        status = (props.get("status") or {}).get("select", {}).get("name")
        if include_stubs or status == "ready":
            mapped.append({"parent": {"database_id": db_id or ""}, "properties": props})

    # Dry-run if no creds
    if not db_id or not notion_token:
        _dry_write(mapped)
        return

    # Filter to DB schema & POST
    try:
        import requests  # type: ignore

        db_props = (
            _fetch_db_schema(notion_token, db_id) if (db_id and notion_token) else {}
        )
        hdr = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        url = "https://api.notion.com/v1/pages"
        for body in mapped:
            if db_props:
                body["properties"] = _filter_to_db(body.get("properties", {}), db_props)
            r = requests.post(url, headers=hdr, data=json.dumps(body), timeout=10)
            if not getattr(r, "ok", False):
                _log_http_error(r, body)
                _dry_write([body])
    except Exception:
        _dry_write(mapped)


def _log_http_error(r, body):
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
                + "\n"
            )
    except Exception:
        pass


def _dry_write(
    payload: List[Dict[str, Any]], path: str = "logs/notion_last_payload.json"
) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"items": payload}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
