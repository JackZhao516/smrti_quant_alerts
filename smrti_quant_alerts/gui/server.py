import argparse
from contextlib import suppress
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import hashlib
import logging
import threading
import json
import os
from pathlib import Path
import secrets
import signal
import tempfile

from smrti_quant_alerts.main import alert_type_to_alert_class
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.gui.workers import Workers

MAX_BODY = 1_000_000


def validate(settings):
    if not isinstance(settings, dict) or not settings:
        raise ValueError("Provide at least one named alert")
    candidate = object.__new__(Config)
    candidate.SETTINGS = deepcopy(settings)
    for name, entry in settings.items():
        if not isinstance(name, str) or not name or not isinstance(entry, dict):
            raise ValueError("Invalid alert entry")
        if entry.get("alert_type") not in alert_type_to_alert_class:
            raise ValueError("Unknown alert type")
        if not isinstance(entry.get("alert_input_args"), dict) or not isinstance(entry.get("alert_params"), dict):
            raise ValueError("Alert arguments must be objects")
        database = entry.get("database_name") or name
        if not isinstance(database, str) or Path(database).name != database or database in (".", ".."):
            raise ValueError("Database name must be a filename")
        try:
            inspect.signature(alert_type_to_alert_class[entry["alert_type"]]).bind(
                alert_name=name, **entry["alert_input_args"]
            )
        except TypeError as exc:
            raise ValueError("Alert constructor arguments do not match") from exc
    try:
        candidate._validate_configs()
    except (SystemExit, TypeError, KeyError, AttributeError, ValueError) as exc:
        raise ValueError("Invalid alert configuration or schedule") from exc
    return candidate.SETTINGS


class StaleConfigError(ValueError):
    pass


class ConfigStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.path = self.root / "configs.json"
        self.lock = threading.Lock()

    def version(self):
        content = self.path.read_bytes() if self.path.exists() else b""
        return '"' + hashlib.sha256(content).hexdigest() + '"'

    def read(self):
        return json.loads(self.path.read_text())

    def snapshot(self):
        with self.lock:
            content = self.path.read_bytes()
            return json.loads(content), '"' + hashlib.sha256(content).hexdigest() + '"'

    def save(self, settings, expected=None):
        with self.lock:
            if expected is not None and expected != self.version():
                raise StaleConfigError("Reload before saving: configuration changed")
            self._save(settings)
            return self.version()

    def _save(self, settings):
        validated = validate(settings)
        self.root.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.root, prefix=".configs-")
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(validated, stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def reply(self, status, data, kind="application/json", etag=None):
        body = json.dumps(data).encode() if kind == "application/json" else data.encode()
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if etag is not None:
            self.send_header("ETag", etag)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def allowed(self, mutation=False):
        expected = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != expected:
            return False
        if mutation:
            return (
                self.headers.get("Origin") == f"http://{expected}"
                and secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), self.server.csrf)
                and self.headers.get_content_type() == "application/json"
            )
        return True

    def do_GET(self):
        if not self.allowed():
            return self.reply(403, {"error": "Forbidden host"})
        if self.path == "/":
            page = Path(__file__).with_name("index.html").read_text().replace("__CSRF__", self.server.csrf)
            return self.reply(200, page, "text/html")
        if self.path == "/api/status":
            return self.reply(200, self.server.workers.status())
        if self.path == "/api/config":
            try:
                settings, version = self.server.store.snapshot()
                return self.reply(200, settings, etag=version)
            except (OSError, ValueError):
                return self.reply(404, {"error": "Create configs.json from the example first"})
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if not self.allowed(mutation=True):
            return self.reply(403, {"error": "Forbidden request"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self.reply(413, {"error": "Invalid request size"})
            payload = json.loads(self.rfile.read(length))
            if self.path in ("/api/start", "/api/stop", "/api/logs"):
                if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
                    raise ValueError("Missing alert name")
                name = payload["name"]
                if self.path == "/api/start":
                    settings = validate(self.server.store.read())
                    if name not in settings:
                        raise ValueError("Unknown alert")
                    self.server.workers.start(name)
                elif self.path == "/api/stop":
                    self.server.workers.stop(name)
                else:
                    return self.reply(200, {"logs": self.server.workers.logs(name)})
                return self.reply(200, {"ok": True})
            if self.path != "/api/config":
                return self.reply(404, {"error": "Not found"})
            expected = self.headers.get("If-Match")
            if expected is None:
                return self.reply(428, {"error": "Reload configuration before saving"})
            version = self.server.store.save(payload, expected=expected)
            return self.reply(200, {"saved": True}, etag=version)
        except StaleConfigError:
            return self.reply(409, {"error": "Configuration changed; reload before saving"})
        except OSError as error:
            logging.error("GUI storage operation failed: %s", type(error).__name__)
            return self.reply(500, {"error": "Storage operation failed; check directory permissions and free space"})
        except (ValueError, TypeError):
            return self.reply(400, {"error": "Invalid request or configuration"})


def create_server(root, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.store = ConfigStore(root)
    server.workers = Workers(root)
    server.csrf = secrets.token_urlsafe(32)
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local alert configuration editor")
    parser.add_argument("--config-root", default=os.getcwd())
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    def terminate(_signum, _frame):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, terminate)
    with create_server(args.config_root, args.port) as server:
        print(f"Open http://127.0.0.1:{server.server_port}", flush=True)
        try:
            with suppress(KeyboardInterrupt):
                server.serve_forever()
        finally:
            server.workers.close()
            signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    main()
