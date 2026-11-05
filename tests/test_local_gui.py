from copy import deepcopy
import http.client
import json
from pathlib import Path
import threading

import pytest

from smrti_quant_alerts.gui.server import ConfigStore, create_server

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return json.loads((ROOT / "configs.json.example").read_text())


@pytest.fixture
def gui(tmp_path, settings):
    ConfigStore(tmp_path).save(settings)
    (tmp_path / "token.json").write_text('{"secret":"never-expose-this"}')
    server = create_server(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def call(server, method, path, data=None, **headers):
    client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    if method == "POST" and path == "/api/config":
        headers.setdefault("If-Match", server.store.version())
    if data is not None:
        headers.setdefault("Content-Type", "application/json")
        data = json.dumps(data)
    try:
        client.request(method, path, data, headers)
        response = client.getresponse()
        return response.status, response.read().decode()
    finally:
        client.close()


def test_editor_and_secret_isolation(gui):
    status, page = call(gui, "GET", "/")
    assert status == 200 and gui.csrf in page
    assert "never-expose-this" not in page
    status, body = call(gui, "GET", "/api/config")
    assert status == 200 and isinstance(json.loads(body), dict)
    assert "never-expose-this" not in body
    assert call(gui, "GET", "/token.json")[0] == 404
    assert call(gui, "GET", "/", Host="attacker.example")[0] == 403


def test_authenticated_save_and_rejected_cross_origin(gui, settings):
    assert call(gui, "POST", "/api/config", settings)[0] == 403
    headers = {"Origin": f"http://127.0.0.1:{gui.server_port}", "X-CSRF-Token": gui.csrf}
    assert call(gui, "POST", "/api/config", settings, **headers)[0] == 200
    headers["Origin"] = "https://attacker.example"
    assert call(gui, "POST", "/api/config", settings, **headers)[0] == 403


def test_invalid_save_preserves_file_and_permissions(tmp_path, settings):
    store = ConfigStore(tmp_path)
    store.save(settings)
    original = store.path.read_bytes()
    invalid = deepcopy(settings)
    first = next(iter(invalid.values()))
    for mutation in ({"database_name": "../escape"}, {"alert_type": "unknown"}, {"alert_input_args": {}}):
        bad = deepcopy(invalid)
        next(iter(bad.values())).update(mutation)
        with pytest.raises(ValueError):
            store.save(bad)
        assert store.path.read_bytes() == original
    assert first
    assert store.path.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".configs-*"))


@pytest.mark.parametrize("settings", [{}, [], {"": {}}, {"name": []}])
def test_rejects_invalid_settings_shapes(settings):
    from smrti_quant_alerts.gui.server import validate

    with pytest.raises(ValueError):
        validate(settings)


def test_rejects_constructor_and_schedule_mismatch(settings):
    from smrti_quant_alerts.gui.server import validate

    for change in (
        {"alert_input_args": []},
        {"alert_input_args": {"unexpected": 1}},
        {"run_time_input_args": {"daily_times": "wrong"}},
    ):
        bad = deepcopy(settings)
        next(iter(bad.values())).update(change)
        with pytest.raises(ValueError):
            validate(bad)


def test_missing_configuration_and_invalid_http_requests(gui):
    gui.store.path.unlink()
    assert call(gui, "GET", "/api/config")[0] == 404
    headers = {"Origin": f"http://127.0.0.1:{gui.server_port}", "X-CSRF-Token": gui.csrf}
    assert call(gui, "POST", "/unknown", {}, **headers)[0] == 404
    assert call(gui, "POST", "/api/config", [], **headers)[0] == 400
    assert call(gui, "POST", "/api/config", {}, **headers, **{"Content-Length": "0"})[0] == 413


def test_gui_cli_shutdown(tmp_path):
    from unittest.mock import MagicMock, patch
    from smrti_quant_alerts.gui.server import main

    server = MagicMock()
    server.__enter__.return_value = server
    server.serve_forever.side_effect = KeyboardInterrupt
    with patch("smrti_quant_alerts.gui.server.create_server", return_value=server) as create:
        main(["--config-root", str(tmp_path), "--port", "0"])
    create.assert_called_once_with(str(tmp_path), 0)
    server.__exit__.assert_called_once()


def test_stale_saves_and_storage_failures(gui, settings):
    from unittest.mock import patch

    headers = {"Origin": f"http://127.0.0.1:{gui.server_port}", "X-CSRF-Token": gui.csrf}
    version = gui.store.version()
    changed = deepcopy(settings)
    next(iter(changed.values()))["database_name"] = "updated"
    assert call(gui, "POST", "/api/config", changed, **headers)[0] == 200
    assert call(gui, "POST", "/api/config", settings, **headers, **{"If-Match": version})[0] == 409
    assert call(gui, "POST", "/api/config", settings, **headers, **{"If-Match": ""})[0] == 409
    with patch.object(gui.store, "save", side_effect=OSError("private storage detail")):
        status, body = call(gui, "POST", "/api/config", settings, **headers)
    assert status == 500 and "private storage detail" not in body
    assert next(iter(gui.store.read().values()))["database_name"] == "updated"
