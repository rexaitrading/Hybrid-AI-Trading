from __future__ import annotations

import json
import sys
from pathlib import Path

from hybrid_ai_trading.providers.crypto_router import ProviderHealth, choose_crypto_provider


def _load_latest_entry(path: Path, provider_name: str):
    if not path.exists():
        print(f"[QoS Gate] No QoS file for {provider_name} at {path}")
        return None

    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        print(f"[QoS Gate] Empty QoS file for {provider_name} at {path}")
        return None

    try:
        entries = [json.loads(ln) for ln in lines]
    except json.JSONDecodeError as exc:
        print(f"[QoS Gate] Invalid JSON in {path}: {exc}")
        return None

    entries = [e for e in entries if e.get("provider") == provider_name or provider_name in str(e.get("provider"))]
    if not entries:
        print(f"[QoS Gate] No entries for {provider_name} in {path}")
        return None

    return entries[-1]


def _health_from_entry(name: str, entry: dict | None) -> ProviderHealth:
    if entry is None:
        # Treat as unhealthy but not fatal by itself
        return ProviderHealth(
            name=name,
            ok=False,
            latency_s=999.0,
            status_code=None,
            freshness_s=999.0,
        )

    return ProviderHealth(
        name=name,
        ok=bool(entry.get("ok", False)),
        latency_s=float(entry.get("latency_s", 999.0)),
        status_code=entry.get("status_code"),
        freshness_s=0.0,  # could compute from ts vs now if needed
    )


def main() -> int:
    base = Path("logs") / "providers"

    coinbase_entry = _load_latest_entry(base / "coinbase_qos.jsonl", "coinbase")
    kraken_entry = _load_latest_entry(base / "kraken_qos.jsonl", "kraken")

    kraken = _health_from_entry("kraken_primary", kraken_entry)
    coinbase = _health_from_entry("coinbase_backup", coinbase_entry)

    print("=== Crypto QoS Gate ===")
    print("Kraken health:", kraken)
    print("Coinbase health:", coinbase)

    if not kraken.ok and not coinbase.ok:
        print("[QoS Gate] Both Kraken and Coinbase are unhealthy or missing QoS. Failing gate.")
        return 1

    try:
        choice = choose_crypto_provider(kraken, coinbase)
    except Exception as exc:
        print(f"[QoS Gate] Router raised exception: {exc!r}")
        return 1

    print(f"[QoS Gate] Router choice from QoS: {choice}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())