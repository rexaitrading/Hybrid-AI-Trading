# tests/check_prev_close.py
from __future__ import annotations

import glob
import json
import os

import pandas as pd

DATA_DIR = "data"


def latest_file(pattern: str) -> str | None:
    files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
    return files[-1] if files else None


def main():
    csv_path = latest_file("prev_close_*.csv")
    json_path = latest_file("prev_close_*.json")

    assert csv_path, "Ã¢ÂÅ’ Ã¦â€°Â¾Ã¤Â¸ÂÃ¥Ë†Â° CSV Ã¦Âªâ€ (data/prev_close_*.csv)"
    assert json_path, "Ã¢ÂÅ’ Ã¦â€°Â¾Ã¤Â¸ÂÃ¥Ë†Â° JSON Ã¦Âªâ€ (data/prev_close_*.json)"
    print(f"Ã¢Å“â€¦ Ã¦Å“â‚¬Ã¦â€“Â° CSV: {os.path.basename(csv_path)}")
    print(f"Ã¢Å“â€¦ Ã¦Å“â‚¬Ã¦â€“Â° JSON: {os.path.basename(json_path)}")

    # Ã¨Â®â‚¬ CSV
    df = pd.read_csv(csv_path)
    print("\n=== CSV Ã¦Â¦â€šÃ¨Â¦Â½ ===")
    print(df.head(3).to_string(index=False))
    print("\nÃ¦Â¬â€žÃ¤Â½ÂÃ¯Â¼Å¡", list(df.columns))

    required_cols = [
        "group",
        "symbol",
        "asof",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "status",
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    assert not missing_cols, f"Ã¢ÂÅ’ Ã§Â¼ÂºÃ¥Â°â€˜Ã¦Â¬â€žÃ¤Â½Â: {missing_cols}"

    # Ã¥Å¸ÂºÃ¦Å“Â¬Ã¦ÂªÂ¢Ã¦Å¸Â¥
    n_rows = len(df)
    n_nulls = df.isna().sum().sum()
    print(
        f"\nÃ§Â¸Â½Ã§Â­â€ Ã¦â€¢Â¸Ã¯Â¼Å¡{n_rows}Ã¯Â¼Å’Ã¥â€¦Â¨Ã¨Â¡Â¨Ã§Â©ÂºÃ¥â‚¬Â¼Ã§Â¸Â½Ã¦â€¢Â¸Ã¯Â¼Å¡{n_nulls}"
    )

    # Ã¥Ââ€ž group Ã¨Â¦â€ Ã¨â€œâ€¹
    print("\nÃ¥Ââ€ž group Ã¨Â¦â€ Ã¨â€œâ€¹Ã¯Â¼Å¡")
    print(df.groupby("group")["symbol"].nunique().to_string())

    # status Ã¦ÂªÂ¢Ã¦Å¸Â¥
    bad = df[df["status"].astype(str).str.upper() != "OK"]
    if not bad.empty:
        print("\nÃ¢Å¡Â Ã¯Â¸Â Ã©ÂÅ¾ OK Ã§â€¹â‚¬Ã¦â€¦â€¹Ã§Â­â€ Ã¦â€¢Â¸Ã¯Â¼Å¡", len(bad))
        print(bad[["group", "symbol", "status"]].to_string(index=False))
    else:
        print("\nÃ¢Å“â€¦ Ã¦â€°â‚¬Ã¦Å“â€°Ã§Â­â€ Ã¦â€¢Â¸ status Ã©Æ’Â½Ã¦ËœÂ¯ OK")

    # Ã¨Â®â‚¬ JSON Ã§Â¢ÂºÃ¨ÂªÂÃ¨Æ’Â½ parse
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"\nJSON Ã§Â­â€ Ã¦â€¢Â¸Ã¯Â¼Å¡{len(data)} Ã¢Å“â€¦")
