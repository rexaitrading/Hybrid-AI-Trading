import json
import sys

from hybrid_ai_trading.data_clients.polygon_news_client import Client as PolyNews
from hybrid_ai_trading.utils.providers import load_providers


def main():
    tick = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    cfg = load_providers("config/providers.yaml")
    pn = PolyNews(**(cfg.get("providers", {}).get("polygon", {})))
    out = pn.latest(tick, limit=10)
    print(json.dumps(out if isinstance(out, dict) else {"_error": "bad json"}, indent=2)[:2000])


if __name__ == "__main__":
    main()
