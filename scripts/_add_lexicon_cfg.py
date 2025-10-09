import yaml

p = "config/config.yaml"
with open(p, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}

lex = cfg.get("sentiment_lexicon")
if not lex:
    lex = {
        "boost_terms": [
            "beats",
            "beat estimates",
            "raises guidance",
            "record profit",
            "contract win",
            "upgrade",
            "approval",
            "fda approval",
            "accelerating growth",
        ],
        "block_terms": [
            "trading halt",
            "halted",
            "bankruptcy",
            "chapter 11",
            "recall",
            "sec probe",
            "data breach",
            "fraud investigation",
        ],
        "boost_value": 0.05,
        "block_value": -0.05,
        "case_sensitive": False,
    }
    cfg["sentiment_lexicon"] = lex
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print("LEXICON_ADDED")
else:
    print("LEXICON_EXISTS")
