PROVIDER QoS LEDGER (JSONL)  v1

File:
- logs/provider_qos.jsonl  (UTF-8 no-BOM, one JSON object per line)

Schema (per line):
{
  "ts_utc": "2025-12-26T00:00:00Z",
  "provider": "IBKR|TMX|QuoteMedia|Barchart|Benzinga|Kraken|Coinbase|OANDA|Polygon|CoinAPI|CryptoCompare",
  "channel": "realtime|scanner|backfill|news|execution|fx|crypto",
  "symbol": "NVDA|SPY|QQQ|RY.TO|...",
  "latency_ms_p50": 0,
  "latency_ms_p95": 0,
  "error_rate_1m": 0.0,
  "freshness_ms": 0,
  "throttle_hits_1m": 0,
  "ok": true,
  "notes": ""
}

Policy (default gates):
- freshness_ms <= 3000 for realtime channels
- error_rate_1m <= 0.02
- latency_ms_p95 <= 500
These are conservative defaults; tune per provider.