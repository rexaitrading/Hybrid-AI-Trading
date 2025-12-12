from __future__ import annotations

import os
from pathlib import Path

from hybrid_ai_trading.microstructure import (
    MicrostructureTelemetryWriter,
    compute_microstructure_features,
    record_microstructure,
    classify_micro_regime,
)


def test_compute_microstructure_features_degenerate_len_lt2():
    feats = compute_microstructure_features(closes=[100.0], volumes=[10.0])
    assert feats.last_ret == 0.0
    assert feats.window_ret == 0.0
    assert feats.volume_sum == 0.0
    assert feats.score == 0.0


def test_compute_microstructure_features_positive_trend_positive_signed_volume():
    closes = [100.0, 101.0, 102.0]
    vols   = [10.0, 20.0, 30.0]
    feats = compute_microstructure_features(closes=closes, volumes=vols)
    assert feats.last_ret > 0
    assert feats.window_ret > 0
    assert feats.signed_volume is not None
    assert feats.signed_volume > 0
    assert feats.score > 0


def test_compute_microstructure_features_imbalance_pushes_score_sign():
    closes = [100.0, 100.5, 100.7]
    vols   = [10.0, 10.0, 10.0]
    buy    = [0.0, 10.0, 10.0]
    sell   = [0.0,  0.0,  0.0]
    feats = compute_microstructure_features(closes=closes, volumes=vols, buy_volumes=buy, sell_volumes=sell)
    assert feats.imbalance is not None
    assert feats.imbalance > 0
    assert feats.score > 0


def test_compute_microstructure_features_spread_wideness_penalizes():
    closes = [100.0, 101.0, 102.0]
    vols   = [10.0, 20.0, 30.0]
    spreads = [1.0, 1.0, 3.0]  # wideness 3.0x average -> should reduce score
    feats_no_spread = compute_microstructure_features(closes=closes, volumes=vols)
    feats_spread    = compute_microstructure_features(closes=closes, volumes=vols, spreads=spreads)
    assert feats_no_spread.score >= feats_spread.score


def test_record_microstructure_writes_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_MICRO_ENABLE", "1")

    # Force writer root to temp dir by patching cwd root via writer init arg.
    # We call writer directly here; record_microstructure uses default root.
    w = MicrostructureTelemetryWriter(root=str(tmp_path))
    feats = compute_microstructure_features(closes=[100.0, 101.0], volumes=[10.0, 20.0])
    w.write("TEST", feats)

    p = tmp_path / ".intel" / "microstructure.jsonl"
    assert p.exists()
    txt = p.read_text(encoding="utf-8")
    assert '"symbol": "TEST"' in txt


def test_classify_micro_regime_basic():
    assert classify_micro_regime(0.002, 0.4, 0.4) == "GREEN"
    assert classify_micro_regime(0.006, 0.8, 0.8) == "CAUTION"
    assert classify_micro_regime(0.02,  2.0, 2.0) == "RED"
