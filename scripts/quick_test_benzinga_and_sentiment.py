from hybrid_ai_trading.data.clients.benzinga_client import BenzingaClient
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter

c = BenzingaClient()
stories = c.get_news("AAPL,TSLA", limit=10)

f = SentimentFilter(model="vader", threshold=0.7, neutral_zone=0.2, smoothing=3)

for s in stories:
    title = s.get("title","")
    score = f.score(title)
    allowed = f.allow_trade(title, side="BUY", precomputed_score=score)
    syms = ",".join([ (x.get("name") or "") for x in s.get("stocks", []) ])
    print(f"[{s.get('created')}] {title} ({syms}) | Score={score:.2f} | Allow={allowed} | {s.get('url')}")