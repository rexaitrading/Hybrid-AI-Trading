import sys

import yaml

cfg_path = "config/config.yaml"
hours_back = int(sys.argv[1])
limit = int(sys.argv[2])

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}

# Ensure sentiment_filter defaults (don't clobber if set)
sf = cfg.get("sentiment_filter") or {}
sf.setdefault("threshold", 0.60)
sf.setdefault("neutral_zone", 0.25)
sf.setdefault("smoothing", 3)
cfg["sentiment_filter"] = sf

# Horizon for gate
cfg["sweep_hours_back"] = hours_back
cfg["sweep_limit"] = limit

# Providers: enable Benzinga + Polygon + RSS
np = cfg.get("news_providers") or {}
np["aggregate"] = True
np["benzinga"] = {
    "enabled": True,
    "weight": float(np.get("benzinga", {}).get("weight", 1.0)),
}
np["polygon"] = {
    "enabled": True,
    "weight": float(np.get("polygon", {}).get("weight", 1.0)),
}
rss = np.get("rss") or {}
rss["enabled"] = True
rss["per_feed_max"] = int(rss.get("per_feed_max", 8))
rss["google_template"] = (
    rss.get("google_template")
    or "https://news.google.com/rss/search?q={sym}+stock&hl=en-US&gl=US&ceid=US:en"
)
rss["yahoo_template"] = (
    rss.get("yahoo_template")
    or "https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&lang=en-US"
)
rss["extra_feeds"] = rss.get("extra_feeds") or []
np["rss"] = rss

# Leave alpaca/kraken/cme as-is (optional later)
cfg["news_providers"] = np

with open(cfg_path, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)
print(
    f"UPDATED: sweep_hours_back={hours_back}, sweep_limit={limit}, providers: benzinga/polygon/rss enabled"
)
