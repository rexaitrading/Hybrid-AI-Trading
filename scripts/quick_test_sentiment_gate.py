import logging
import os
from textwrap import shorten

from hybrid_ai_trading.risk.sentiment_gate import score_headlines_for_symbols

# Silence warning spam from the sentiment filter logger
logging.getLogger("hybrid_ai_trading.risk.sentiment_filter").setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)

SYMS = os.getenv("GATE_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,TSLA")
HRS = int(os.getenv("GATE_HOURS", "24"))
LIM = int(os.getenv("GATE_LIMIT", "100"))
SIDE = os.getenv("GATE_SIDE", "BUY")
TOPN = int(os.getenv("GATE_TOPN", "10"))

print("=== Sentiment Gate (quiet) ===")
res = score_headlines_for_symbols(SYMS, hours_back=HRS, limit=LIM, side=SIDE)
print(f"date_from: {res['date_from']}   total stories (watch-filtered): {res['total']}")

print("\nSymbol  Seen  Allowed  Blocked  AvgScore")
print("----------------------------------------")
for sym, d in sorted(res["per_symbol"].items()):
    print(f"{sym:5}  {d['seen']:4}  {d['allowed']:7}  {d['blocked']:7}  {d['avgScore']:.4f}")

allowed = [s for s in res["stories"] if s.get("allow")]
allowed.sort(key=lambda x: x.get("score", 0), reverse=True)
print(f"\nTop {min(TOPN,len(allowed))} ALLOW headlines:")
for s in allowed[:TOPN]:
    title = shorten(s.get("title", ""), width=100, placeholder="…")
    syms = ",".join(s.get("symbols", []))
    print(f"  {s.get('score',0):.2f}  [{syms}]  {title}  -> {s.get('url')}")
