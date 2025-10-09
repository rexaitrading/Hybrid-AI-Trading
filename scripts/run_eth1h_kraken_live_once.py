import os
from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager, RiskConfig
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.execution.brokers import KrakenClient

# Safety: micro size + notional cap + no shorts
cfg = RunnerConfig(
    exchange="kraken",
    symbol="ETH/CAD",          # Kraken uses USD (not USDT)
    broker="kraken",
    virtual_fills=False,       # LIVE route
    allow_shorts=False,
    base_capital=25.0,         # micro notional basis
    kelly_fraction=0.5,
    fee_bps=26.0,              # conservative total fees for Kraken tier
    slip_bps=5.0,
    time_stop_bars=1
)

# Risk caps (stop any >$50 trade)
risk = RiskManager(RiskConfig(
    per_trade_notional_cap=50.0,
    max_trades_per_day=1
))

logger = TradeLogger()         # logs/trades.jsonl, trades.csv, trades.log
kelly  = KellySizer()
bsg    = BlackSwanGuard()

r = ETH1HRunner(cfg, risk, kelly, bsg, logger)

# Inject keys into the Kraken broker (runnerâ€™s factory creates a plain client)
key = os.getenv("KRAKEN_KEY","")
sec = os.getenv("KRAKEN_SECRET","")
r.broker = KrakenClient(api_key=key, secret=sec)

# One step: use FORCE_TRADE to control direction (BUY/SELL), or let alpha decide
force = os.getenv("FORCE_TRADE","").upper()
ev = r.step()
print("Result:", ev)
