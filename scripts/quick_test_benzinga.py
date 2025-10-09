from dotenv import load_dotenv

from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient

load_dotenv()
client = BenzingaClient()
news = client.get_news("AAPL,TSLA", limit=5)
for story in news:
    print(story["created"], story["title"], story["url"])
