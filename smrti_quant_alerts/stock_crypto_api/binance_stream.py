"""Synchronous lifecycle for the official SDK's asynchronous Spot market streams."""

import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from binance_common.configuration import ConfigurationWebSocketStreams
from binance_sdk_spot.spot import Spot

from smrti_quant_alerts.http_client import redact
from smrti_quant_alerts.stock_crypto_api.binance_client import plain


class SpotWebsocketStreamClient:
    def __init__(self, on_message, is_combined=True, timeout=2000, sdk=None):
        self.on_message = on_message
        self.sdk = sdk or Spot(config_ws_streams=ConfigurationWebSocketStreams())
        self.streams = self.sdk.websocket_streams
        self.socket_manager = self
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-events")
        self.ready = False
        self.closed = False
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    def _deliver(self, stream, payload):
        if self.closed:
            return
        data = plain(payload)
        message = data if isinstance(data, dict) and "data" in data else {"stream": stream, "data": data}

        def notify():
            try:
                self.on_message(self, json.dumps(message))
            except Exception as error:
                logging.error("Market event handler failed: %s", redact(error))

        self.executor.submit(notify)

    async def _subscribe(self, names):
        if not self.ready:
            await self.streams.create_connection()
            self.ready = True
        await self.streams.subscribe(names)
        for name in names:
            self.streams.on("message", lambda payload, stream=name: self._deliver(stream, payload), name)

    def subscribe(self, names):
        if self.closed:
            raise RuntimeError("stream client closed")
        try:
            return asyncio.run_coroutine_threadsafe(self._subscribe(list(names)), self.loop).result(timeout=30)
        except Exception:
            self.stop()
            raise

    def is_alive(self):
        return (
            not self.closed
            and self.thread.is_alive()
            and self.ready
            and any(c.is_open for c in self.streams.connections)
        )

    def stop(self):
        if self.closed:
            return
        self.closed = True
        try:
            asyncio.run_coroutine_threadsafe(self.streams.close_connection(), self.loop).result(timeout=10)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=12)
            self.executor.shutdown(wait=False, cancel_futures=True)
