# tests/export_prev_close.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any

from utils.config import load_config
from utils.universe import Core_Stocks, Crypto_Signal, Macro_Risk, Leverage_Tools, IPO_Watch
from utils.polygon import PolygonClient


def _ms_to_iso(ms: int) -> str:
    """Polygon 回傳的 t 為毫秒 epoch，轉 ISO UTC 字串。"""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def main():
    # 1) 載入設定 & 建立 client
    cfg = load_config()
    client = PolygonClient()

    # 2) 組別清單
    asset_groups: Dict[str, List[str]] = {
        "Core_Stocks": Core_Stocks,
        "Crypto_Signal": Crypto_Signal,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }

    # 3) 逐組別抓取前日收市，累積成 rows
    rows: List[Dict[str, Any]] = []

    for group, symbols in asset_groups.items():
        print(f"\n📊 取得 {group}（{len(symbols)}）")
        for symbol in symbols:
            try:
                data = client.prev_close(symbol)
                if "results" in data and data["results"]:
                    r = data["results"][0]
                    row = {
                        "group": group,
                        "symbol": symbol,
                        "asof": _ms_to_iso(r.get("t", 0)),
                        "open": r.get("o"),
                        "high": r.get("h"),
                        "low": r.get("l"),
                        "close": r.get("c"),
                        "volume": r.get("v"),
                        "vwap": r.get("vw"),
                        "status": data.get("status", "OK"),
                    }
                    rows.append(row)
                    print(f" ✅ {symbol} close={row['close']} O/H/L={row['open']}/{row['high']}/{row['low']} vol={row['volume']}")
                else:
                    rows.append({
                        "group": group, "symbol": symbol, "asof": "",
                        "open": None, "high": None, "low": None, "close": None,
                        "volume": None, "vwap": None, "status": f"NO_DATA: {data}"
                    })
                    print(f" ⚠️ {symbol} 無數據")
            except Exception as e:
                rows.append({
                    "group": group, "symbol": symbol, "asof": "",
                    "open": None, "high": None, "low": None, "close": None,
                    "volume": None, "vwap": None, "status": f"ERROR: {e}"
                })
                print(f" ❌ {symbol} 錯誤: {e}")

    # 4) 輸出 CSV / JSON 到 ./data
    os.makedirs("data", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("data", f"prev_close_{stamp}.csv")
    json_path = os.path.join("data", f"prev_close_{stamp}.json")

    # CSV（標準庫寫，免依賴 pandas）
    import csv
    headers = ["group", "symbol", "asof", "open", "high", "low", "close", "volume", "vwap", "status"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\n📁 已輸出：\n- {csv_path}\n- {json_path}")


if __name__ == "__main__":
    main()