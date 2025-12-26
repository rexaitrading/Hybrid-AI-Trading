from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def tail_jsonl(path: Path, n: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: List[Dict[str, Any]] = []
    for ln in lines[-max(1, n):]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def load_watermark(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_watermark(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def key_for_item(it: Dict[str, Any]) -> str:
    k = it.get("kind", "")
    if k == "news_rss_item":
        return "news:" + (it.get("link") or it.get("title") or "")
    if k == "youtube_video":
        return "yt:" + (it.get("videoId") or it.get("url") or it.get("title") or "")
    return "x:" + (it.get("link") or it.get("url") or it.get("title") or "")


def filter_new(items: List[Dict[str, Any]], seen: set[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        kk = key_for_item(it)
        if not kk or kk in seen:
            continue
        out.append(it)
    return out


def build_prompt(news: List[Dict[str, Any]], yt: List[Dict[str, Any]]) -> str:
    def fmt_news(x: Dict[str, Any]) -> str:
        return (
            f"- {x.get('title','')}\n"
            f"  link: {x.get('link','')}\n"
            f"  pub: {x.get('pubDate_raw','')}\n"
            f"  summary: {(x.get('summary','') or '')[:240]}"
        )

    def fmt_yt(x: Dict[str, Any]) -> str:
        return (
            f"- {x.get('title','')}\n"
            f"  channel: {x.get('channelTitle','')}\n"
            f"  url: {x.get('url','')}\n"
            f"  publishedAt: {x.get('publishedAt','')}"
        )

    news_block = "\n".join(fmt_news(x) for x in news) if news else "(none)"
    yt_block = "\n".join(fmt_yt(x) for x in yt) if yt else "(none)"

    return f"""Return STRICT JSON only (no markdown). Schema:
{{
  "ts_utc": "<iso8601>",
  "as_of_date": "YYYY-MM-DD",
  "items": [
    {{
      "source": "rss" | "youtube",
      "id": "<link/url/videoId>",
      "tickers": ["NVDA","SPY","QQQ"],
      "topic": "earnings|macro|rates|ai|chips|geopolitics|company|technical|other",
      "sentiment": -2|-1|0|1|2,
      "urgency": 0|1|2,
      "risk_flags": ["gap_risk","halts","fed","china_export","earnings_imminent","vol_spike","other"],
      "one_line": "<max 160 chars>",
      "action_hint": "ignore|watch|tighten_risk|avoid_live|review_manually"
    }}
  ]
}}

Rules:
- Conservative: if unsure, sentiment=0 urgency=0 action_hint=review_manually
- Keep <= 25 items total
- Do NOT output trading instructions beyond action_hint

RSS:
{news_block}

YOUTUBE:
{yt_block}
"""


def call_openai(prompt: str, model: str) -> Dict[str, Any]:
    client = OpenAI()  # uses OPENAI_API_KEY from env
    resp = client.responses.create(model=model, input=prompt)
    return json.loads(resp.output_text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intelDir", default="src/.intel")
    ap.add_argument("--news", default="news_feed.jsonl")
    ap.add_argument("--youtube", default="youtube_feed.jsonl")
    ap.add_argument("--out", default="llm_features.jsonl")
    ap.add_argument("--watermark", default="llm_watermark.json")
    ap.add_argument("--tail", type=int, default=60)
    ap.add_argument("--model", default="gpt-4.1-mini")
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("Missing OPENAI_API_KEY", flush=True)
        return 2

    intel = Path(args.intelDir)
    news_path = intel / args.news
    yt_path = intel / args.youtube
    out_path = intel / args.out
    wm_path = intel / args.watermark

    wm = load_watermark(wm_path)
    seen = set(wm.get("seen", []))

    news_items = tail_jsonl(news_path, args.tail)
    yt_items = tail_jsonl(yt_path, args.tail)

    news_new = filter_new(news_items, seen)
    yt_new = filter_new(yt_items, seen)

    if not news_new and not yt_new:
        print("NO_NEW_ITEMS=1", flush=True)
        return 0

    prompt = build_prompt(news_new[:40], yt_new[:40])
    obj = call_openai(prompt, args.model)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("", encoding="utf-8") if not out_path.exists() else None
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    for it in news_new + yt_new:
        seen.add(key_for_item(it))
    save_watermark(wm_path, {"seen": list(seen)[-5000:], "ts_utc": now_utc()})

    print(f"WROTE=1 out={out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())