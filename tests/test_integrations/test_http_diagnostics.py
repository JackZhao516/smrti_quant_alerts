from unittest.mock import Mock, patch

import pytest
import requests

from smrti_quant_alerts.diagnostics import diagnose
from smrti_quant_alerts.http_client import APIError, PermanentAPIError, get_json, redact


def response(status, payload, headers=None):
    return Mock(status_code=status, json=Mock(return_value=payload), headers=headers or {})


@pytest.mark.parametrize("status", [401, 403, 451])
def test_permanent_errors_are_not_retried(status):
    with patch("requests.get", return_value=response(status, {})) as request:
        with pytest.raises(PermanentAPIError) as error:
            get_json("https://example.invalid?apikey=secret")
    assert str(error.value).find("secret") == -1
    assert request.call_count == 1


def test_rate_limit_respects_bounded_retry_after():
    with (
        patch("requests.get", side_effect=[response(429, {}, {"Retry-After": "100"}), response(200, [1])]),
        patch("time.sleep") as sleep,
    ):
        assert get_json("https://example.invalid") == [1]
    sleep.assert_called_once_with(30)


def test_transient_errors_exhaust_budget():
    with patch("requests.get", side_effect=requests.ConnectionError("apikey=secret")) as get:
        with pytest.raises(APIError, match="Network"):
            get_json("https://example.invalid", attempts=2)
    assert get.call_count == 2


def test_redacts_tokens_in_query_and_telegram_path():
    assert "secret" not in redact("https://api.telegram.org/botsecret/getMe?apikey=secret&api_token=secret")


def test_offline_diagnostics_does_not_request_network():
    with patch("requests.get") as get:
        result = diagnose({})
    get.assert_not_called()
    assert any(r["status"] == "missing_credentials" for r in result)


def test_live_region_block_is_classified_without_trades_or_messages():
    with patch("requests.get", return_value=response(451, {})) as get:
        assert diagnose({}, True, ["binance"])[0]["status"] == "region_restricted"
    assert get.call_args.args[0].endswith("/ping")


@pytest.mark.parametrize("status", [429, 503])
def test_http_retry_exhaustion_and_bad_retry_header(status):
    with patch("requests.get", return_value=response(status, {}, {"Retry-After": "invalid"})), patch("time.sleep"):
        with pytest.raises(APIError) as caught:
            get_json("https://example.invalid", attempts=2)
        assert caught.value.status == status


def test_http_rejects_invalid_json_provider_errors_and_budget():
    with pytest.raises(ValueError):
        get_json("https://example.invalid", attempts=0)
    bad = response(200, {})
    bad.json.side_effect = ValueError("secret response")
    with patch("requests.get", return_value=bad), pytest.raises(APIError, match="Invalid JSON"):
        get_json("https://example.invalid")
    with patch("requests.get", return_value=response(200, {"error": "secret"})):
        with pytest.raises(PermanentAPIError):
            get_json("https://example.invalid")


@pytest.mark.parametrize(
    "provider,data,status",
    [
        ("openai", {}, "reachable"),
        ("telegram", {"ok": False}, "rejected"),
        ("fmp", None, "empty_response"),
        ("eodhd", {}, "reachable"),
    ],
)
def test_read_only_provider_probes(provider, data, status):
    tokens = {
        "OPENAI_API_KEY": "real-value",
        "TELEGRAMBOT": {"TOKEN": "real-value"},
        "FMP_API_KEY": "real-value",
        "EODHD_API_KEY": "real-value",
    }
    with patch("smrti_quant_alerts.diagnostics.get_json", return_value=data) as request:
        assert diagnose(tokens, True, [provider])[0]["status"] == status
    assert request.call_args.kwargs["attempts"] == 1
    assert "sendMessage" not in request.call_args.args[0]


def test_diagnostic_cli_missing_and_invalid_credentials(tmp_path, monkeypatch, capsys):
    from smrti_quant_alerts.diagnostics import configured, main
    import sys

    assert not configured({})
    monkeypatch.setattr(sys, "argv", ["diagnose", "--config-root", str(tmp_path)])
    main()
    assert "missing_credentials" in capsys.readouterr().out
    (tmp_path / "token.json").write_text('["private"]')
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 2
    assert "private" not in capsys.readouterr().err
    (tmp_path / "token.json").write_text('{"OPENAI_API_KEY":"real-value"}')
    main()
    assert "configured" in capsys.readouterr().out


def test_redirects_never_forward_credentials_and_empty_selection_is_empty():
    with patch("requests.get", return_value=response(302, {})) as request:
        with pytest.raises(PermanentAPIError, match="Redirects"):
            get_json("https://provider.invalid", headers={"x-cg-pro-api-key": "private"})
    assert request.call_args.kwargs["allow_redirects"] is False
    with patch("requests.get") as request:
        assert diagnose({}, live=True, providers=[]) == []
    request.assert_not_called()
