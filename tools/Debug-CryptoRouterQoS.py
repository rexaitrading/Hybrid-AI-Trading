from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from hybrid_ai_trading.providers.crypto_router import ProviderHealth, choose_crypto_provider


def load_coinbase_qos(path: Path):
    if not path.exists():
        raise SystemExit(f"[QoS] Coinbase QoS log not found at {path}")

    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise SystemExit(f"[QoS] Coinbase QoS log at {path} is empty")

    entries = [json.loads(ln) for ln in lines]
    ok_entries = [e for e in entries if e.get("ok")]

    if not ok_entries:
        raise SystemExit("[QoS] No successful Coinbase QoS entries found.")

    # Some entries may not have latency_s; filter defensively
    latencies = [e["latency_s"] for e in ok_entries if "latency_s" in e]
    if not latencies:
        raise SystemExit("[QoS] No latency_s field in successful Coinbase entries.")

    avg_latency = mean(latencies)
    last = entries[-1]

    print("=== Coinbase QoS summary ===")
    print(f"Total entries:     {len(entries)}")
    print(f"Successful entries:{len(ok_entries)}")
    print(f"Avg latency (s):   {avg_latency:.4f}")
    print(f"Last entry:        {last}")

    return avg_latency, last


def build_provider_health(avg_latency: float, last_entry: dict):
    # Match ProviderHealth signature: name, ok, latency_s, status_code, freshness_s
    coinbase = ProviderHealth(
        name="coinbase_backup",
        ok=bool(last_entry.get("ok", False)),
        latency_s=float(last_entry.get("latency_s", avg_latency)),
        status_code=last_entry.get("status_code"),
        freshness_s=float(last_entry.get("freshness_s", 0.0)),
    )

    # Example: Kraken primary is currently healthy with good latency.
    kraken = ProviderHealth(
        name="kraken_primary",
        ok=True,
        latency_s=0.12,
        status_code=200,
        freshness_s=0.05,
    )

    return kraken, coinbase


def main():
    # QoS ledger path for Coinbase (per-provider JSONL)
    qpath = Path("logs") / "providers" / "coinbase_qos.jsonl"

    avg_latency, last = load_coinbase_qos(qpath)
    kraken, coinbase = build_provider_health(avg_latency, last)

    print("\n=== Router decision test ===")
    choice = choose_crypto_provider(kraken, coinbase)
    print(f"Router choice (both healthy): {choice}")

    # Simulate Kraken going down -> router should flip to Coinbase backup
    kraken_down = ProviderHealth(
        name=kraken.name,
        ok=False,
        latency_s=kraken.latency_s,
        status_code=kraken.status_code,
        freshness_s=kraken.freshness_s,
    )

    choice_failover = choose_crypto_provider(kraken_down, coinbase)
    print(f"Router choice (kraken down):  {choice_failover}")


if __name__ == "__main__":
    main()