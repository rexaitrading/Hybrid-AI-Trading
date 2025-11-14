#!/usr/bin/env python
"""
tools/news_translate.py

Scan .intel/news_feed.jsonl, auto-translate non-English titles to English
(using GOOGLE_TRANSLATE_KEY) and write .intel/news_feed_translated.jsonl.

- Keeps original title as 'title'
- Adds:
    - 'title_lang'   (detected language code or 'en')
    - 'title_en'     (English version; may equal original if already English)
    - 'macro_region' (NA / EU / APAC / EM / GLOBAL)
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

import requests

GOOGLE_KEY = os.environ.get("GOOGLE_TRANSLATE_KEY")

NEWS_IN_PATH = Path(".intel") / "news_feed.jsonl"
NEWS_OUT_PATH = Path(".intel") / "news_feed_translated.jsonl"


def detect_lang_heuristic(text: str) -> str:
    """
    Very simple heuristic based on Unicode ranges.
    This is enough for our main use-cases (zh/ja/ko/hi).
    Everything else we treat as 'auto' (return '').
    """
    has_cjk = False
    has_korean = False
    has_japanese = False
    has_deva = False

    for ch in text:
        cp = ord(ch)
        # CJK Unified Ideographs (Chinese, some Japanese)
        if 0x4E00 <= cp <= 0x9FFF:
            has_cjk = True
        # Hiragana / Katakana (Japanese)
        if 0x3040 <= cp <= 0x30FF:
            has_japanese = True
        # Hangul syllables (Korean)
        if 0xAC00 <= cp <= 0xD7AF:
            has_korean = True
        # Devanagari (Hindi, etc.)
        if 0x0900 <= cp <= 0x097F:
            has_deva = True

    if has_japanese:
        return "ja"
    if has_korean:
        return "ko"
    if has_deva:
        return "hi"
    if has_cjk:
        # We dont distinguish zh-CN vs zh-TW here; use generic 'zh'
        return "zh"

    # default: let Google auto-detect
    return ""


def infer_macro_region(rec: Dict[str, Any]) -> str:
    """
    Coarse macro bucket for the headline:
      - NA   : US / Canada
      - EU   : Europe / UK
      - APAC : Asia-Pacific (China / Japan / Korea / India / etc.)
      - EM   : broader emerging markets
      - GLOBAL: fallback
    Uses publisher (from title), lang guess, and some geographic keywords.
    """
    title_en = (rec.get("title_en") or rec.get("title") or "").lower()
    title_raw = (rec.get("title") or "").lower()
    link = (rec.get("link") or "").lower()
    query = (rec.get("query") or "").lower()
    lang = (rec.get("title_lang") or "").lower()

    text = " ".join([title_en, title_raw, link, query])

    # Helper for keyword match
    def has_any(needles):
        return any(n in text for n in needles)

        # ---- NORTH AMERICA (US + CA) ----
    if has_any([
        "yahoo finance",
        "usa today",
        "wall street journal",
        "marketwatch",
        "morningstar",
        "barron's",
        "cnbc",
        "24/7 wall st",
        "seekingalpha.com",
        "seeking alpha",
        "bloomberg.com",
        "reuters.com",
        "markets.businessinsider.com",
        "u.s. stocks",
        "us stocks",
        "s&p 500",
        "nasdaq",
        "dow jones",
        "the globe and mail",
        "financial post",
        "calgary herald",
    ]):
        return "NA"

    if "tsx" in text or "canadian" in text or "toronto" in text:
        return "NA"

    # US exchange / ETF style hints
    if has_any([
        "nyse:", "nysearca:", "nasdaq:", "amex:",
        "(spy)", " spy ", " spy,", " spy.", " spy:",
        "nysearca:spy",
        "(qqq)", " qqq ", "nysearca:qqq",
        "(iwm)", " iwm ", "nysearca:iwm",
        "(dia)", " dia ", "nysearca:dia",
        "nysearca:voo", "nysearca:vti",
    ]):
        return "NA"

    # ---- EUROPE ----
    if has_any([
        "financial times",
        "ft.com",
        "the guardian",
        "eurozone",
        "european union",
        "european central bank",
        "ecb",
        "london",
        "frankfurt",
        "dax",
        "stoxx 600",
        "ubs",
        "credit suisse",
        "deutsche bank",
    ]):
        return "EU"

    # ---- APAC (China / Japan / Korea / India / etc.) ----
    if lang in ("zh", "ja", "ko", "hi"):
        return "APAC"

    if has_any([
        "nikkei", "tokyo", "osaka",
        "sensex", "nifty", "bse", "mumbai", "india",
        "hang seng", "hong kong", "hsi",
        "taiwan", "taipei",
        "kospi", "korea",
        "shanghai composite", "shenzhen",
    ]):
        return "APAC"

    # ---- EMERGING MARKETS (catch-all) ----
    if has_any([
        "emerging market",
        "latam",
        "brazil", "bovespa", "são paulo", "sao paulo",
        "mexico", "bmv",
        "johannesburg", "south africa",
        "nigeria",
        "vietnam", "hydrometeorological forecasting",
        "national center for hydro-meteorological forecasting",
    ]):
        return "EM"

    # Fallback
    return "GLOBAL"


def translate_text(text: str, source_lang: str, target_lang: str = "en") -> Optional[str]:
    """
    Call Google Translation API.
    - If source_lang is '', let Google auto-detect.
    - If 400/403/etc., return None so we can fall back to original text.
    """
    if not GOOGLE_KEY:
        return None

    url = "https://translation.googleapis.com/language/translate/v2"
    params = {"key": GOOGLE_KEY}
    payload: Dict[str, Any] = {"q": [text], "target": target_lang}
    if source_lang:
        payload["source"] = source_lang

    try:
        resp = requests.post(url, params=params, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        sys.stderr.write(f"[WARN] translate failed ({source_lang}->{target_lang}): {e}\n")
        return None

    try:
        data = resp.json()
        return data["data"]["translations"][0]["translatedText"]
    except Exception as e:
        sys.stderr.write(f"[WARN] unexpected translate response: {e}\n")
        return None


def process_news() -> None:
    if not NEWS_IN_PATH.exists():
        sys.stderr.write(f"ERROR: {NEWS_IN_PATH} not found. Run tools/news_feed.py first.\n")
        sys.exit(1)

    NEWS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    total_in = 0
    total_out = 0
    translated = 0

    with NEWS_IN_PATH.open("r", encoding="utf-8") as fin, \
         NEWS_OUT_PATH.open("w", encoding="utf-8") as fout:

        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                rec: Dict[str, Any] = json.loads(line)
            except Exception:
                continue

            total_in += 1

            title = rec.get("title", "")
            if not title:
                # Still assign a region based on whatever we have
                rec["macro_region"] = infer_macro_region(rec)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total_out += 1
                continue

            # If already has an English title, keep it
            if "title_en" in rec:
                rec["macro_region"] = infer_macro_region(rec)
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total_out += 1
                continue

            lang_guess = detect_lang_heuristic(title)

            # Default: assume English if we don't see non-ASCII letters
            if not any(ord(c) > 127 for c in title):
                rec["title_lang"] = "en"
                rec["title_en"] = title
            else:
                # Try translate
                t = translate_text(title, lang_guess, "en")
                if t:
                    rec["title_lang"] = lang_guess or "auto"
                    rec["title_en"] = t
                    translated += 1
                else:
                    # Fallback: keep original as title_en too
                    rec["title_lang"] = lang_guess or "unknown"
                    rec["title_en"] = title

            # NEW: assign macro_region based on title_en/title/link/lang
            rec["macro_region"] = infer_macro_region(rec)

            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total_out += 1

    print(f"Processed {total_in} news rows, wrote {total_out}, translated={translated}")
    print(f"Wrote translated feed to {NEWS_OUT_PATH}")


def main() -> None:
    if not GOOGLE_KEY:
        sys.stderr.write("WARN: GOOGLE_TRANSLATE_KEY not set; copying feed without translation.\n")
        if not NEWS_IN_PATH.exists():
            sys.stderr.write(f"ERROR: {NEWS_IN_PATH} not found.\n")
            sys.exit(1)
        NEWS_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # In the no-key case we just copy through without adding macro_region,
        # which is acceptable as a degraded mode.
        with NEWS_IN_PATH.open("r", encoding="utf-8") as fin, \
             NEWS_OUT_PATH.open("w", encoding="utf-8") as fout:
            for line in fin:
                fout.write(line)
        print(f"Copied {NEWS_IN_PATH} -> {NEWS_OUT_PATH} without translation/region (no key).")
        return

    process_news()


if __name__ == "__main__":
    main()