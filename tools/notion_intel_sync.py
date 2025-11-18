#!/usr/bin/env python
"""
tools/notion_intel_sync.py

Take top 3 YouTube scalper videos + top N macro/news headlines
from the local intel feeds and push them into Notion as two pages.

Uses:
  - NOTION_TOKEN
  - NOTION_INTEL_DATASOURCE  (data_source_id for Trading Journal multi-source DB)
Requires:
  - requests (pip install requests)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import requests


NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
INTEL_DS = os.environ.get("NOTION_INTEL_DATASOURCE")

if not NOTION_TOKEN:
    print("WARN: NOTION_TOKEN is not set; skipping Notion sync.", file=sys.stderr)
    sys.exit(0)

if not INTEL_DS:
    print("WARN: NOTION_INTEL_DATASOURCE is not set; skipping Notion sync.", file=sys.stderr)
    sys.exit(0)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def load_yt_top3(path: Path):
    if not path.exists():
        print(f"WARN: {path} not found; no YouTube intel to sync.", file=sys.stderr)
        return []

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue

    if not rows:
        print(f"WARN: No rows in {path}; no YouTube intel to sync.", file=sys.stderr)
        return []

    rows.sort(
        key=lambda r: (
            r.get("score", 0),
            r.get("published_at", ""),
        ),
        reverse=True,
    )

    return rows[:3]


def load_news_topN(path: Path, top_n: int = 30):
    if not path.exists():
        print(f"WARN: {path} not found; no news intel to sync.", file=sys.stderr)
        return []

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue

    if not rows:
        print(f"WARN: No rows in {path}; no news intel to sync.", file=sys.stderr)
        return []

    rows.sort(
        key=lambda r: (
            r.get("score", 0),
            r.get("published_at", ""),
        ),
        reverse=True,
    )

    if top_n < 1:
        top_n = 1
    if top_n > len(rows):
        top_n = len(rows)

    return rows[:top_n]


def build_children_for_scalper(items):
    children = []
    for r in items:
        line = f"{r.get('title','')}  {r.get('channel_title','')}  {r.get('published_at','')}  {r.get('url','')} (score={r.get('score',0)})"
        children.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": line},
                        }
                    ]
                },
            }
        )
    return children


def build_children_for_macro(items):
    children = []
    for r in items:
        line = f"{r.get('title','')}  {r.get('published_at','')}  {r.get('link','')} (score={r.get('score',0)})"
        children.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": line},
                        }
                    ]
                },
            }
        )
    return children


def create_notion_page(title: str, items, macro: bool):
    children = build_children_for_macro(items) if macro else build_children_for_scalper(items)

    # Only set Name (title) property to avoid validation errors on missing fields
    props = {
        "Name": {
            "title": [
                {"type": "text", "text": {"content": title}}
            ]
        }
    }

    data = {
        "parent": {
            "type": "data_source_id",
            "data_source_id": INTEL_DS,
        },
        "properties": props,
        "children": children,
    }

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json=data,
        timeout=20,
    )
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR: Failed to create Notion page '{title}': {e} / {resp.text}", file=sys.stderr)
        return None

    page = resp.json()
    page_id = page.get("id")
    print(f"Created Notion page '{title}' ({page_id})")
    return page_id


def main():
    root = Path(".")
    yt_path = root / ".intel" / "yt_scalper_feed.jsonl"
    news_path = root / ".intel" / "news_feed.jsonl"

    today = datetime.now().strftime("%Y-%m-%d")

    yt_items = load_yt_top3(yt_path)
    news_items = load_news_topN(news_path, top_n=30)

    if yt_items:
        create_notion_page(
            title=f"Scalper Intel {today}",
            items=yt_items,
            macro=False,
        )
    else:
        print("INFO: No YouTube scalper intel to sync.", file=sys.stderr)

    if news_items:
        create_notion_page(
            title=f"Macro Intel {today}",
            items=news_items,
            macro=True,
        )
    else:
        print("INFO: No macro/news intel to sync.", file=sys.stderr)


if __name__ == "__main__":
    main()