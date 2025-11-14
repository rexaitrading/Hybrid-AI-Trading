#!/usr/bin/env python
"""
tools/news_feed.py

Fetch Google News RSS headlines for key trading topics and save to
.intel/news_feed.jsonl for Hybrid AI Trading.

Requires:
  - requests (pip install requests)
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

import requests

# Queries for our day-trade system
QUERIES = [
    "SPY stock",
    "QQQ stock",
    "TSX index",
    "TSX stocks",
    "Bitcoin price",
    "BTCUSD",
    "Fed interest rates",
    "stock market volatility",
]

# Google News RSS search URL template
RSS_TEMPLATE = "https://news.google.com/rss/search?q={query}&hl=en-CA&gl=CA&ceid=CA:en"

OUTPUT_PATH = Path(".intel/news_feed.jsonl")


def fetch_rss(query: str) -> str:
    url = RSS_TEMPLATE.format(query=query.replace(" ", "+"))
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text


def parse_rss(xml_text: str):
    # Very simple RSS parsing: <item><title>, <link>, <pubDate>
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        date_el = item.find("pubDate")

        title = title_el.text if title_el is not None else ""
        link = link_el.text if link_el is not None else ""
        pub = date_el.text if date_el is not None else ""

        items.append(
            {
                "title": title,
                "link": link,
                "published_at": pub,
            }
        )
    return items


def score_headline(title: str) -> int:
    """Simple heuristic score for now."""
    t = title.lower()
    score = 0

    # More points for volatility / breaking style words
    for w in ["volatility", "selloff", "crash", "plunge", "spike", "surge", "earnings"]:
        if w in t:
            score += 2

    # Slight boost for 'fed' or 'rate'
    for w in ["fed", "rate hike", "rates"]:
        if w in t:
            score += 1

    # Slight boost for 'bitcoin', 'btc'
    for w in ["bitcoin", "btc"]:
        if w in t:
            score += 1

    return score


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    seen = set()
    count = 0

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as f:
        for q in QUERIES:
            try:
                xml_text = fetch_rss(q)
                items = parse_rss(xml_text)
            except Exception as e:
                print(f"[WARN] failed for query '{q}': {e}", file=sys.stderr)
                continue

            for it in items:
                title = it.get("title", "").strip()
                link = it.get("link", "").strip()
                pub = it.get("published_at", "").strip()

                if not title or not link:
                    continue

                key = (title, link)
                if key in seen:
                    continue

                seen.add(key)

                s = score_headline(title)

                record = {
                    "source": "google_news",
                    "query": q,
                    "title": title,
                    "link": link,
                    "published_at": pub,
                    "score": s,
                }

                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1

    print(f"Wrote {count} news headlines to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()