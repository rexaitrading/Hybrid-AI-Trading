# tests/check_prev_close.py
from __future__ import annotations
import json, glob, os
import pandas as pd

DATA_DIR = "data"

def latest_file(pattern: str) -> str | None:
    files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
    return files[-1] if files else None

def main():
    csv_path = latest_file("prev_close_*.csv")
    json_path = latest_file("prev_close_*.json")

    assert csv_path, "❌ 找不到 CSV 檔 (data/prev_close_*.csv)"
    assert json_path, "❌ 找不到 JSON 檔 (data/prev_close_*.json)"
    print(f"✅ 最新 CSV: {os.path.basename(csv_path)}")
    print(f"✅ 最新 JSON: {os.path.basename(json_path)}")

    # 讀 CSV
    df = pd.read_csv(csv_path)
    print("\n=== CSV 概覽 ===")
    print(df.head(3).to_string(index=False))
    print("\n欄位：", list(df.columns))

    required_cols = ["group","symbol","asof","open","high","low","close","volume","vwap","status"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    assert not missing_cols, f"❌ 缺少欄位: {missing_cols}"

    # 基本檢查
    n_rows = len(df)
    n_nulls = df.isna().sum().sum()
    print(f"\n總筆數：{n_rows}，全表空值總數：{n_nulls}")

    # 各 group 覆蓋
    print("\n各 group 覆蓋：")
    print(df.groupby("group")["symbol"].nunique().to_string())

    # status 檢查
    bad = df[df["status"].astype(str).str.upper() != "OK"]
    if not bad.empty:
        print("\n⚠️ 非 OK 狀態筆數：", len(bad))
        print(bad[["group","symbol","status"]].to_string(index=False))
    else:
        print("\n✅ 所有筆數 status 都是 OK")

    # 讀 JSON 確認能 parse
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"\nJSON 筆數：{len(data)} ✅")

if __name__ == "__main__":
    main()