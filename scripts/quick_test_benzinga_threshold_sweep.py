"""
Quick Threshold Sweep (per-symbol fetch, YAML-driven)
- Reads: sentiment_filter_sweep, sweep_symbols, sweep_hours_back, sweep_limit from config/config.yaml
- For each watch symbol: fetch news independently, tag _source_symbol, dedupe by id
- If Benzinga omits "stocks", fall back to the _source_symbol so watch-filter still works
- Uses precomputed_score to avoid double-smoothing drift
- Prints per-symbol stats
"""
import yaml
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from hybrid_ai_trading.data.news_aggregator import aggregate_news
from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter

# Load config
with open("config/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}

sweep_cfg   = cfg.get("sentiment_filter_sweep", [])
symbols_str = cfg.get("sweep_symbols", "")
hours_back  = int(cfg.get("sweep_hours_back", 48))
limit_total = int(cfg.get("sweep_limit", 200))

watch = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
watch_set = set(watch)
if not sweep_cfg:
    sweep_cfg = [
        {"threshold": 0.60, "neutral_zone": 0.25, "smoothing": 3},
        {"threshold": 0.65, "neutral_zone": 0.25, "smoothing": 3},
        {"threshold": 0.70, "neutral_zone": 0.20, "smoothing": 3},
    ]

date_from = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%d")

# Per-symbol fetch & dedupe
c = BenzingaClient()
per_sym_limit = max(3, int(round(limit_total / max(1,len(watch)))))
stories = []
seen = set()
for sym in watch:
    batch = c.get_news(sym, limit=per_sym_limit, date_from=date_from)
    for it in batch:
        sid = str(it.get("id"))
        if sid in seen:
            continue
        it["_source_symbol"] = sym
        stories.append(it)
        seen.add(sid)

print("\n=== Sentiment Filter Parameter Sweep (YAML-driven, per-symbol fetch) ===\n")
print(f"Watch set ({len(watch_set)}): {', '.join(watch)}")
print(f"Lookback: {hours_back}h | TotalLimit: {limit_total} | PerSymbolLimit: {per_sym_limit} | date_from={date_from}\n")
print(f"Fetched unique stories: {len(stories)}\n")

for params in sweep_cfg:
    f = SentimentFilter(
        model="vader",
        threshold=params.get("threshold", 0.6),
        neutral_zone=params.get("neutral_zone", 0.25),
        smoothing=params.get("smoothing", 3),
    )
    allowed_count = blocked_count = skipped = 0
    sym_allowed = defaultdict(int)
    sym_blocked = defaultdict(int)
    sym_score_sum = defaultdict(float)
    sym_score_cnt = defaultdict(int)

    print(f"\n--- Config: threshold={params['threshold']} | neutral_zone={params['neutral_zone']} | smoothing={params.get('smoothing',3)} ---")

    for s in stories:
        tagged = [ (x.get("name") or "").upper() for x in s.get("stocks", []) if (x.get("name") or "").strip() ]
        if not tagged:
            tagged = [s.get("_source_symbol","").upper()]
        in_watch = [sym for sym in tagged if sym in watch_set]
        if not in_watch:
            skipped += 1
            continue

        title = s.get("title","")
        sc = f.score(title)
        allowed = f.allow_trade(title, side="BUY", precomputed_score=sc)

        for sym in in_watch:
            sym_score_sum[sym] += sc
            sym_score_cnt[sym] += 1
            if allowed:
                sym_allowed[sym] += 1
            else:
                sym_blocked[sym] += 1

        if allowed:
            allowed_count += 1
            status = "ALLOW "
        else:
            blocked_count += 1
            status = "BLOCK "

        print(f"[{s.get('created')}] {title} ({','.join(in_watch)}) | Score={sc:.2f} | {status}")

    total = allowed_count + blocked_count
    pct_allowed = (allowed_count / total * 100) if total > 0 else 0
    print(f"\nSummary: Allowed={allowed_count}, Blocked={blocked_count}, Skipped(non-watch)={skipped}, Allowed%={pct_allowed:.1f}%")

    if sym_score_cnt:
        print("\nPer-symbol summary:")
        for sym in sorted(sym_score_cnt):
            cnt = sym_score_cnt[sym]
            avg = sym_score_sum[sym] / cnt
            a = sym_allowed[sym]
            b = sym_blocked[sym]
            print(f"  {sym}: seen={cnt}, avgScore={avg:.2f}, allowed={a}, blocked={b}")

print("\n=== End of Sweep ===\n")