from __future__ import annotations

from config.phase5_config_loader import load_phase5_ev_bands, get_ev_band_abs


def main() -> None:
    cfg = load_phase5_ev_bands()
    print("Loaded keys:", sorted(cfg.keys()))

    for regime in ["NVDA_BPLUS_LIVE", "SPY_ORB_LIVE", "QQQ_ORB_LIVE"]:
        band = get_ev_band_abs(regime, cfg, default=None)
        print(regime, "-> ev_band_abs =", band)


if __name__ == "__main__":
    main()