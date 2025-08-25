# tests/test_signal_demo.py
from __future__ import annotations
import pandas as pd
import glob, os

DATA_DIR = "data"

def latest_csv(pattern="prev_close_*.csv"):
    files = sorted(glob.glob(os.path.join(DATA_DIR, pattern)))
    return files[-1] if files else None

def main():
    csv_path = latest_csv()
    df = pd.read_csv(csv_path)
    print(f"使用最新數據檔案: {csv_path}")

    # 簡單策略：收市價 > 開市價 = 買入信號
    df["signal"] = df["close"] > df["open"]

    print("\n=== Demo 訊號 ===")
    print(df[["group","symbol","open","close","signal"]].head(10).to_string(index=False))

if __name__ == "__main__":
    main()