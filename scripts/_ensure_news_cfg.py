import yaml, os
p="config/config.yaml"
with open(p,"r",encoding="utf-8") as f:
    cfg=yaml.safe_load(f) or {}

np = cfg.get("news_providers") or {}

# Enable core sources; you can toggle in YAML later
np.setdefault("aggregate", True)
np.setdefault("benzinga", {"enabled": True,  "weight": 1.0})
np.setdefault("polygon",  {"enabled": True,  "weight": 1.0})
np.setdefault("alpaca",   {"enabled": False, "weight": 1.0})  # turn on when ALPACA keys ready
np.setdefault("ibkr",     {"enabled": False})                  # placeholder for future IB news
np.setdefault("coinapi",  {"enabled": False})                  # (CoinAPI is price data; no standard news)
# RSS bundle (Google/Yahoo templates + extra feeds)
np.setdefault("rss", {
    "enabled": True,
    "per_feed_max": 8,
    "google_template": "https://news.google.com/rss/search?q={sym}+stock&hl=en-US&gl=US&ceid=US:en",
    "yahoo_template":  "https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&lang=en-US",
    "extra_feeds": []
})
# Optional vendor-specific RSS sets you can extend
np.setdefault("kraken_rss", {
    "enabled": False,
    "feeds": ["https://blog.kraken.com/feed", "https://status.kraken.com/history.atom"]
})
np.setdefault("cme_rss", {
    "enabled": False,
    "feeds": ["https://www.cmegroup.com/rss/feeds/press-releases.xml"]
})

cfg["news_providers"] = np

# Ensure env mapping includes ALPACA + OPENAI (for future summarizer if you want)
prov = cfg.get("providers") or {}
alp = prov.get("alpaca") or {}
alp.setdefault("key_id_env","ALPACA_KEY_ID")
alp.setdefault("secret_key_env","ALPACA_SECRET_KEY")
prov["alpaca"] = alp
prov.setdefault("openai", {"api_key_env":"OPENAI_API_KEY"})
cfg["providers"] = prov

with open(p,"w",encoding="utf-8") as f:
    yaml.safe_dump(cfg,f,sort_keys=False)
print("NEWS_PROVIDERS_UPDATED")