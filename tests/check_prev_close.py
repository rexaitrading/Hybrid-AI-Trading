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

    assert (
        csv_path
    ), "ÃƒÂ¢Ã‚ÂÃ…â€™ ÃƒÂ¦Ã¢â‚¬Â°Ã‚Â¾ÃƒÂ¤Ã‚Â¸Ã‚ÂÃƒÂ¥Ã‹â€ Ã‚Â° CSV ÃƒÂ¦Ã‚ÂªÃ¢â‚¬Â (data/prev_close_*.csv)"
    assert (
        json_path
    ), "ÃƒÂ¢Ã‚ÂÃ…â€™ ÃƒÂ¦Ã¢â‚¬Â°Ã‚Â¾ÃƒÂ¤Ã‚Â¸Ã‚ÂÃƒÂ¥Ã‹â€ Ã‚Â° JSON ÃƒÂ¦Ã‚ÂªÃ¢â‚¬Â (data/prev_close_*.json)"
    print(
        f"ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ ÃƒÂ¦Ã…â€œÃ¢â€šÂ¬ÃƒÂ¦Ã¢â‚¬â€œÃ‚Â° CSV: {os.path.basename(csv_path)}"
    )
    print(
        f"ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ ÃƒÂ¦Ã…â€œÃ¢â€šÂ¬ÃƒÂ¦Ã¢â‚¬â€œÃ‚Â° JSON: {os.path.basename(json_path)}"
    )

    # ÃƒÂ¨Ã‚Â®Ã¢â€šÂ¬ CSV
    df = pd.read_csv(csv_path)
    print("\n=== CSV ÃƒÂ¦Ã‚Â¦Ã¢â‚¬Å¡ÃƒÂ¨Ã‚Â¦Ã‚Â½ ===")
    print(df.head(3).to_string(index=False))
    print("\nÃƒÂ¦Ã‚Â¬Ã¢â‚¬Å¾ÃƒÂ¤Ã‚Â½Ã‚ÂÃƒÂ¯Ã‚Â¼Ã…Â¡", list(df.columns))

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
    assert (
        not missing_cols
    ), f"ÃƒÂ¢Ã‚ÂÃ…â€™ ÃƒÂ§Ã‚Â¼Ã‚ÂºÃƒÂ¥Ã‚Â°Ã¢â‚¬ËœÃƒÂ¦Ã‚Â¬Ã¢â‚¬Å¾ÃƒÂ¤Ã‚Â½Ã‚Â: {missing_cols}"

    # ÃƒÂ¥Ã…Â¸Ã‚ÂºÃƒÂ¦Ã…â€œÃ‚Â¬ÃƒÂ¦Ã‚ÂªÃ‚Â¢ÃƒÂ¦Ã…Â¸Ã‚Â¥
    n_rows = len(df)
    n_nulls = df.isna().sum().sum()
    print(
        f"\nÃƒÂ§Ã‚Â¸Ã‚Â½ÃƒÂ§Ã‚Â­Ã¢â‚¬Â ÃƒÂ¦Ã¢â‚¬Â¢Ã‚Â¸ÃƒÂ¯Ã‚Â¼Ã…Â¡{n_rows}ÃƒÂ¯Ã‚Â¼Ã…â€™ÃƒÂ¥Ã¢â‚¬Â¦Ã‚Â¨ÃƒÂ¨Ã‚Â¡Ã‚Â¨ÃƒÂ§Ã‚Â©Ã‚ÂºÃƒÂ¥Ã¢â€šÂ¬Ã‚Â¼ÃƒÂ§Ã‚Â¸Ã‚Â½ÃƒÂ¦Ã¢â‚¬Â¢Ã‚Â¸ÃƒÂ¯Ã‚Â¼Ã…Â¡{n_nulls}"
    )

    # ÃƒÂ¥Ã‚ÂÃ¢â‚¬Å¾ group ÃƒÂ¨Ã‚Â¦Ã¢â‚¬Â ÃƒÂ¨Ã¢â‚¬Å“Ã¢â‚¬Â¹
    print("\nÃƒÂ¥Ã‚ÂÃ¢â‚¬Å¾ group ÃƒÂ¨Ã‚Â¦Ã¢â‚¬Â ÃƒÂ¨Ã¢â‚¬Å“Ã¢â‚¬Â¹ÃƒÂ¯Ã‚Â¼Ã…Â¡")
    print(df.groupby("group")["symbol"].nunique().to_string())

    # status ÃƒÂ¦Ã‚ÂªÃ‚Â¢ÃƒÂ¦Ã…Â¸Ã‚Â¥
    bad = df[df["status"].astype(str).str.upper() != "OK"]
    if not bad.empty:
        print(
            "\nÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â ÃƒÂ©Ã‚ÂÃ…Â¾ OK ÃƒÂ§Ã¢â‚¬Â¹Ã¢â€šÂ¬ÃƒÂ¦Ã¢â‚¬Â¦Ã¢â‚¬Â¹ÃƒÂ§Ã‚Â­Ã¢â‚¬Â ÃƒÂ¦Ã¢â‚¬Â¢Ã‚Â¸ÃƒÂ¯Ã‚Â¼Ã…Â¡",
            len(bad),
        )
        print(bad[["group", "symbol", "status"]].to_string(index=False))
    else:
        print(
            "\nÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦ ÃƒÂ¦Ã¢â‚¬Â°Ã¢â€šÂ¬ÃƒÂ¦Ã…â€œÃ¢â‚¬Â°ÃƒÂ§Ã‚Â­Ã¢â‚¬Â ÃƒÂ¦Ã¢â‚¬Â¢Ã‚Â¸ status ÃƒÂ©Ã†â€™Ã‚Â½ÃƒÂ¦Ã‹Å“Ã‚Â¯ OK"
        )

    # ÃƒÂ¨Ã‚Â®Ã¢â€šÂ¬ JSON ÃƒÂ§Ã‚Â¢Ã‚ÂºÃƒÂ¨Ã‚ÂªÃ‚ÂÃƒÂ¨Ã†â€™Ã‚Â½ parse
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(
        f"\nJSON ÃƒÂ§Ã‚Â­Ã¢â‚¬Â ÃƒÂ¦Ã¢â‚¬Â¢Ã‚Â¸ÃƒÂ¯Ã‚Â¼Ã…Â¡{len(data)} ÃƒÂ¢Ã…â€œÃ¢â‚¬Â¦"
    )
