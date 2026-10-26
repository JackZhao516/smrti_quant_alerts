"""Additional unit tests for the OpenAI-backed LLM API.

The OpenAI client is always a mock; no network access is required.
"""

import logging
from unittest import mock

import pytest

from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.llm_api import LLMAPI
from smrti_quant_alerts.llm_api import llm_api as llm_api_module
from smrti_quant_alerts.settings import Config


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    LLMAPI._last_request_time = 0
    LLMAPI._current_count = 0
    yield
    LLMAPI._last_request_time = 0
    LLMAPI._current_count = 0


@pytest.fixture
def api() -> LLMAPI:
    """An LLMAPI instance with a mocked client and no Config side effects."""
    api = object.__new__(LLMAPI)
    api._model = "gpt-4.1"
    api._client = mock.Mock()
    return api


def _completion(content: str | None) -> mock.Mock:
    message = mock.Mock()
    message.content = content
    choice = mock.Mock()
    choice.message = message
    response = mock.Mock()
    response.choices = [choice]
    return response


def test_init_uses_api_key_from_tokens(monkeypatch) -> None:
    monkeypatch.setattr(Config, "TOKENS", {"OPENAI_API_KEY": "token-key"})
    monkeypatch.setattr(Config, "IS_SETUP", True)

    with mock.patch.object(llm_api_module, "OpenAI") as openai_cls:
        api = LLMAPI()

    assert api._api_key == "token-key"
    assert api._model == "gpt-4.1"
    openai_cls.assert_called_once_with(api_key="token-key")


def test_init_falls_back_to_environment_variable(monkeypatch) -> None:
    monkeypatch.setattr(Config, "TOKENS", {})
    monkeypatch.setattr(Config, "IS_SETUP", True)
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")

    with mock.patch.object(llm_api_module, "OpenAI") as openai_cls:
        api = LLMAPI()

    assert api._api_key == "env-key"
    openai_cls.assert_called_once_with(api_key="env-key")


def test_init_without_api_key_skips_client(monkeypatch, caplog) -> None:
    monkeypatch.setattr(Config, "TOKENS", {})
    monkeypatch.setattr(Config, "IS_SETUP", True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with (
        mock.patch.object(llm_api_module, "OpenAI") as openai_cls,
        caplog.at_level(logging.WARNING),
    ):
        api = LLMAPI()

    assert api._client is None
    openai_cls.assert_not_called()
    assert "No OpenAI API key" in caplog.text


def test_build_chat_message_omits_empty_parts() -> None:
    assert LLMAPI.build_chat_message("", "") == []
    assert LLMAPI.build_chat_message("system", "") == [{"role": "system", "content": "system"}]
    assert LLMAPI.build_chat_message("", "user") == [{"role": "user", "content": "user"}]


def test_get_ai_response_returns_content_and_sorted_citations(api: LLMAPI) -> None:
    api._client.chat.completions.create.return_value = _completion(
        "Answer with [b.com](https://b.com), [a.com](https://a.com) and [a.com](https://a.com)."
    )

    content, citations = api.get_ai_response("question")

    assert content.startswith("Answer with")
    assert citations == "\n\n## Sources:\n- [a.com](https://a.com)\n- [b.com](https://b.com)"
    kwargs = api._client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4.1"
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_tokens"] == 2000
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1]["content"].strip().endswith("question")


def test_get_ai_response_without_citations(api: LLMAPI) -> None:
    api._client.chat.completions.create.return_value = _completion("Answer without links")

    assert api.get_ai_response("question") == ("Answer without links", "")


def test_get_ai_response_handles_empty_content(api: LLMAPI) -> None:
    api._client.chat.completions.create.return_value = _completion(None)

    assert api.get_ai_response("question") == ("", "")


def test_get_ai_response_swallows_client_errors(api: LLMAPI) -> None:
    api._client.chat.completions.create.side_effect = RuntimeError("boom")

    assert api.get_ai_response("question") == ("", "")


def test_get_stock_increase_reason_builds_prompt(api: LLMAPI) -> None:
    with mock.patch.object(api, "get_ai_response", return_value=("reason", "")) as get_response:
        result = api.get_stock_increase_reason(StockSymbol("AAPL"), ["1d", "5y"])

    assert result == "reason"
    prompt = get_response.call_args.args[0]
    assert "stock code AAPL" in prompt
    assert "5y timeframe ago" in prompt


def test_get_stock_increase_reason_accepts_single_timeframe(api: LLMAPI) -> None:
    with mock.patch.object(api, "get_ai_response", return_value=("reason", "")) as get_response:
        result = api.get_stock_increase_reason(StockSymbol("AAPL"), "1d")

    assert result == "reason"
    assert "1d timeframe ago" in get_response.call_args.args[0]


def test_get_stock_increase_reason_appends_citations(api: LLMAPI) -> None:
    citations = "\n\n## Sources:\n- [a.com](https://a.com)"

    with mock.patch.object(api, "get_ai_response", return_value=("reason", citations)):
        result = api.get_stock_increase_reason(StockSymbol("AAPL"), "1d")

    assert result == f"reason{citations}"


def test_get_stock_increase_reason_waits_when_rate_limit_is_reached(api: LLMAPI, monkeypatch) -> None:
    sleeps = []
    monkeypatch.setattr(llm_api_module, "time", lambda: 100.0)
    monkeypatch.setattr(llm_api_module, "sleep", lambda seconds: sleeps.append(seconds))
    api._last_request_time = 90.0
    api._current_count = 0

    with mock.patch.object(api, "get_ai_response", return_value=("reason", "")):
        api.get_stock_increase_reason(StockSymbol("AAPL"), "1d")

    assert sleeps == [50.0]
    assert api._current_count == 1
    assert api._last_request_time == 100.0


def test_get_stock_increase_reason_skips_wait_below_rate_limit(api: LLMAPI, monkeypatch) -> None:
    sleeps = []
    monkeypatch.setattr(llm_api_module, "time", lambda: 100.0)
    monkeypatch.setattr(llm_api_module, "sleep", lambda seconds: sleeps.append(seconds))
    api._current_count = 5

    with mock.patch.object(api, "get_ai_response", return_value=("reason", "")):
        api.get_stock_increase_reason(StockSymbol("AAPL"), "1d")

    assert sleeps == []
    assert api._current_count == 6


def test_get_stock_increase_reason_returns_empty_after_retries(api: LLMAPI, monkeypatch) -> None:
    monkeypatch.setattr(llm_api_module, "sleep", lambda _seconds: None)

    with mock.patch.object(api, "get_ai_response", side_effect=RuntimeError("boom")) as get_response:
        result = api.get_stock_increase_reason(StockSymbol("AAPL"), "1d")

    assert result == ""
    assert get_response.call_count == 5
