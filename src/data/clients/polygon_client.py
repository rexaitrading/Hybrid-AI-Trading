# src/data/clients/polygon_client.py
import requests

from src.config.settings import load_config


class PolygonAPIError(RuntimeError):
    """Raised when Polygon API call fails"""

    pass


class PolygonClient:
    def __init__(self):
        config = load_config()
        try:
            key = config["providers"]["polygon"]["api_key_env"]
        except Exception as e:
            raise PolygonAPIError(f"Invalid config for Polygon: {e}")

        if not key:
            raise RuntimeError("Polygon API key missing, please check config.yaml")

        self.headers = {"Authorization": f"Bearer {key}"}

    def prev_close(self, ticker: str):
        """Get previous day’s close data for a ticker"""
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise PolygonAPIError(f"Polygon prev_close failed: {e}")

    def ping(self) -> bool:
        """Basic health check using AAPL as test symbol"""
        try:
            _ = self.prev_close("AAPL")
            return True
        except Exception:
            return False
