from __future__ import annotations
import os
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._writer import normalize_record, load_existing_ids, dedupe_new, filter_fresh, write_jsonl_atomic_append

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]

def _watchlist() -> List[str]:
    s = (os.getenv('HAT_INTEL_WATCHLIST') or 'NVDA,SPY,QQQ').strip()
    out = [x.strip().upper() for x in s.split(',') if x.strip()]
    return sorted(set(out))

def _tag_symbols(title: str, watch: List[str]) -> List[str]:
    t = (title or '').upper()
    syms: List[str] = []
    for sym in watch:
        if re.search(rf'(?<![A-Z0-9]){re.escape(sym)}(?![A-Z0-9])', t):
            syms.append(sym)
    return syms

def _yt_feed_urls() -> List[str]:
    ids = (os.getenv('HAT_YT_CHANNEL_IDS') or '').strip()
    if not ids:
        return []
    out: List[str] = []
    for cid in [x.strip() for x in ids.split(';') if x.strip()]:
        out.append(f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}')
    return out

def _parse_atom(xml_text: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    root = ET.fromstring(xml_text)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    for entry in root.findall('a:entry', ns):
        title = (entry.findtext('a:title', default='', namespaces=ns) or '').strip()
        link_el = entry.find('a:link', ns)
        link = (link_el.get('href') if link_el is not None else '') or ''
        published = (entry.findtext('a:published', default='', namespaces=ns) or '').strip()
        out.append({'title': title, 'url': link, 'created': published})
    return out

def collect(hours_back: int = 72, limit_per_feed: int = 30) -> Tuple[bool, str, int]:
    repo = _repo_root()
    out_path = repo / 'src' / '.intel' / 'youtube_feed.jsonl'
    watch = _watchlist()
    feeds = _yt_feed_urls()
    if not feeds:
        return (True, 'no_channels_configured', 0)

    existing = load_existing_ids(out_path)
    rows: List[Dict[str, Any]] = []
    try:
        for url in feeds:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            items = _parse_atom(r.text)[: max(1, int(limit_per_feed))]
            for it in items:
                title = it.get('title','')
                syms = _tag_symbols(title, watch)
                if not syms:
                    continue
                rows.append(normalize_record(
                    kind='youtube',
                    provider='yt_rss',
                    title=title,
                    url=it.get('url',''),
                    created=it.get('created',''),
                    symbols=syms,
                    raw={'feed_url': url},
                ))
    except Exception as e:
        return (False, f'yt_rss_error:{type(e).__name__}:{e}', 0)

    rows = filter_fresh(rows, hours_back=hours_back)
    rows = dedupe_new(rows, existing)
    if rows:
        write_jsonl_atomic_append(out_path, rows)
    return (True, 'ok', len(rows))
