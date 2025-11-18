#!/usr/bin/env python
"""
tools/translate_text.py

Usage:
  python tools/translate_text.py "你好，今天波動很大" zh-TW en
"""

import os
import sys
import json
import requests

API_KEY = os.environ.get("GOOGLE_TRANSLATE_KEY")
if not API_KEY:
    print("ERROR: GOOGLE_TRANSLATE_KEY env var is not set.", file=sys.stderr)
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: translate_text.py <text> [source] [target]", file=sys.stderr)
        sys.exit(1)

    text   = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else ""
    target = sys.argv[3] if len(sys.argv) > 3 else "en"

    url = f"https://translation.googleapis.com/language/translate/v2?key={API_KEY}"
    payload = {"q": [text], "target": target}
    if source:
        payload["source"] = source

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    translated = data["data"]["translations"][0]["translatedText"]
    print(translated)

if __name__ == "__main__":
    main()