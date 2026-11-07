from unittest.mock import patch

import pytest

from smrti_quant_alerts.telegram_api import TelegramBot


def bot():
    return TelegramBot(daemon=False, tokens={"TOKEN": "secret", "TELEGRAM_IDS": {"CG_ALERT": "chat"}})


def test_message_uses_body_and_public_link_without_credential():
    with patch("requests.post") as post:
        bot()._send_message("A&B #中文 <tag>", blue_text=True)
    payload = post.call_args.kwargs["json"]
    assert "secret" not in payload["text"]
    assert "A&amp;B #中文 &lt;tag&gt;" in payload["text"]
    assert "?" not in post.call_args.args[0]


def test_upload_closes_file_even_when_request_raises(tmp_path):
    path = tmp_path / "test.csv"
    path.write_text("data")
    handles = []

    def fail(*args, **kwargs):
        handles.append(kwargs["files"]["document"])
        raise RuntimeError("failed")

    with patch("requests.post", side_effect=fail):
        bot().send_file(str(path), "test.csv")
    assert all(handle.closed for handle in handles)


def test_csv_is_removed_after_send_failure(tmp_path):
    client = bot()
    client.PWD = str(tmp_path)
    with patch.object(client, "send_file", side_effect=RuntimeError("failed")):
        client.send_data_as_csv_file("test.csv", ["header"], [[1]])
    assert not list(tmp_path.iterdir())


def test_csv_rejects_path_traversal():
    with pytest.raises(ValueError):
        bot().send_data_as_csv_file.__wrapped__(bot(), "../outside.csv", [], [])
