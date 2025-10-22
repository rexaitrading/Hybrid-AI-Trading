from hybrid_ai_trading.runners.paper_config import parse_args
def test_flags_parse_known():
    a = parse_args([
        "--config","config/paper_runner.yaml",
        "--universe","AAPL,MSFT",
        "--mdt","3",
        "--once",
        "--snapshots-when-closed",
        "--enforce-riskhub",
        "--log-file","logs/runner_paper.jsonl",
        "--some-unknown-flag"  # should be tolerated by parse_known_args
    ])
    assert a.universe == "AAPL,MSFT"
    assert a.once and a.snapshots_when_closed and a.enforce_riskhub
