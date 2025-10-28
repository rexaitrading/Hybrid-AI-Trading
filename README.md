

# 🚀 Hybrid AI Trading

![Python](https://img.shields.io/badge/python-3.12-blue)
![Status](https://img.shields.io/badge/status-active-success)
![License](https://img.shields.io/badge/license-private-lightgrey)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)

AI-driven trading system with **hybrid strategies** and **multi-asset integration** (equities, futures, forex, crypto).
Includes **risk management modules**, **backtesting pipelines**, and **interactive broker connectivity**.

---

## 📌 Overview
This project is a **Hybrid AI Aggressive High-Performance Trading System**.
It combines **quantitative trading**, **AI signals**, and **multi-broker execution** into one pipeline:

- 📈 **Equities** via Polygon + Interactive Brokers (IBKR)
- 📊 **Futures** via EdgeClear (Rithmic)
- 💱 **Forex** via OANDA
- ₿ **Crypto** via CCXT (Binance, Bybit, Kraken)
- 📰 **News/Sentiment** via Benzinga Pro & Dow Jones / LSEG
- ☁️ **Infrastructure** on AWS/GCP for 24/7 execution

Built for **day trading** with a focus on **1–2% daily return targets** and strict **risk controls** (+1% lock, –3% stop).

---

## 🛠️ Features
- ✅ **Backtesting Engine** (daily & intraday strategies)
- ✅ **Signal Modules** (breakout, anomaly detection)
- ✅ **Risk Manager** (daily loss caps, per-trade risk, black swan guard)
- ✅ **Broker Integrations** (IBKR, OANDA, Rithmic, CCXT)
- ✅ **Data Feeds** (Polygon, CoinAPI, Kaiko, LSEG, Benzinga)
- ✅ **Visualization** (equity curves, drawdowns, portfolio reports)

---

## ⚡ Setup

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
