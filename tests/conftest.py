"""Shared pytest fixtures.

The production code uses a process-wide ``Config`` singleton and a global database
proxy. These fixtures keep that state isolated between tests and provide a temporary
SQLite database for tests that need persistence.
"""

import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from smrti_quant_alerts.settings import Config

TEST_SETTINGS_DIR = Path(__file__).parent / "test_settings"


def _load_json(name: str) -> dict:
    return json.loads((TEST_SETTINGS_DIR / name).read_text())


@pytest.fixture(autouse=True)
def restore_config():
    """Restore ``Config`` class state after every test.

    Several legacy tests mutate ``Config.TOKENS``/``SETTINGS``/``PROJECT_DIR``
    directly. Restoring keeps those mutations from leaking into other tests.
    """
    original = (
        Config.PROJECT_DIR,
        copy.deepcopy(Config.TOKENS),
        copy.deepcopy(Config.SETTINGS),
        Config.IS_SETUP,
    )
    yield
    Config.PROJECT_DIR, Config.TOKENS, Config.SETTINGS, Config.IS_SETUP = original


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Skip real sleeps so retry/queue logic runs instantly in tests."""
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)


@pytest.fixture
def test_settings() -> SimpleNamespace:
    """Dummy tokens and alert settings used by the test suite."""
    return SimpleNamespace(
        project_dir=TEST_SETTINGS_DIR,
        tokens=_load_json("token.json"),
        settings=_load_json("configs.json"),
    )


@pytest.fixture
def runtime_database(tmp_path: Path):
    """Initialize the global database proxy against a throwaway project directory."""
    from smrti_quant_alerts.db import close_database, init_database_runtime

    original_project_dir = Config.PROJECT_DIR
    close_database()
    Config.PROJECT_DIR = str(tmp_path)
    init_database_runtime("test.db")
    try:
        yield tmp_path
    finally:
        close_database()
        Config.PROJECT_DIR = original_project_dir


@pytest.fixture
def fake_telegram_bot() -> MagicMock:
    """A TelegramBot stand-in that records messages instead of sending them."""
    return MagicMock()
