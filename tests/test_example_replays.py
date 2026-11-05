from examples.offline import replay
from smrti_quant_alerts.settings import Config


def test_crypto_replay_persists_counts_without_network():
    original = Config.PROJECT_DIR
    assert replay("crypto") == {"symbol": "BTC", "first_count": 1, "second_count": 2, "new_on_second_run": False}
    assert original == Config.PROJECT_DIR


def test_stock_replay_calculates_percentage_without_credentials():
    assert replay("stock") == {"symbol": "AAPL", "timeframe": "1D", "change_percent": 10.0}


def test_each_alert_has_a_matching_cli_command_and_output_guide():
    import json
    from pathlib import Path
    import re
    import shlex

    root = Path(__file__).resolve().parents[1]
    settings = json.loads((root / "configs.json.example").read_text())
    directory = root / "examples" / "alerts"
    assert {path.stem for path in directory.glob("*.md")} == {entry["alert_type"] for entry in settings.values()}
    for name, entry in settings.items():
        guide = (directory / f"{entry['alert_type']}.md").read_text()
        command = re.search(r"^python -m smrti_quant_alerts.main .+$", guide, re.MULTILINE).group()
        assert shlex.split(command) == ["python", "-m", "smrti_quant_alerts.main", name]
        if symbols_file := entry["alert_input_args"].get("symbols_file"):
            assert (root / symbols_file).is_file()
        assert "## Expected output" in guide
        assert re.search(r"```text\n[^`]+```", guide)
