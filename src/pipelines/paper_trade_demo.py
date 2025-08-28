# src/pipelines/paper_trade_demo.py
from datetime import datetime
from src.signals.breakout_v1 import breakout_signal

def run_demo():
    sig = breakout_signal("BITSTAMP_SPOT_BTC_USD")
    print(f"[{datetime.utcnow()}] Breakout signal: {sig}")

if __name__ == "__main__":
    run_demo()
