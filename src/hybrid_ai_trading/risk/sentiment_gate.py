"""
Sentiment Gate (Hybrid AI Quant Pro v1.0  OE Grade)
- Aggregates news via NewsAggregator
- Scores headlines with SentimentFilter (YAML defaults + lexicon)
- Returns tidy per-symbol metrics for gating BUY/SELL decisions
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import yaml

from hybrid_ai_trading.data.news_aggregator import aggregate_news
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter


def score_headlines_for_symbols(
    symbols_csv: str,
    hours_back: int = None,
    limit: int = None,
    side: str = "BUY",
) -> Dict[str, Any]:
    """Return {'date_from', 'total', 'per_symbol': {SYM: {...}}, 'stories': [...] }"""
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    hours_back = (
        int(cfg.get("sweep_hours_back", 24)) if hours_back is None else hours_back
    )
    limit = int(cfg.get("sweep_limit", 100)) if limit is None else limit

    date_from = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime(
        "%Y-%m-%d"
    )
    stories = aggregate_news(symbols_csv, limit, date_from)

    filt = SentimentFilter()  # uses YAML defaults + lexicon
    per_symbol: Dict[str, Dict[str, Any]] = {}
    out_stories: List[Dict[str, Any]] = []

    watch = {s.strip().upper() for s in symbols_csv.split(",") if s.strip()}
    for s in stories:
        syms = [
            (x.get("name") or "").upper()
            for x in s.get("stocks", [])
            if (x.get("name") or "").strip()
        ]
        # If provider omitted stocks, try to derive from title (best-effort) or skip
        in_watch = [sym for sym in syms if sym in watch]
        if not in_watch:
            continue
        title = s.get("title", "")
        score = filt.score(title)
        allow = filt.allow_trade(title, side=side, precomputed_score=score)
        rec = {
            "created": s.get("created"),
            "title": title,
            "score": round(score, 4),
            "allow": bool(allow),
            "url": s.get("url"),
            "symbols": in_watch,
            "source": s.get("source", ""),
        }
        out_stories.append(rec)
        for sym in in_watch:
            d = per_symbol.setdefault(
                sym, {"seen": 0, "allowed": 0, "blocked": 0, "avgScore": 0.0}
            )
            d["seen"] += 1
            if allow:
                d["allowed"] += 1
            else:
                d["blocked"] += 1
            d["avgScore"] += score

    for sym, d in per_symbol.items():
        if d["seen"] > 0:
            d["avgScore"] = round(d["avgScore"] / d["seen"], 4)

    return {
        "date_from": date_from,
        "total": len(out_stories),
        "per_symbol": per_symbol,
        "stories": out_stories,
    }
