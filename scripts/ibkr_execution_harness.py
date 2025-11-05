"""
IBKR Execution Harness (Quant Pro v7.0 Ã¢â‚¬â€œ Hedge Fund Level)
----------------------------------------------------------
Responsibilities:
- Connect to IBKR TWS / Gateway (paper/live configurable)
- Submit bracket orders (entry + stop-loss + take-profit)
- Enforce RiskManager pre-checks before sending orders
- Log all trades to console and SQLite audit DB
- Disconnect cleanly and safely
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from ib_insync import IB, LimitOrder, MarketOrder, Stock, Trade

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("IBKRExecHarness")


# ---------------------------------------------------------------------
# RiskManager (simplified hook)
# ---------------------------------------------------------------------
class RiskManager:
    """Basic risk checks (placeholder for full hybrid_ai_trading.risk)."""

    def __init__(self, max_qty: int = 1000, max_order_value: float = 100_000):
        self.max_qty = max_qty
        self.max_order_value = max_order_value

    def approve(self, symbol: str, qty: int, price: float) -> bool:
        """Approve or reject trade based on basic limits."""
        if qty > self.max_qty:
            logger.error("Ã¢ÂÅ’ Risk breach: qty %d > max %d", qty, self.max_qty)
            return False
        if qty * price > self.max_order_value:
            logger.error(
                "Ã¢ÂÅ’ Risk breach: order value %.2f > max %.2f",
                qty * price,
                self.max_order_value,
            )
            return False
        logger.info("Ã¢Å“â€¦ Risk check passed for %s %d @ %.2f", symbol, qty, price)
        return True


# ---------------------------------------------------------------------
# SQLite Audit Logger
# ---------------------------------------------------------------------
class AuditLogger:
    """Persist all orders to SQLite for audit trail."""

    def __init__(self, db_path: str = "trades_audit.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                qty INTEGER,
                entry REAL,
                stop REAL,
                target REAL,
                status TEXT
            )"""
        )
        self.conn.commit()

    def log_trade(
        self,
        symbol: str,
        side: str,
        qty: int,
        entry: float,
        stop: float,
        target: float,
        status: str,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO trades VALUES (NULL,?,?,?,?,?,?,?,?)",
            (
                datetime.utcnow().isoformat(),
                symbol,
                side,
                qty,
                entry,
                stop,
                target,
                status,
            ),
        )
        self.conn.commit()


# ---------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------
def main(
    symbol: str = "AAPL",
    qty: int = 10,
    side: str = "BUY",
    entry_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    target_price: Optional[float] = None,
    client_id: int = 1,
    port: int = 7497,
) -> None:
    """Submit a bracket order with risk checks + audit logging."""

    ib = IB()
    audit = AuditLogger()
    risk = RiskManager()

    try:
        # Connect (7497=paper, 7496=live)
        ib.connect("127.0.0.1", port, clientId=client_id)
        logger.info("Ã¢Å“â€¦ Connected to IBKR (port=%d, clientId=%d)", port, client_id)

        # Define contract
        contract = Stock(symbol, "SMART", "USD")

        # Market entry or limit entry
        order = (
            LimitOrder(side, qty, entry_price)
            if entry_price
            else MarketOrder(side, qty)
        )

        # Risk check
        last_price = ib.reqMktData(contract, "", False, False).last or entry_price or 0
        if not risk.approve(symbol, qty, last_price):
            logger.error("Ã¢ÂÅ’ Trade blocked by RiskManager")
            return

        # Place entry order
        trade: Trade = ib.placeOrder(contract, order)
        logger.info("Ã°Å¸Å¡â‚¬ Entry submitted: %s %d %s", side, qty, symbol)

        # Attach stop-loss + target if given
        if stop_price and target_price:
            bracket = ib.bracketOrder(
                side, qty, entry_price or last_price, target_price, stop_price
            )
            for o in bracket:
                ib.placeOrder(contract, o)
            logger.info(
                "Ã°Å¸â€œÅ  Bracket placed: stop=%.2f target=%.2f",
                stop_price,
                target_price,
            )

        # Wait for updates
        ib.sleep(5)
        status = trade.orderStatus.status
        logger.info("Ã°Å¸â€œË† Final order status: %s", status)

        # Audit log
        audit.log_trade(
            symbol,
            side,
            qty,
            entry_price or last_price,
            stop_price or 0.0,
            target_price or 0.0,
            status,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("Ã¢ÂÅ’ Error: %s", e)
    finally:
        if ib.isConnected():
            ib.disconnect()
            logger.info("Ã°Å¸â€Å’ Disconnected from IBKR")


# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Example run
    main(
        symbol="AAPL",
        qty=10,
        side="BUY",
        entry_price=None,  # Market
        stop_price=170.0,
        target_price=200.0,
    )
