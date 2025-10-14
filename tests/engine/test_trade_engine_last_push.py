import csv, os, pytest
from hybrid_ai_trading.trade_engine import TradeEngine

@pytest.fixture()
def eng_tmp(tmp_path):
    e = TradeEngine(config={})
    # direct audit files to a temp folder so we can hit header + append
    e.audit_log  = os.path.join(tmp_path, "audit.csv")
    e.backup_log = os.path.join(tmp_path, "backup.csv")
    return e

def test_write_audit_header_and_append(eng_tmp):
    row = [0.0, "AAPL", "BUY", 1, 100.0, "filled", eng_tmp.portfolio.equity, "ok"]
    # first write -> file doesn't exist: header + row
    eng_tmp._write_audit(row)
    # second write -> file exists: no header, append only
    eng_tmp._write_audit(row)
    # quick sanity to ensure both files were touched
    for p in (eng_tmp.audit_log, eng_tmp.backup_log):
        with open(p, newline="") as f:
            r = list(csv.reader(f))
            assert len(r) >= 2  # header + at least one row

def test_record_trade_outcome_logs_failure(monkeypatch, caplog):
    e = TradeEngine(config={})
    # make record_trade raise -> exercise logger.error in except
    monkeypatch.setattr(e.performance_tracker, "record_trade",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")), raising=True)
    e.record_trade_outcome(1.23)
    assert any("Failed to record trade outcome:" in rec.message for rec in caplog.records)