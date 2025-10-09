from ib_insync import IB, Stock, LimitOrder
import os

ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"),
           int(os.getenv("IB_PORT","4002")),
           int(os.getenv("IB_CLIENT_ID","901")), timeout=15)

contract = Stock("AAPL","SMART","USD")
ib.qualifyContracts(contract)

order = LimitOrder("BUY", 1, 100.00)  # no whatIf flag here
state = ib.whatIfOrder(contract, order)

print("whatIf.status:", getattr(state, "status", None))
print("commission:", getattr(state, "commission", None), getattr(state, "commissionCurrency", ""))
print("min/max commission:", getattr(state, "minCommission", None), getattr(state, "maxCommission", None))
print("equityWithLoanChange:", getattr(state, "equityWithLoanChange", None))
print("initMarginChange:", getattr(state, "initMarginChange", None))
print("maintMarginChange:", getattr(state, "maintMarginChange", None))
ib.disconnect()