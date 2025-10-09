"""
Market Logger (Hybrid AI Quant Pro v8.2 – OE Hedge-Fund Grade, Polished)
------------------------------------------------------------------------
Responsibilities:
- Connect to IBKR TWS/Gateway
- Subscribe to live market data for selected symbols
- Log ticks to CSV with timestamp
- Structured logging & graceful shutdown
- Robust error handling for production use
"""

import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from ib_insync import IB, Stock
except ImportError:  # fallback if ib_insync not installed
    IB = None
    Stock = None

logger = logging.getLogger("hybrid_ai_trading.execution.market_logger")
logger.setLevel(logging.INFO)


class MarketLogger:
    """Log live ticks from IBKR into CSV files."""

    def __init__(self, symbols: List[str], outdir: str = "market_logs") -> None:
        if IB is None or Stock is None:
            raise ImportError(
                "ib_insync is required for MarketLogger. "
                "Install with `pip install ib-insync`."
            )

        self.symbols = symbols
        self.outdir = Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)

        self.ib: Optional[IB] = None
        self.subscriptions: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
    ) -> None:
        """Connect to IBKR TWS/Gateway."""
        try:
            self.ib = IB()
            self.ib.connect(host, port, clientId=client_id)
            logger.info("✅ Connected to IBKR at %s:%d", host, port)
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Failed to connect to IBKR: %s", exc)
            raise RuntimeError("IBKR connection failed") from exc

    # ------------------------------------------------------------------
    def start_logging(self) -> None:
        """Subscribe to tickers and log to CSV."""
        if not self.ib:
            raise RuntimeError("IBKR not connected. Call connect() first.")

        for symbol in self.symbols:
            try:
                contract = Stock(symbol, "SMART", "USD")
                ticker = self.ib.reqMktData(contract)
                self.subscriptions[symbol] = ticker

                csv_file = self.outdir / f"{symbol}_ticks.csv"
                fhandle = open(csv_file, "a", newline="", encoding="utf-8")
                writer = csv.writer(fhandle)

                # ✅ Ensure header exists
                if csv_file.stat().st_size == 0:
                    writer.writerow(["timestamp", "symbol", "last", "bid", "ask"])

                def log_tick(ticker=ticker, sym=symbol, writer=writer) -> None:
                    try:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        price = getattr(ticker, "last", "") or ""
                        bid = getattr(ticker, "bid", "") or ""
                        ask = getattr(ticker, "ask", "") or ""
                        writer.writerow([ts, sym, price, bid, ask])
                        fhandle.flush()
                        logger.debug(
                            "Tick logged | %s %s last=%s bid=%s ask=%s",
                            ts,
                            sym,
                            price,
                            bid,
                            ask,
                        )
                    except Exception as err:  # noqa: BLE001
                        logger.error("❌ Failed to log tick for %s: %s", sym, err)

                ticker.updateEvent += log_tick
            except Exception as exc:  # noqa: BLE001
                logger.error("❌ Subscription failed for %s: %s", symbol, exc)

        logger.info("🚀 Market logging started for: %s", ", ".join(self.symbols))
        try:
            self.ib.run()
        except KeyboardInterrupt:
            logger.info("🛑 Interrupted by user. Shutting down...")
            self.shutdown()
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ Market logging stopped unexpectedly: %s", exc)
            self.shutdown()

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        """Cancel subscriptions and disconnect gracefully."""
        if self.ib:
            for sym, ticker in list(self.subscriptions.items()):
                try:
                    self.ib.cancelMktData(ticker.contract)
                    logger.info("❌ Unsubscribed from %s", sym)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("⚠️ Failed to unsubscribe %s: %s", sym, exc)
            try:
                self.ib.disconnect()
                logger.info("🔌 Disconnected from IBKR")
            except Exception as exc:  # noqa: BLE001
                logger.warning("⚠️ IBKR disconnect issue: %s", exc)
            finally:
                self.ib = None
        self.subscriptions.clear()


# ----------------------------------------------------------------------
# CLI Entrypoint
# ----------------------------------------------------------------------
def main() -> None:  # pragma: no cover
    """CLI entry point for quick testing."""
    if IB is None:
        sys.exit("❌ ib_insync is not installed. Run `pip install ib-insync`.")

    symbols = ["AAPL", "TSLA"]
    logger.info("Starting MarketLogger for symbols: %s", symbols)

    mlogger = MarketLogger(symbols)
    mlogger.connect()
    mlogger.start_logging()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    main()
