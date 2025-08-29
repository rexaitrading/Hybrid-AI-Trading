# 🚀 Hybrid AI Trading

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

