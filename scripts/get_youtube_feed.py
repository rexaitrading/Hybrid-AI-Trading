from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def fetch_json(url: str, timeout: int = 20) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "HAT-Intel/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def main() -> int:
    ap = argparse.ArgumentParser("YouTube Data API search -> JSONL")
    ap.add_argument("--out", required=True, help="Output JSONL path")
    ap.add_argument("--query", default="NVDA ORB,SPY ORB,QQQ ORB,scalping,order flow,tape reading,market microstructure")
    ap.add_argument("--maxPerQuery", type=int, default=5)
    ap.add_argument("--lookbackHours", type=int, default=48)
    ap.add_argument("--region", default="US")
    ap.add_argument("--lang", default="en")
    args = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        print("Missing env YOUTUBE_API_KEY", file=sys.stderr)
        return 2

    now = now_utc()
    published_after = (now - dt.timedelta(hours=max(1, args.lookbackHours))).isoformat().replace("+00:00", "Z")

    queries = [q.strip() for q in (args.query or "").split(",") if q.strip()]
    if not queries:
        print("No queries provided", file=sys.stderr)
        return 2

    # Load existing IDs for dedupe
    seen: set[str] = set()
    try:
        with open(args.out, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    vid = obj.get("videoId")
                    if vid:
                        seen.add(str(vid))
                except Exception:
                    continue
    except FileNotFoundError:
        pass

    written = 0
    with open(args.out, "a", encoding="utf-8") as f:
        for q in queries:
            params = {
                "part": "snippet",
                "type": "video",
                "order": "date",
                "maxResults": str(max(1, min(50, args.maxPerQuery))),
                "q": q,
                "publishedAfter": published_after,
                "regionCode": args.region,
                "relevanceLanguage": args.lang,
                "key": key,
            }
            url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
            try:
                data = fetch_json(url)
            except Exception as e:
                err = {
                    "ts_utc": now.isoformat(),
                    "kind": "youtube_error",
                    "query": q,
                    "error": str(e),
                }
                f.write(json.dumps(err, ensure_ascii=False) + "\n")
                continue

            for it in data.get("items", []):
                vid = (it.get("id", {}) or {}).get("videoId")
                sn = it.get("snippet", {}) or {}
                if not vid or vid in seen:
                    continue
                seen.add(vid)

                rec = {
                    "ts_utc": now.isoformat(),
                    "kind": "youtube_video",
                    "query": q,
                    "videoId": vid,
                    "title": sn.get("title", ""),
                    "channelTitle": sn.get("channelTitle", ""),
                    "publishedAt": sn.get("publishedAt", ""),
                    "url": "https://www.youtube.com/watch?v=" + vid,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1

    print(f"WROTE={written} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())