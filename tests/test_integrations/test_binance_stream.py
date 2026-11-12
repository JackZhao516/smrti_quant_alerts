import json
import threading
from unittest.mock import AsyncMock, Mock

from smrti_quant_alerts.stock_crypto_api.binance_stream import SpotWebsocketStreamClient


def test_modular_subscription_message_and_shutdown():
    sdk = Mock()
    sdk.websocket_streams.create_connection = AsyncMock()
    sdk.websocket_streams.subscribe = AsyncMock()
    sdk.websocket_streams.close_connection = AsyncMock()
    sdk.websocket_streams.connections = [Mock(is_open=True)]
    received = []
    ready = threading.Event()

    def callback(client, message):
        received.append(json.loads(message))
        ready.set()

    client = SpotWebsocketStreamClient(callback, sdk=sdk)
    try:
        client.subscribe(["btcusdt@kline_15m"])
        sdk.websocket_streams.subscribe.assert_awaited_once_with(["btcusdt@kline_15m"])
        assert client.is_alive()
        sdk.websocket_streams.on.call_args.args[1]({"e": "kline", "k": {"x": True}})
        assert ready.wait(2)
        assert received[0]["stream"] == "btcusdt@kline_15m"
    finally:
        client.stop()
    assert not client.thread.is_alive()
    sdk.websocket_streams.close_connection.assert_awaited_once()


def test_subscription_failure_closes_loop_and_rejects_reuse():
    import pytest

    sdk = Mock()
    sdk.websocket_streams.create_connection = AsyncMock(side_effect=RuntimeError("connect failed"))
    sdk.websocket_streams.close_connection = AsyncMock()
    client = SpotWebsocketStreamClient(Mock(), sdk=sdk)
    with pytest.raises(RuntimeError, match="connect failed"):
        client.subscribe(["btcusdt@kline_15m"])
    assert not client.thread.is_alive()
    with pytest.raises(RuntimeError, match="closed"):
        client.subscribe([])
    client.stop()
    client._deliver("stream", {})


def test_handler_errors_are_contained_and_pending_tasks_cancelled():
    import asyncio

    sdk = Mock()
    sdk.websocket_streams.create_connection = AsyncMock()
    sdk.websocket_streams.subscribe = AsyncMock()
    sdk.websocket_streams.close_connection = AsyncMock()
    done = threading.Event()

    def fail(*_args):
        done.set()
        raise ValueError("handler failure")

    client = SpotWebsocketStreamClient(fail, sdk=sdk)
    client.subscribe(["btcusdt@kline_15m"])
    pending = asyncio.run_coroutine_threadsafe(asyncio.sleep(100), client.loop)
    client._deliver("stream", {})
    assert done.wait(2)
    client.stop()
    assert pending.cancelled()
    assert not client.thread.is_alive()
