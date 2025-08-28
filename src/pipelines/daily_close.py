# tests/export_prev_close.py
from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from src.config.settings import load_config
from utils.universe import Core_Stocks, Crypto_Signal, Macro_Risk, Leverage_Tools, IPO_Watch
from src.data.clients.polygon_client import PolygonClient
from src.data.clients.coinapi_client import batch_prev_close # <--- ç”¨æ–¼ Crypto_Signal ä¸€æ¬¡éŽæŠ“

def _ms_to_iso(ms: int) -> str:
    """Polygon å›žå‚³çš„ t ç‚ºæ¯«ç§’ epochï¼Œè½‰ ISO UTC å­—ä¸²ã€‚"""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return ""

def main():
    # 1) è¼‰å…¥è¨­å®š & å»ºç«‹ client
    cfg = load_config()
    client = PolygonClient()

    # 2) çµ„åˆ¥æ¸…å–®
    asset_groups: Dict[str, List[str]] = {
        "Core_Stocks": Core_Stocks,
        "Crypto_Signal": Crypto_Signal,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }

    # 3) é€çµ„åˆ¥æŠ“å‰æ—¥æ”¶å¸‚ï¼Œç´¯ç©æˆ rows
    rows: List[Dict[str, Any]] = []

    for group, symbols in asset_groups.items():
        print(f"\nðŸ“¥ å–å¾— {group} ({len(symbols)})")
         
        # ---- Crypto_Signal ç”¨ CoinAPIï¼šæ‰¹æ¬¡æŠ“å– ----
        if group == "Crypto_Signal":
            try:
                out = batch_prev_close(symbols, quote="USD")
                for s in symbols:
                    r = out.get(s, {})
                    rows.append({
                        "group": group, "symbol": s,
                        "asof": r.get("asof", ""),
                        "open": r.get("open"),
                        "high": r.get("high"),
                        "low": r.get("low"),
                        "close": r.get("close"),
                        "volume": r.get("volume"),
                        "vwap": r.get("vwap"),
                        "status": r.get("status", "NO_DATA"),
                    })
                print(f"âœ… {group} done")
            except Exception as e:
                print(f"âŒ {group} error: {e}")
            # é€™çµ„è™•ç†å®Œå°±æ›ä¸‹ä¸€çµ„ï¼ˆè·³éŽä¸‹é¢ Polygon æµç¨‹ï¼‰
        continue

        # ---- å…¶ä»–çµ„åˆ¥ç¶­æŒåŽŸæœ¬ Polygon æµç¨‹ï¼ˆé€éš» symbolï¼‰----
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
                    print(f"âœ… {symbol} close={row['close']} O/H/L={row['open']}/{row['high']}/{row['low']}")
                else:
                    rows.append({
                        "group": group, "symbol": symbol, "asof": "",
                        "open": None, "high": None, "low": None, "close": None,
                        "volume": None, "vwap": None, "status": f"NO_DATA: {data}",
                    })
                    print(f"âš ï¸ {symbol} ç„¡æ•¸æ“š")
            except Exception as e:
                rows.append({
                    "group": group, "symbol": symbol, "asof": "",
                    "open": None, "high": None, "low": None, "close": None,
                    "volume": None, "vwap": None, "status": f"ERROR: {e}",
                })
                print(f"âŒ {symbol} éŒ¯èª¤: {e}")    
        
    # 4) è¼¸å‡º CSV / JSON åˆ° ./data
    os.makedirs("data", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join("data", f"prev_close_{stamp}.csv")
    json_path = os.path.join("data", f"prev_close_{stamp}.json")

    # CSVï¼ˆæ¨™æº–åº«å¯«ï¼Œå…ä¾è³´ pandasï¼‰
    import csv
    headers = ["group", "symbol", "asof", "open", "high", "low", "close", "volume", "vwap", "status"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\nðŸ“‚ å·²è¼¸å‡ºï¼š\n- {csv_path}\n- {json_path}")

if __name__ == "__main__":
    main()


