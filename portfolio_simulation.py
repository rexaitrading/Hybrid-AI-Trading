import base64
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from io import BytesIO

import ccxt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from polygon import RESTClient
from scipy.optimize import minimize

# --- Load Config ---
with open("portfolio_config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

TICKERS = cfg.get("tickers", [])
START_DATE = cfg.get("start", "2020-01-01")
END_DATE = cfg.get("end", datetime.today().strftime("%Y-%m-%d"))
REBALANCE = cfg.get("rebalance", "daily")
RISK_FREE = cfg.get("risk_free_rate", 0.0)

EMAIL_FROM = cfg.get("email_from")
EMAIL_TO = cfg.get("email_to")
SMTP_USER = cfg.get("smtp_user")
SMTP_PASS = cfg.get("smtp_pass")  # Must be a Gmail App Password
SMTP_HOST = cfg.get("smtp_host", "smtp.gmail.com")
SMTP_PORT = cfg.get("smtp_port", 587)

print(
    "ðŸ“„ Config loaded:",
    TICKERS,
    START_DATE,
    END_DATE,
    f"Rebalance={REBALANCE}, RF={RISK_FREE}",
)

# --- Global Clients ---
polygon_key = os.getenv("POLYGON_KEY") or cfg.get("polygon_key")
if not polygon_key:
    raise RuntimeError(
        "âŒ Missing Polygon API key. Set POLYGON_KEY in env or in portfolio_config.yaml"
    )

_binance = ccxt.binance()
_polygon_client = RESTClient(polygon_key)


# --- Helpers ---
def plot_to_base64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def send_email(subject, body, attachments=None):
    """Send email with attachments via SMTP, skip missing files gracefully."""
    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg["Subject"] = subject
        msg.set_content(body)

        if attachments:
            for fname in attachments:
                if not os.path.exists(fname):
                    print(f"âš ï¸ Missing attachment, skipping: {fname}")
                    continue
                with open(fname, "rb") as f:
                    data = f.read()
                msg.add_attachment(
                    data,
                    maintype="application",
                    subtype="octet-stream",
                    filename=os.path.basename(fname),
                )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        print(f"ðŸ“§ Email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"âŒ Email sending failed: {e}")


# --- Data Fetchers ---
def fetch_crypto(symbol: str, start_date: str) -> pd.DataFrame:
    try:
        print(f"ðŸ”— Fetching crypto {symbol} from Binance...")
        ohlcv = _binance.fetch_ohlcv(
            symbol, timeframe="1d", since=_binance.parse8601(start_date + "T00:00:00Z")
        )
        df = pd.DataFrame(
            ohlcv, columns=["ts", "open", "high", "low", "close", "volume"]
        )
        df["date"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("date", inplace=True)
        df["returns"] = np.log(df["close"] / df["close"].shift(1))
        return df[["close", "returns"]]
    except Exception as e:
        print(f"âŒ Failed to fetch crypto {symbol}: {e}")
        return pd.DataFrame()


def fetch_polygon(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch daily OHLCV from Polygon (works for stocks, ETFs, IPOs, and forex)."""
    try:
        print(f"ðŸ”— Fetching {symbol} from Polygon...")
        bars = _polygon_client.get_aggs(
            ticker=symbol, multiplier=1, timespan="day", from_=start_date, to=end_date
        )

        if not bars or not getattr(bars, "results", None):
            print(f"âš ï¸ No data returned for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(bars.results)
        df.rename(
            columns={
                "t": "ts",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
            },
            inplace=True,
        )
        df["date"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("date", inplace=True)
        df["returns"] = np.log(df["close"] / df["close"].shift(1))
        return df[["close", "returns"]]

    except Exception as e:
        print(f"âŒ Failed to fetch {symbol} from Polygon: {e}")
        return pd.DataFrame()


# --- Portfolio Simulation ---
def simulate_portfolio(weights, returns_df, rebalance="daily"):
    weights = pd.Series(weights, index=returns_df.columns)
    daily_returns = (returns_df * weights).sum(axis=1).dropna()

    if rebalance == "weekly":
        daily_returns = (
            daily_returns.resample("W-MON").mean().reindex(returns_df.index).ffill()
        )
    elif rebalance == "monthly":
        daily_returns = (
            daily_returns.resample("M").mean().reindex(returns_df.index).ffill()
        )

    port_cum = (1 + daily_returns).cumprod()
    ann_return = daily_returns.mean() * 252
    ann_vol = daily_returns.std() * np.sqrt(252)
    sharpe = (ann_return - RISK_FREE) / ann_vol if ann_vol > 0 else 0
    downside = daily_returns[daily_returns < 0]
    sortino = (
        (ann_return - RISK_FREE) / (downside.std() * np.sqrt(252))
        if not downside.empty
        else None
    )
    max_dd = (port_cum / port_cum.cummax() - 1).min()
    calmar = ann_return / abs(max_dd) if max_dd != 0 else None
    var95 = daily_returns.quantile(0.05)
    cvar95 = daily_returns[daily_returns <= var95].mean()

    return {
        "Ann_Return": ann_return,
        "Ann_Volatility": ann_vol,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Calmar": calmar,
        "VaR_95": var95,
        "CVaR_95": cvar95,
        "Max_Drawdown": max_dd,
        "Cumulative": port_cum,
        "DailyReturns": daily_returns,
    }


# --- Optimizer ---
def optimize_portfolio(returns_df, max_alloc=0.5, min_alloc=0.05):
    n_assets = len(returns_df.columns)
    x0 = np.repeat(1 / n_assets, n_assets)
    bounds = [(min_alloc, max_alloc)] * n_assets
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1}

    res = minimize(
        lambda w: -simulate_portfolio(w, returns_df, REBALANCE)["Sharpe"],
        x0,
        bounds=bounds,
        constraints=cons,
        method="SLSQP",
    )
    if not res.success:
        raise RuntimeError("Portfolio optimization failed:", res.message)
    return res.x


# --- Report Generator ---
def generate_report_html(opt_metrics, opt_w, tickers, html_file):
    html = "<h1>Portfolio Report</h1>"
    html += (
        pd.DataFrame([opt_metrics])
        .drop(columns=["Cumulative", "DailyReturns"])
        .to_html()
    )

    # Equity curve
    fig, ax = plt.subplots(figsize=(8, 4))
    opt_metrics["Cumulative"].plot(ax=ax, title="Equity Curve")
    ax.set_ylabel("Portfolio Value")
    html += (
        f"<h2>Equity Curve</h2><img src='data:image/png;base64,{plot_to_base64(fig)}'>"
    )
    plt.close(fig)

    # Drawdown
    fig, ax = plt.subplots(figsize=(8, 4))
    dd = opt_metrics["Cumulative"] / opt_metrics["Cumulative"].cummax() - 1
    dd.plot(ax=ax, title="Drawdown")
    ax.set_ylabel("Drawdown")
    html += f"<h2>Drawdown</h2><img src='data:image/png;base64,{plot_to_base64(fig)}'>"
    plt.close(fig)

    # Portfolio Weights
    fig, ax = plt.subplots(figsize=(6, 6))
    weights = pd.Series(opt_w, index=tickers)
    weights.plot.pie(ax=ax, autopct="%.1f%%", title="Portfolio Weights")
    html += f"<h2>Optimal Weights</h2><img src='data:image/png;base64,{plot_to_base64(fig)}'>"
    plt.close(fig)

    with open(html_file, "w") as f:
        f.write(html)


# --- Main Execution ---
if __name__ == "__main__":
    assets = {}
    for ticker in TICKERS:
        if "/" in ticker:
            df = fetch_crypto(ticker, START_DATE)
        else:
            df = fetch_polygon(ticker, START_DATE, END_DATE)
        if not df.empty:
            assets[ticker] = df
        else:
            print(f"âš ï¸ Skipping {ticker} (no data)")

    if not assets:
        raise RuntimeError("âŒ No asset data available. Check APIs/keys.")

    combined = pd.concat([df["returns"].rename(t) for t, df in assets.items()], axis=1)
    combined = combined.reindex(pd.date_range(START_DATE, END_DATE, freq="B")).ffill()

    opt_w = optimize_portfolio(combined, max_alloc=0.5, min_alloc=0.05)
    opt_metrics = simulate_portfolio(opt_w, combined, REBALANCE)

    print(
        "â­ Optimal Weights:",
        dict(zip(combined.columns, [round(w * 100, 2) for w in opt_w])),
    )
    print(
        "ðŸ“Š Optimal Metrics:",
        {
            k: round(v, 4)
            for k, v in opt_metrics.items()
            if isinstance(v, (int, float, np.floating))
        },
    )

    # --- Save reports safely ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    REPORT_DIR = "reports"
    os.makedirs(REPORT_DIR, exist_ok=True)

    xlsx_file = os.path.join(REPORT_DIR, f"portfolio_report_{ts}.xlsx")
    html_file = os.path.join(REPORT_DIR, f"portfolio_report_{ts}.html")

    with pd.ExcelWriter(xlsx_file) as writer:
        combined.to_excel(writer, sheet_name="Returns")
        pd.DataFrame([opt_metrics]).drop(
            columns=["Cumulative", "DailyReturns"]
        ).to_excel(writer, sheet_name="Metrics")

    generate_report_html(opt_metrics, opt_w, combined.columns, html_file)

    print(f"ðŸ“‚ Reports saved: {xlsx_file} & {html_file}")

    # --- Email them ---
    send_email(
        subject="Portfolio Report",
        body="Attached are the latest portfolio reports.",
        attachments=[xlsx_file, html_file],
    )
