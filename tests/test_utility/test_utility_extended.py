"""Additional tests for the alert scheduling helpers."""

from unittest import mock

import pytest

from smrti_quant_alerts import utility as utility_module
from smrti_quant_alerts.utility import run_alert


class _FakeConfig:
    def __init__(self) -> None:
        self.SETTINGS = {
            "test_alert": {
                "alert_input_args": {"window": 200},
                "run_time_input_args": {"daily_times": "00:00"},
            }
        }
        self.reload_calls = 0

    def reload_settings(self) -> None:
        self.reload_calls += 1


class _RecordingAlert:
    instances: list["_RecordingAlert"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.ran = False
        _RecordingAlert.instances.append(self)

    def run(self) -> None:
        self.ran = True


@pytest.fixture(autouse=True)
def reset_recording_alert():
    _RecordingAlert.instances = []
    yield
    _RecordingAlert.instances = []


def test_run_alert_executes_task_with_configured_alert_name(monkeypatch) -> None:
    config = _FakeConfig()
    monkeypatch.setattr(utility_module, "Config", lambda: config)
    monkeypatch.setattr(utility_module, "run_task_at_daily_time", lambda task, **kwargs: task())

    run_alert("test_alert", _RecordingAlert)

    alert = _RecordingAlert.instances[0]
    assert alert.ran
    assert alert.kwargs == {"window": 200, "alert_name": "test_alert"}
    assert config.reload_calls == 1


def test_run_alert_logs_start_and_finish(monkeypatch) -> None:
    config = _FakeConfig()
    monkeypatch.setattr(utility_module, "Config", lambda: config)
    monkeypatch.setattr(utility_module, "run_task_at_daily_time", lambda task, **kwargs: task())

    with mock.patch.object(utility_module.logging, "info") as info:
        run_alert("test_alert", _RecordingAlert)

    assert [call.args[0] for call in info.call_args_list] == ["test_alert start", "test_alert finished"]
