import os
import sys

from ib_insync import IB, LimitOrder, Stock

ib = IB()
ib.connect(
    os.getenv("IB_HOST", "127.0.0.1"),
    int(os.getenv("IB_PORT", "4002")),
    int(os.getenv("IB_CLIENT_ID", "901")),
    timeout=15,
)

# list accounts and pick the first (usually your DUxxxxxx paper account)
accounts = ib.managedAccounts()
print("accounts:", accounts)
if not accounts:
    print("No accounts returned; are you logged into PAPER in IB Gateway?")
    sys.exit(2)
acct = accounts[0]

# qualify AAPL contract
contract = Stock("AAPL", "SMART", "USD", primaryExchange="NASDAQ")
ib.qualifyContracts(contract)

# build order and set ACCOUNT explicitly
order = LimitOrder("BUY", 1, 100.00)
order.tif = "DAY"
order.account = acct

# run what-if and print details
state = ib.whatIfOrder(contract, order)


def g(o, name, default=None):
    return getattr(o, name, default)


print("whatIf.status:", g(state, "status"))
print("warningText:", g(state, "warningText"))
print("commission:", g(state, "commission"), g(state, "commissionCurrency", ""))
print(
    "minCommission/maxCommission:", g(state, "minCommission"), g(state, "maxCommission")
)
print("equityWithLoanChange:", g(state, "equityWithLoanChange"))
print("initMarginChange:", g(state, "initMarginChange"))
print("maintMarginChange:", g(state, "maintMarginChange"))

ib.disconnect()
