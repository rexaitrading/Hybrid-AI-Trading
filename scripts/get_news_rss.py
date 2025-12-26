from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "HAT-Intel/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_rss(xml_bytes: bytes) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    items: List[Dict[str, Any]] = []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        desc = _strip_html(it.findtext("description") or "")
        items.append({"title": title, "link": link, "pubDate": pub, "summary": desc})
    return items


def main() -> int:
    ap = argparse.ArgumentParser("RSS News -> JSONL")
    ap.add_argument("--out", required=True, help="Output JSONL path")
    ap.add_argument("--lookbackMin", type=int, default=60)
    ap.add_argument("--maxItems", type=int, default=50)
    ap.add_argument("--tag", default="rss")
    ap.add_argument(
        "--feeds",
        default="https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA,SPY,QQQ&region=US&lang=en-US",
        help="Comma-separated RSS URLs",
    )
    args = ap.parse_args()

    now = _now_utc()

    feeds = [u.strip() for u in (args.feeds or "").split(",") if u.strip()]
    if not feeds:
        print("No feeds provided.", file=sys.stderr)
        return 2

    written = 0
    with open(args.out, "a", encoding="utf-8") as f:
        for url in feeds:
            try:
                data = _fetch(url)
                items = _parse_rss(data)
            except Exception as e:
                err = {
                    "ts_utc": now.isoformat(),
                    "kind": "news_rss_error",
                    "tag": args.tag,
                    "feed": url,
                    "error": str(e),
                }
                f.write(json.dumps(err, ensure_ascii=False) + "\n")
                continue

            for it in items[: args.maxItems]:
                rec = {
                    "ts_utc": now.isoformat(),
                    "kind": "news_rss_item",
                    "tag": args.tag,
                    "feed": url,
                    "title": it.get("title", ""),
                    "link": it.get("link", ""),
                    "pubDate_raw": it.get("pubDate", ""),
                    "summary": it.get("summary", ""),
                    "lookback_min": args.lookbackMin,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1

    print(f"WROTE={written} out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())