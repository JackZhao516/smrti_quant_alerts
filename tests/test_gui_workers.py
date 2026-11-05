import json
import subprocess
from unittest.mock import Mock

import pytest

from smrti_quant_alerts.gui.workers import Workers


def test_process_control_uses_argument_list_and_closes_streams(tmp_path):
    process = Mock()
    process.poll.return_value = None
    spawn = Mock(return_value=process)
    manager = Workers(tmp_path, popen=spawn)
    name = "literal;not-a-shell-command"
    manager.start(name)
    args, kwargs = spawn.call_args
    assert args[0][-1] == name
    assert kwargs["shell"] is False
    assert kwargs["cwd"] == tmp_path
    assert kwargs["env"]["SMRTI_CONFIG_DIR"] == str(tmp_path)
    with pytest.raises(ValueError, match="already running"):
        manager.start(name)
    assert manager.status()[name]["running"]
    process.wait.side_effect = [subprocess.TimeoutExpired("alert", 5), 0]
    manager.stop(name)
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert kwargs["stdout"].closed
    process.poll.return_value = 0
    manager.close()
    with pytest.raises(ValueError, match="shutting down"):
        manager.start(name)


def test_failed_spawn_closes_log_handle(tmp_path):
    spawn = Mock(side_effect=OSError("cannot spawn"))
    manager = Workers(tmp_path, popen=spawn)
    with pytest.raises(OSError):
        manager.start("alert")
    assert spawn.call_args.kwargs["stdout"].closed
    assert manager.status() == {}


def test_logs_are_bounded_and_redacted(tmp_path):
    manager = Workers(tmp_path, popen=Mock(return_value=Mock()))
    manager.start("../../alert")
    path = manager._log_path("../../alert")
    assert path.parent == tmp_path / "logs"
    (tmp_path / "token.json").write_text(json.dumps({"OPENAI_API_KEY": "secret-abcdef"}))
    path.write_text("old" * 20_000 + " secret-abcdef https://x.test?apikey=token123 END-MARKER")
    tail = manager.logs("../../alert")
    assert len(tail.encode()) <= 16_384
    assert "END-MARKER" in tail
    assert "secret-abcdef" not in tail and "token123" not in tail
    assert "REDACTED" in tail
    (tmp_path / "token.json").unlink()
    assert "unavailable" in manager.logs("../../alert")
    with pytest.raises(ValueError):
        manager.logs("unknown")
    manager.close()


def test_log_symlinks_are_rejected(tmp_path):
    manager = Workers(tmp_path, popen=Mock())
    target = tmp_path / "private-file"
    target.write_text("private contents")
    path = manager._log_path("alert")
    path.parent.mkdir(mode=0o700)
    path.symlink_to(target)
    with pytest.raises(OSError):
        manager.start("alert")
    manager.popen.assert_not_called()
    assert target.read_text() == "private contents"


def test_short_and_rotated_credentials_are_redacted(tmp_path):
    token = tmp_path / "token.json"
    token.write_text(json.dumps({"key": "old-key", "short": "xyz"}))
    manager = Workers(tmp_path, popen=Mock(return_value=Mock()))
    manager.start("alert")
    path = manager._log_path("alert")
    path.write_text("old-key xyz new-key ordinary-tail")
    token.write_text(json.dumps({"key": "new-key"}))
    result = manager.logs("alert")
    assert all(secret not in result for secret in ("old-key", "xyz", "new-key"))
    assert "ordinary-tail" in result
    manager.close()


def test_replaced_log_symlink_and_shared_directory_are_rejected(tmp_path):
    manager = Workers(tmp_path, popen=Mock(return_value=Mock()))
    manager.start("alert")
    path = manager._log_path("alert")
    path.unlink()
    path.symlink_to(tmp_path / "token.json")
    with pytest.raises(OSError):
        manager.logs("alert")
    manager.close()
    path.unlink()
    path.parent.chmod(0o755)
    with pytest.raises(PermissionError):
        Workers(tmp_path, popen=Mock()).start("second")
