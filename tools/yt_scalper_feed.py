#!/usr/bin/env python
"""
tools/yt_scalper_feed.py

Auto-scan YouTube for fresh 'top 1%' style scalper / day-trade content
and save a JSONL feed for Hybrid AI Trading.

Now hardened so that 403 errors from YouTube do NOT wipe the existing intel file.

Requires:
  - env var YOUTUBE_API_KEY
  - requests (pip install requests)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import requests

API_KEY = os.environ.get("YOUTUBE_API_KEY")
if not API_KEY:
    print("ERROR: YOUTUBE_API_KEY env var is not set.", file=sys.stderr)
    sys.exit(1)

SEARCH_TERMS = [
    "order flow scalping futures",
    "scalping ES futures order book",
    "vwap scalping strategy",
    "tsx day trading scalping",
    "pre market levels day trading",
    "risk management day trader",
    "black swan risk hedging trading",
    "leverage risk futures trading",
]

DAYS_BACK = 3

INCLUDE_WORDS = [
    "scalp", "scalping",
    "order flow", "tape", "dom", "order book",
    "vwap",
    "day trade", "day trading",
]
EXCLUDE_WORDS = [
    "lottery", "1000%", "10000%",
    "signal group", "copy trading",
    "no risk", "guaranteed", "get rich",
]

MAX_RESULTS_PER_TERM = 10

OUTPUT_PATH = Path(".intel/yt_scalper_feed.jsonl")


def text_contains_any(text: str, words) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)


def text_contains_none(text: str, words) -> bool:
    t = text.lower()
    return all(w.lower() not in t for w in words)


def build_search_url():
    return "https://www.googleapis.com/youtube/v3/search"


def search_videos(query: str, published_after_iso: str):
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "date",
        "maxResults": MAX_RESULTS_PER_TERM,
        "videoDuration": "medium",
        "relevanceLanguage": "en",
        "publishedAfter": published_after_iso,
        "key": API_KEY,
        "safeSearch": "none",
    }
    resp = requests.get(build_search_url(), params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("items", [])


def main():
    now = datetime.now(timezone.utc)
    published_after = now - timedelta(days=DAYS_BACK)
    published_after_iso = published_after.isoformat().replace("+00:00", "Z")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = OUTPUT_PATH.with_suffix(".tmp.jsonl")

    seen_ids = set()
    count_written = 0
    api_blocked = False

    try:
        f = tmp_path.open("w", encoding="utf-8", newline="\n")
    except Exception as e:
        print(f"ERROR: cannot open temp file {tmp_path}: {e}", file=sys.stderr)
        sys.exit(1)

    with f:
        for term in SEARCH_TERMS:
            try:
                items = search_videos(term, published_after_iso)
            except Exception as e:
                msg = str(e)
                print(f"[WARN] search failed for term '{term}': {e}", file=sys.stderr)
                # If we see 403, assume API temporarily blocked; stop further calls.
                if "403" in msg and "Client Error" in msg:
                    api_blocked = True
                    break
                continue

            for it in items:
                vid_id = it.get("id", {}).get("videoId")
                if not vid_id or vid_id in seen_ids:
                    continue

                snippet = it.get("snippet", {})
                title = snippet.get("title", "")
                desc = snippet.get("description", "")
                channel = snippet.get("channelTitle", "")
                published_at = snippet.get("publishedAt", "")

                full_text = f"{title}\n{desc}"

                if not text_contains_any(full_text, INCLUDE_WORDS):
                    continue
                if not text_contains_none(full_text, EXCLUDE_WORDS):
                    continue

                score = 0
                for w in INCLUDE_WORDS:
                    if w.lower() in full_text.lower():
                        score += 1

                record = {
                    "video_id": vid_id,
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "title": title,
                    "channel_title": channel,
                    "published_at": published_at,
                    "query": term,
                    "score": score,
                }

                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                seen_ids.add(vid_id)
                count_written += 1

    if count_written > 0:
        # Replace the real file with the new temp file
        tmp_path.replace(OUTPUT_PATH)
        print(f"Wrote {count_written} videos to {OUTPUT_PATH}")
    else:
        # No new videos; do NOT wipe the old file
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

        if api_blocked:
            print("No new videos written because YouTube API returned 403 for our queries.")
            print("Keeping existing intel file at", OUTPUT_PATH)
        else:
            print("No new videos found; keeping existing intel file at", OUTPUT_PATH)


if __name__ == "__main__":
    main()