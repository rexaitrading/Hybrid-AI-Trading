#!/usr/bin/env python
"""
tools/news_pretty.py

Pretty-print top Google News headlines from .intel/news_feed.jsonl
for Hybrid AI Trading.
"""

import json
from pathlib import Path
from datetime import datetime


NEWS_PATH = Path(".intel/news_feed.jsonl")


def parse_line(line: str):
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except Exception:
        return None


def parse_pubdate(text: str):
    # We won't do full timezone parsing; we just use the raw string as tiebreaker.
    # If needed later we can use email.utils.parsedate_to_datetime.
    return text or ""


def main(top_n: int = 30):
    if not NEWS_PATH.exists():
        print("No news file found at", NEWS_PATH)
        return

    rows = []
    with NEWS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            r = parse_line(line)
            if not r:
                continue
            rows.append(r)

    if not rows:
        print("No usable news rows in", NEWS_PATH)
        return

    # Sort by score desc, then published_at desc, then title
    rows.sort(
        key=lambda r: (
            r.get("score", 0),
            parse_pubdate(r.get("published_at", "")),
            r.get("title", ""),
        ),
        reverse=True,
    )

    if top_n < 1:
        top_n = 1
    if top_n > len(rows):
        top_n = len(rows)

    print(f"Top {top_n} news headlines:")
    print()

    for i, r in enumerate(rows[:top_n], 1):
        title = r.get("title", "")
        link = r.get("link", "")
        query = r.get("query", "")
        src = r.get("source", "")
        pub = r.get("published_at", "")
        score = r.get("score", 0)

        print(f"{i:2d}. [{score}] {title}")
        print(f"    {link}")
        print(f"    source={src}, query={query}, published={pub}")
        print()


if __name__ == "__main__":
    main()