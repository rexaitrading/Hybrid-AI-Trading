from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard

def main():
    # Kraken data + Kraken broker; still virtual_fills=True (no keys needed)
    cfg = RunnerConfig(exchange="kraken", symbol="ETH/USD", broker="kraken", virtual_fills=True)
    logger = TradeLogger()
    risk = RiskManager()
    kelly = KellySizer()
    bsg = BlackSwanGuard()
    r = ETH1HRunner(cfg, risk, kelly, bsg, logger)
    ev = r.step()
    if ev:
        print("Trade filled:", ev)

if __name__ == "__main__":
    main()