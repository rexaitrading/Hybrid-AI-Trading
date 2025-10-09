from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard

def main():
    cfg = RunnerConfig(virtual_fills=True)  # safe mode; flip when ready
    logger = TradeLogger()
    risk = RiskManager()
    kelly = KellySizer()
    bsg = BlackSwanGuard()
    runner = ETH1HRunner(cfg, risk, kelly, bsg, logger)
    ev = runner.step()
    if not ev:
        return  # quiet on no-trade; runner prints fills/reasons

if __name__ == "__main__":
    main()