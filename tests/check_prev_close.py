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

    assert csv_path, "âŒ æ‰¾ä¸åˆ° CSV æª” (data/prev_close_*.csv)"
    assert json_path, "âŒ æ‰¾ä¸åˆ° JSON æª” (data/prev_close_*.json)"
    print(f"âœ… æœ€æ–° CSV: {os.path.basename(csv_path)}")
    print(f"âœ… æœ€æ–° JSON: {os.path.basename(json_path)}")

    # è®€ CSV
    df = pd.read_csv(csv_path)
    print("\n=== CSV æ¦‚è¦½ ===")
    print(df.head(3).to_string(index=False))
    print("\næ¬„ä½ï¼š", list(df.columns))

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
    assert not missing_cols, f"âŒ ç¼ºå°‘æ¬„ä½: {missing_cols}"

    # åŸºæœ¬æª¢æŸ¥
    n_rows = len(df)
    n_nulls = df.isna().sum().sum()
    print(f"\nç¸½ç­†æ•¸ï¼š{n_rows}ï¼Œå…¨è¡¨ç©ºå€¼ç¸½æ•¸ï¼š{n_nulls}")

    # å„ group è¦†è“‹
    print("\nå„ group è¦†è“‹ï¼š")
    print(df.groupby("group")["symbol"].nunique().to_string())

    # status æª¢æŸ¥
    bad = df[df["status"].astype(str).str.upper() != "OK"]
    if not bad.empty:
        print("\nâš ï¸ éž OK ç‹€æ…‹ç­†æ•¸ï¼š", len(bad))
        print(bad[["group", "symbol", "status"]].to_string(index=False))
    else:
        print("\nâœ… æ‰€æœ‰ç­†æ•¸ status éƒ½æ˜¯ OK")

    # è®€ JSON ç¢ºèªèƒ½ parse
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"\nJSON ç­†æ•¸ï¼š{len(data)} âœ…")
