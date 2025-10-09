mods = ["torch", "transformers", "vaderSentiment", "ccxt", "ib_insync"]
ok, bad = [], []
for m in mods:
    try:
        __import__(m)
        ok.append(m)
    except Exception as e:
        bad.append((m, str(e)))
print("OK:", ok)
print("BAD:", bad)
