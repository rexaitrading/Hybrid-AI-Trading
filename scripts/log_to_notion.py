from __future__ import annotations

import datetime as dt
import json
import os
import time
from typing import List

import requests

# --- settings ---
TITLE_PROP = "Name"  # change if your DB title property name is different
DETAILS_PROP = "Details"  # if this prop doesn't exist, well create content as page children instead

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB = os.environ.get("NOTION_DB")
LOG_FILE = os.environ.get("HAT_LOG_FILE", r"logs/runner_paper.jsonl")

assert NOTION_TOKEN, "Set NOTION_TOKEN env var"
assert NOTION_DB, "Set NOTION_DB env var"

session = requests.Session()
session.headers.update(
    {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
)


def read_tail_lines(path: str, n: int = 200) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-n:]
    except FileNotFoundError:
        return []


def parse_jsonl(lines: List[str]) -> List[dict]:
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def find_pair(items: List[dict]):
    """
    Return last run_start + once_done pair if present; otherwise last item only.
    """
    last_run_start = None
    last_once_done = None
    for obj in items:
        if obj.get("event") == "run_start":
            last_run_start = obj
        if obj.get("event") == "once_done":
            last_once_done = obj
    if last_once_done:
        return last_run_start, last_once_done
    # fallback: use very last record
    return (items[-1] if items else None), None


def notion_create_page(title: str, details_text: str):
    # Try putting details into a rich_text property named DETAILS_PROP.
    # If it doesn't exist, well attach it as page content (children).
    props = {
        TITLE_PROP: {
            "type": "title",
            "title": [{"type": "text", "text": {"content": title[:200]}}],
        }
    }
    body = {
        "parent": {"database_id": NOTION_DB},
        "properties": props,
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": details_text[:1900]
                            },  # keep it short-ish
                        }
                    ]
                },
            }
        ],
    }

    # First, try to also add rich_text property named DETAILS_PROP (if it exists)
    # Its safe: if Notion rejects because prop not in schema, well retry without it.
    props_with_details = dict(props)
    props_with_details[DETAILS_PROP] = {
        "type": "rich_text",
        "rich_text": [{"type": "text", "text": {"content": details_text[:1900]}}],
    }
    body_try_prop = dict(body)
    body_try_prop["properties"] = props_with_details

    r = session.post(
        "https://api.notion.com/v1/pages", data=json.dumps(body_try_prop).encode()
    )
    if r.status_code == 200:
        return True

    # Retry without DETAILS_PROP (schema likely missing)
    r = session.post("https://api.notion.com/v1/pages", data=json.dumps(body).encode())
    if r.status_code != 200:
        try:
            print("Notion error:", json.dumps(r.json(), indent=2))
        except Exception:
            print("Notion error status:", r.status_code, r.text[:500])
        return False
    return True


def main():
    lines = read_tail_lines(LOG_FILE, n=400)
    objs = parse_jsonl(lines)
    if not objs:
        print(f"No log records found in {LOG_FILE}")
        return 0

    rs, od = find_pair(objs)
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if od:
        # Build a concise one-line title
        items = od.get("data", {}).get("result", {}).get("items", [])
        sym_list = [d.get("symbol") for d in items if isinstance(d, dict)]
        title = (
            f"[once_done] {','.join(sym_list) or 'N/A'}  ({len(items)} items)  @ {ts}"
        )
        details = json.dumps({"run_start": rs, "once_done": od}, ensure_ascii=False)
    else:
        title = f"[log] {rs.get('event') if rs else 'record'}  @ {ts}"
        details = json.dumps(rs or {}, ensure_ascii=False)

    ok = notion_create_page(title, details)
    print("Notion create page:", "OK" if ok else "FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
