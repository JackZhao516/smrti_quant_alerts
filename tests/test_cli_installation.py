"""CLI discovery must work before users create credentials."""

import os
from pathlib import Path
import subprocess
import sys


def test_cli_help_without_configuration(tmp_path):
    env = dict(os.environ, SMRTI_CONFIG_DIR=str(tmp_path))
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-m", "smrti_quant_alerts.main", "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "alert_name" in result.stdout
    assert not list(tmp_path.iterdir())


def test_cli_dispatches_once_and_rejects_unknown_names():
    from unittest.mock import Mock, patch
    import pytest
    from smrti_quant_alerts import main as cli

    config = Mock()
    config.SETTINGS = {
        "price": {"alert_type": "price_volume", "alert_input_args": {}},
        "daily": {"alert_type": "market_cap", "alert_input_args": {}},
    }
    price_class = Mock()
    daily_class = Mock()
    with (
        patch.object(cli, "Config", return_value=config),
        patch.dict(cli.alert_type_to_alert_class, {"price_volume": price_class, "market_cap": daily_class}),
        patch.object(cli, "run_alert") as run,
    ):
        cli.main(["price"])
        price_class.assert_called_once_with(alert_name="price")
        price_class.return_value.run.assert_called_once()
        cli.main(["daily"])
        run.assert_called_once_with("daily", daily_class)
        with pytest.raises(SystemExit) as caught:
            cli.main(["unknown"])
        assert caught.value.code == 2


def test_diagnostics_uses_config_environment_directory(tmp_path, monkeypatch, capsys):
    from smrti_quant_alerts.diagnostics import main

    monkeypatch.setenv("SMRTI_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["diagnose", "--provider", "openai"])
    (tmp_path / "token.json").write_text('{"OPENAI_API_KEY":"configured-real-value"}')
    main()
    assert '"status": "configured"' in capsys.readouterr().out
