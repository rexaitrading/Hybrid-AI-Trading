import importlib

m = importlib.import_module("hybrid_ai_trading.data.clients.polygon_news_client")
print("polygon client import OK:", m.__file__)
