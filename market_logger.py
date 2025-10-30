import csv
from datetime import datetime

from ib_insync import *

ib = IB()
ib.connect("127.0.0.1", 7496, clientId=1)

ib.reqMarketDataType(3)

# Define multiple contracts
contracts = [
    Stock("AAPL", "SMART", "USD"),
    Stock("MSFT", "SMART", "USD"),
    Stock("TSLA", "SMART", "USD"),
    Stock("AMZN", "SMART", "USD"),
    Stock("GOOG", "SMART", "USD"),
]


# Subscribe to market data
tickers = [ib.reqMktData(c) for c in contracts]

# Open CSV file for logging
with open("market_data.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Time", "Symbol", "Last", "Market Price"])

    while True:
        ib.sleep(1)
        for t in tickers:
            writer.writerow(
                [datetime.now(), t.contract.symbol, t.last, t.marketPrice()]
            )
            print("Saved:", datetime.now(), t.contract.symbol, t.last, t.marketPrice())
