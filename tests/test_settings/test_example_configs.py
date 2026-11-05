"""Keep the documented setup templates usable without credentials or network calls."""

import ast
import inspect
import json
from pathlib import Path

import pytest

from smrti_quant_alerts import alerts
from smrti_quant_alerts.alerts.comprehensive_alerts.macd_alert import MACDAlert
from smrti_quant_alerts.settings import Config

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    return json.loads((ROOT / name).read_text())


def _alert_registry():
    # Importing main initializes Config, so read its declared registry without
    # executing the CLI or constructing network-backed alert objects.
    module = ast.parse((ROOT / "smrti_quant_alerts" / "main.py").read_text())
    assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "alert_type_to_alert_class" for target in node.targets)
    )
    return {
        key.value: getattr(alerts, value.id)
        for key, value in zip(assignment.value.keys, assignment.value.values, strict=True)
    }


@pytest.mark.parametrize("name", ["configs.json.example", "token.json.example"])
def test_setup_template_is_valid_json(name):
    assert isinstance(_load(name), dict)


def test_setup_templates_pass_application_validation():
    config = object.__new__(Config)
    config.TOKENS = _load("token.json.example")
    config.SETTINGS = _load("configs.json.example")

    config._validate_tokens(verbose=False)
    config._validate_configs()


def test_config_templates_cover_every_registered_alert():
    settings = _load("configs.json.example")
    assert {entry["alert_type"] for entry in settings.values()} == set(_alert_registry())


def test_example_inputs_match_alert_constructors_and_telegram_channels():
    settings = _load("configs.json.example")
    channels = _load("token.json.example")["TELEGRAMBOT"]["TELEGRAM_IDS"]
    registry = _alert_registry()
    for name, entry in settings.items():
        args = entry["alert_input_args"]
        if entry["alert_type"] == "price_volume":
            assert len(args["tg_types"]) == len(args["alert_types"])
        inspect.signature(registry[entry["alert_type"]]).bind(alert_name=name, **args)
        for channel in args.get("tg_types", [args.get("tg_type", "TEST")]):
            assert channel in channels, (name, channel)


def test_macd_example_uses_supported_timeframes():
    settings = _load("configs.json.example")
    for entry in settings.values():
        if entry["alert_type"] == "macd_alert":
            args = entry["alert_input_args"]
            for timeframe in args["timeframe_list"] + args["add_on_timeframe_list"]:
                assert timeframe in MACDAlert.TIMEFRAME_DAYS
