from __future__ import annotations

import os
import re
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._writer import normalize_record, load_existing_ids, dedupe_new, filter_fresh, write_jsonl_atomic_append


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _watchlist() -> List[str]:
    s = (os.getenv("HAT_INTEL_WATCHLIST") or "NVDA,SPY,QQQ").strip()
    out = [x.strip().upper() for x in s.split(",") if x.strip()]
    return sorted(set(out))


def _tag_symbols(title: str, watch: List[str]) -> List[str]:
    t = (title or "").upper()
    syms: List[str] = []
    for sym in watch:
        if re.search(rf"(?<![A-Z0-9]){re.escape(sym)}(?![A-Z0-9])", t):
            syms.append(sym)
    return syms


def _read_topic_keywords(repo_root: Path) -> List[str]:
    """
    Source of truth: config/youtube_topic_keywords.txt
    Returns lowercase keywords (substring match on title)
    """
    p = repo_root / "config" / "youtube_topic_keywords.txt"
    out: List[str] = []
    try:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = (line or "").strip()
            if (not s) or s.startswith("#"):
                continue
            out.append(s.lower())
    except FileNotFoundError:
        pass
    return out


def _match_topics(title: str, keywords: List[str]) -> List[str]:
    t = (title or "").lower()
    return [k for k in keywords if k in t]


def _read_channel_ids() -> Tuple[List[str], List[str]]:
    """
    Returns (good_ids, bad_ids)
    Source of truth:
      1) env HAT_YT_CHANNEL_IDS (semicolon-separated)
      2) config/youtube_channels.txt (one channel id per line)
    """
    raw = (os.getenv("HAT_YT_CHANNEL_IDS") or "").strip()

    if not raw:
        cfg = _repo_root() / "config" / "youtube_channels.txt"
        if cfg.exists():
            raw = ";".join(
                [
                    ln.strip()
                    for ln in cfg.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if ln.strip() and (not ln.strip().startswith("#"))
                ]
            )

    if not raw:
        return ([], [])

    good: List[str] = []
    bad: List[str] = []
    pat = re.compile(r"^UC[a-zA-Z0-9_-]{10,}$")

    for cid in [x.strip() for x in raw.split(";") if x.strip()]:
        if ("<" in cid) or (">" in cid) or (not pat.match(cid)):
            bad.append(cid)
        else:
            good.append(cid)

    return (good, bad)


def _yt_feed_urls() -> Tuple[List[str], List[str]]:
    good, bad = _read_channel_ids()
    out: List[str] = []
    for cid in good:
        cid_enc = urllib.parse.quote(cid, safe="")
        out.append(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid_enc}")
    return (out, bad)



# HAT_YT_FEEDS_LOADER_BEGIN (do not edit)
def _read_feed_urls(repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    Returns (feed_urls, bad_entries).
    Priority:
      1) env HAT_YOUTUBE_FEEDS_PATH / HAT_INTEL_YOUTUBE_FEEDS_PATH / YOUTUBE_FEEDS_PATH (file: urls or UC ids)
      2) env HAT_YT_CHANNEL_IDS (semicolon-separated UC ids)
      3) config/youtube_channels.txt (UC ids)
    Accepted per-line values:
      - full feed URL: https://www.youtube.com/feeds/videos.xml?channel_id=UC....
      - UC channel id: UCxxxxxxxxxxxx
    """
    bad: List[str] = []
    feeds: List[str] = []

    def _add_from_line(s: str) -> None:
        ss = (s or "").strip()
        if (not ss) or ss.startswith("#"):
            return
        # full URL
        if ss.startswith("http://") or ss.startswith("https://"):
            if "youtube.com/feeds/videos.xml" in ss and "channel_id=" in ss:
                feeds.append(ss)
            else:
                bad.append(ss)
            return
        # channel id
        if re.match(r"^UC[a-zA-Z0-9_-]{10,}$", ss):
            cid_enc = urllib.parse.quote(ss, safe="")
            feeds.append(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid_enc}")
        else:
            bad.append(ss)

    # 1) feed file path (urls or ids)
    p = (os.getenv("HAT_YOUTUBE_FEEDS_PATH") or os.getenv("HAT_INTEL_YOUTUBE_FEEDS_PATH") or os.getenv("YOUTUBE_FEEDS_PATH") or "").strip()
    if not p:
        # repo default
        p = str(repo_root / "src" / ".intel" / "youtube_feeds.txt")
    try:
        fp = Path(p)
        if fp.exists():
            for ln in fp.read_text(encoding="utf-8", errors="ignore").splitlines():
                _add_from_line(ln)
            return (sorted(set(feeds)), bad)
    except Exception:
        pass

    # 2) env channel ids
    raw = (os.getenv("HAT_YT_CHANNEL_IDS") or "").strip()
    if raw:
        for cid in [x.strip() for x in raw.split(";") if x.strip()]:
            _add_from_line(cid)
        return (sorted(set(feeds)), bad)

    # 3) config youtube_channels.txt
    cfg = repo_root / "config" / "youtube_channels.txt"
    if cfg.exists():
        for ln in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
            _add_from_line(ln)
    return (sorted(set(feeds)), bad)
# HAT_YT_FEEDS_LOADER_END (do not edit)

def _parse_atom(xml_text: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    root = ET.fromstring(xml_text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        link_el = entry.find("a:link", ns)
        link = (link_el.get("href") if link_el is not None else "") or ""
        published = (entry.findtext("a:published", default="", namespaces=ns) or "").strip()
        out.append({"title": title, "url": link, "created": published})
    return out


def collect(hours_back: int = 720, limit_per_feed: int = 30) -> Tuple[bool, str, int]:
    repo = _repo_root()
    topic_keywords = _read_topic_keywords(repo)
    out_path = repo / "src" / ".intel" / "youtube_feed.jsonl"
    watch = _watchlist()
    feeds, bad = _read_feed_urls(repo)

    if (not feeds) and bad:
        return (False, "yt_invalid_channel_ids:" + ",".join(bad), 0)

    if not feeds:
        return (True, "no_channels_configured", 0)

    existing = load_existing_ids(out_path)
    rows: List[Dict[str, Any]] = []
    accepted_total = 0
    fresh_before_dedupe = 0
    empty_feeds: List[str] = []

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": os.getenv("HAT_YT_ACCEPT_LANGUAGE", "en-US,en;q=0.9"),
        "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
    }

    try:
        for url in feeds:
            r = requests.get(url, timeout=15, headers=headers)
            r.raise_for_status()
            items = _parse_atom(r.text)[: max(1, int(limit_per_feed))]
            if not items:
                empty_feeds.append(url)

            for it in items:
                title = it.get("title", "")
                syms = _tag_symbols(title, watch)
                topics = _match_topics(title, topic_keywords)

                # Accept if symbol OR topic keyword match
                if (not syms) and (not topics):
                    continue

                # Keep downstream stable: topic-only gets watchlist symbols
                symbols_final = syms if syms else watch

                accepted_total += 1


                rows.append(


                    normalize_record(
                        kind="youtube",
                        provider="yt_rss",
                        title=title,
                        url=it.get("url", ""),
                        created=it.get("created", ""),
                        symbols=symbols_final,
                        raw={
                            "feed_url": url,
                            "topic_keywords": topics,
                            "is_topic_relevant": bool(topics),
                            "topic_only": bool(topics) and (not syms),
                        },
                    )
                )
    except Exception as e:
        return (False, f"yt_rss_error:{type(e).__name__}:{e}", 0)

    rows = filter_fresh(rows, hours_back=hours_back)
    fresh_before_dedupe = len(rows)
    rows = dedupe_new(rows, existing)
    if rows:
        write_jsonl_atomic_append(out_path, rows)


    if empty_feeds and (not rows):
        return (False, "yt_empty_feeds:" + ",".join(empty_feeds), 0)

    reason_final = f"ok(written={len(rows)} accepted={accepted_total} fresh={fresh_before_dedupe} feeds={len(feeds)})"
    if len(rows) == 0:
        if fresh_before_dedupe > 0:
            reason_final = f"ok(no_new_items hours_back={hours_back} deduped={fresh_before_dedupe} accepted={accepted_total} feeds={len(feeds)})"
        else:
            reason_final = f"ok(no_fresh_items hours_back={hours_back} accepted={accepted_total} feeds={len(feeds)})"

    return (True, reason_final, len(rows))

