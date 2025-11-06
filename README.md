<p align="left">
  <a href="https://github.com/rexaitrading/Hybrid-AI-Trading/actions/workflows/risk_nightly.yml">
    <img src="https://github.com/rexaitrading/Hybrid-AI-Trading/actions/workflows/risk_nightly.yml/badge.svg" alt="Risk Nightly (non-IB)">
  </a>
</p>


# Ã°Å¸Å¡â‚¬ Hybrid AI Trading

![Python](https://img.shields.io/badge/python-3.12-blue)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-private-lightgrey)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)

AI-driven trading system with **hybrid strategies** and **multi-asset integration** (equities, futures, forex, crypto).
Includes **risk management modules**, **backtesting pipelines**, and **interactive broker connectivity**.

---

## Ã°Å¸â€œÅ’ Overview
This project is a **Hybrid AI Aggressive High-Performance Trading System**.
It combines **quantitative trading**, **AI signals**, and **multi-broker execution** into one pipeline:

- Ã°Å¸â€œË† **Equities** via Polygon + Interactive Brokers (IBKR)
- Ã°Å¸â€œÅ  **Futures** via EdgeClear (Rithmic)
- Ã°Å¸â€™Â± **Forex** via OANDA
- Ã¢â€šÂ¿ **Crypto** via CCXT (Binance, Bybit, Kraken)
- Ã°Å¸â€œÂ° **News/Sentiment** via Benzinga Pro & Dow Jones / LSEG
- Ã¢ËœÂÃ¯Â¸Â **Infrastructure** on AWS/GCP for 24/7 execution

Built for **day trading** with a focus on **1Ã¢â‚¬â€œ2% daily return targets** and strict **risk controls** (+1% lock, Ã¢â‚¬â€œ3% stop).

---

## Ã°Å¸â€ºÂ Ã¯Â¸Â Features
- Ã¢Å“â€¦ **Backtesting Engine** (daily & intraday strategies)
- Ã¢Å“â€¦ **Signal Modules** (breakout, anomaly detection)
- Ã¢Å“â€¦ **Risk Manager** (daily loss caps, per-trade risk, black swan guard)
- Ã¢Å“â€¦ **Broker Integrations** (IBKR, OANDA, Rithmic, CCXT)
- Ã¢Å“â€¦ **Data Feeds** (Polygon, CoinAPI, Kaiko, LSEG, Benzinga)
- Ã¢Å“â€¦ **Visualization** (equity curves, drawdowns, portfolio reports)

---

## Ã¢Å¡Â¡ Setup

Clone the repo and install dependencies:

```bash
git clone https://github.com/rexaitrading/Hybrid-AI-Trading.git
cd Hybrid-AI-Trading
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
## ORB Play-Forward Runner

[![ORB CSV SIM Smoke](https://github.com/rexaitrading/Hybrid-AI-Trading/actions/workflows/orb_sim_smoke.yml/badge.svg)](https://github.com/rexaitrading/Hybrid-AI-Trading/actions/workflows/orb_sim_smoke.yml)

**CSV SIM (no IB needed)**
```powershell
python scripts/live_orb_play_forward.py --from-csv data/AAPL_1m.csv --sim --symbol AAPL --mdt 3 --rth 0 --orb-minutes 15 --qty 100 --fees 0

```

**Live during RTH (needs data subs)**
```powershell
python scripts/live_orb_play_forward.py --symbol AAPL --primary NASDAQ --mdt 1 --rth 1 --orb-minutes 15 --qty 100 --fees 0
```

![ORB Smoke](https://github.com/rexaitrading/Hybrid-AI-Trading/actions/workflows/orb_smoke.yml/badge.svg)
