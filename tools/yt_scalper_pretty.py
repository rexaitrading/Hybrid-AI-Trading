#!/usr/bin/env python
"""
Pretty-print today's YouTube scalper intel from .intel/yt_scalper_feed.jsonl
"""

import json
from pathlib import Path

path = Path(".intel/yt_scalper_feed.jsonl")
if not path.exists():
    print("No intel file found at", path)
    raise SystemExit(1)

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

# Sort by score desc, then newest first
rows.sort(key=lambda r: (r.get("score", 0), r.get("published_at", "")), reverse=True)

for i, r in enumerate(rows, 1):
    print(f"{i:2d}. [{r.get('score', 0)}] {r.get('title', '')}")
    print(f"    {r.get('url', '')}")
    print(f"    channel: {r.get('channel_title', '')}, published: {r.get('published_at', '')}")
    print()