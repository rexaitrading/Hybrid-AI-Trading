from ib_insync import *

# Connect to TWS / Gateway (Paper: 7497, Live: 7496)
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Define contract (AAPL stock)
contract = Stock('AAPL', 'SMART', 'USD')

# Market order: buy 10 shares
order = MarketOrder('BUY', 10)

# Place the order
trade = ib.placeOrder(contract, order)
print("Order submitted:", trade)

# Wait for execution updates
ib.sleep(5)
print("Order status:", trade.orderStatus.status)

ib.disconnect()
