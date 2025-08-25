# utils/crypto.py — CoinAPI 封裝：穩定、可批次、相容 export_prev_close.py

from __future__ import annotations
import os, time, math
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone as tz
from dotenv import load_dotenv

load_dotenv()

COINAPI_KEY = os.getenv("COINAPI_KEY")
BASE = "https://rest.coinapi.io"
HEADERS = {"X-CoinAPI-Key": COINAPI_KEY} if COINAPI_KEY else {}

# ---- 小工具 --------------------------------------------------------------

def _normalize_symbol(sym: str) -> str:
    """把 'BTC.X' / 'ETH.X' 這種帶 .X 的代碼，轉成 CoinAPI 需要的 'BTC' / 'ETH'。"""
    s = sym.strip().upper()
    return s[:-2] if s.endswith(".X") else s

def _iso(ts: datetime) -> str:
    return ts.replace(tzinfo=tz.utc).isoformat().replace("+00:00", "Z")

def _retry_get(url: str, headers: dict, timeout: int = 10, max_retry: int = 3, backoff: float = 1.5):
    """簡單重試：429/5xx 做退避，其他直接丟出。"""
    last = None
    for i in range(max_retry):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            # 速率限制：429
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 1.0)) if r.headers else (backoff ** i)
                time.sleep(min(wait, 10.0))
                last = r
                continue
            r.raise_for_status()
            return r
        except requests.HTTPError as e:
            # 5xx 再試；401/403/404 直接丟
            code = getattr(e.response, "status_code", 0)
            if code >= 500:
                time.sleep(backoff ** i)
                last = e
                continue
            raise
        except requests.RequestException as e:
            # 網路抖動再試
            last = e
            time.sleep(backoff ** i)
    if isinstance(last, requests.Response):
        last.raise_for_status()
    elif last:
        raise last
    else:
        raise RuntimeError("Unknown request error")

# ---- 主要 API ------------------------------------------------------------

# 檔案頂部（已經有 COINAPI_KEY / BASE 之後，加呢行一次就夠）
HEADERS = {"X-CoinAPI-Key": COINAPI_KEY} if COINAPI_KEY else {}

def prev_close_ohlc(symbol: str, quote: str = "USD") -> Dict[str, Optional[float]]:
    """
    取「前一日收市」OHLC，回傳欄位與股票一致：
    open / high / low / close / asof / volume / vwap / status
    沒有 API KEY 或取不到資料時，status 分別為 NO_API_KEY / NO_DATA / ERROR。
    """
    if not COINAPI_KEY:
        return {
            "asof": "", "open": None, "high": None, "low": None, "close": None,
            "volume": None, "vwap": None, "status": "NO_API_KEY",
        }

    base = _normalize_symbol(symbol) # 例如 'BTC.X' -> 'BTC'
    url = f"{BASE}/v1/ohlcv/{base}/{quote}/history?period_id=1DAY&limit=2"

    try:
        r = _retry_get(url, headers=HEADERS, timeout=10, max_retry=3)
        bars = r.json()

        # 沒資料
        if not isinstance(bars, list) or len(bars) == 0:
            return {
                "asof": "", "open": None, "high": None, "low": None, "close": None,
                "volume": None, "vwap": None, "status": "NO_DATA",
            }

        # 最新一根可能是當天未收盤，用倒數第二根；若只有一根就用那一根
        bar = bars[-2] if len(bars) >= 2 else bars[-1]

        return {
            "asof": bar.get("time_close", ""),
            "open": bar.get("price_open"),
            "high": bar.get("price_high"),
            "low": bar.get("price_low"),
            "close": bar.get("price_close"),
            "volume": bar.get("volume_traded", 0.0),
            "vwap": None, # CoinAPI 1DAY 沒有 vwap 欄位
            "status": "OK",
        }

    except Exception as e:
        return {
            "asof": "", "open": None, "high": None, "low": None, "close": None,
            "volume": None, "vwap": None, "status": f"ERROR: {e}",
        }

    except Exception as e:
        return {
            "asof": "",
            "open": None, "high": None, "low": None, "close": None,
            "volume": None, "vwap": None, "status": f"ERROR: {e}",
        }

def latest_price(symbol: str, quote: str = "USD") -> Tuple[Optional[float], Optional[str], str]:
    """
    讀取即時/最近成交價（作測試或盤中監測用）。
    回傳：(price, iso_time, status)
    """
    if not COINAPI_KEY:
        return None, None, "NO_API_KEY"

    base = _normalize_symbol(symbol)
    url = f"{BASE}/v1/exchangerate/{base}/{quote}"
    try:
        r = _retry_get(url, headers=HEADERS, timeout=6, max_retry=2)
        data = r.json()
        return data.get("rate"), data.get("time"), "OK"
    except Exception as e:
        return None, None, f"ERROR: {e}"

def batch_prev_close(symbols: List[str], quote: str = "USD") -> Dict[str, Dict]:
    """
    批次取多個 crypto 的前收，輸出 dict：{symbol: row(dict)}。
    便於在 export_prev_close.py 的迴圈內使用。
    """
    out: Dict[str, Dict] = {}
    for s in symbols:
        out[s] = prev_close_ohlc(s, quote=quote)
        # 避免頻率過快
        time.sleep(0.15)
    return out

