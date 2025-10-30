import csv
import datetime as dt
import os

start = dt.datetime(2024, 1, 2, 9, 30)
n = 40
rows = []
# Build a flat ORB first 15 mins, then spike high at minute 20, then drift
base = 100.0
for i in range(n):
    t = start + dt.timedelta(minutes=i)
    if i < 15:
        o = c = base + (i * 0.01)  # very tight range
    elif i == 20:
        o = c = base + 1.00  # clear breakout above ORB high
    else:
        o = c = base + 0.5 + (i - 15) * 0.02
    h = o + 0.05
    l = o - 0.05
    v = 300 + (i % 50)
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
os.makedirs("data", exist_ok=True)
with open(r"data/AAPL_1m.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
    w.writerows(rows)
print(f"wrote {len(rows)} forced-breakout rows -> data/AAPL_1m.csv")
