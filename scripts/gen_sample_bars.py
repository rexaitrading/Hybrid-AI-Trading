import csv
import datetime as dt
import os
import random

start = dt.datetime(2024, 1, 2, 9, 30)
n = 40  # >= orb_minutes + 5 (15 + 5 = 20); use 40 for headroom
price = 100.0
rows = []
random.seed(42)
for i in range(n):
    t = start + dt.timedelta(minutes=i)
    o = price
    delta = random.uniform(-0.4, 0.4)
    c = round(o + delta, 2)
    h = round(max(o, c) + abs(delta) * 0.5 + 0.03, 2)
    l = round(min(o, c) - abs(delta) * 0.5 - 0.03, 2)
    v = random.randint(100, 500)
    rows.append(
        [
            t.strftime("%Y-%m-%d %H:%M:%S"),
            f"{o:.2f}",
            f"{h:.2f}",
            f"{l:.2f}",
            f"{c:.2f}",
            v,
        ]
    )
    price = c
os.makedirs("data", exist_ok=True)
with open(r"data/AAPL_1m.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
    w.writerows(rows)
print(f"wrote {len(rows)} rows -> data/AAPL_1m.csv")
