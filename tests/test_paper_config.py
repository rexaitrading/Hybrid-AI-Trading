from hybrid_ai_trading.runners.paper_config import load_config, parse_args


def test_parse_universe_list():
    ns = parse_args(["--universe", "AAPL, msft , tsla", "--once"])
    assert ns.universe_list == ["AAPL", "MSFT", "TSLA"]


def test_load_config_empty(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg == {}
