# utils/polygon.py
import os
import requests
from utils.config import load_config # ✅ 引入 config loader

class PolygonClient:
    def __init__(self):
        config = load_config() # ✅ 讀取 config.yaml
        key = config["providers"]["polygon"]["api_key_env"]

        if not key:
            raise RuntimeError("找不到 Polygon API key，請確認 config.yaml")
        self.headers = {"Authorization": f"Bearer {key}"}

    def prev_close(self, ticker: str):
        """取得某股票的前一日收市數據"""
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        data = r.json()
        return data
