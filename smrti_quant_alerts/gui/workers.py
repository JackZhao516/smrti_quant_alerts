"""Manage only alert processes explicitly started by this GUI session."""

import hashlib
import os
import stat
import json
from pathlib import Path
import subprocess
import sys
import threading

from smrti_quant_alerts.gateway.http_client import redact


class Workers:
    def __init__(self, root, popen=subprocess.Popen):
        self.root = Path(root).resolve()
        self.popen = popen
        self.entries = {}
        self.lock = threading.Lock()
        self.closed = False
        self.known_secrets = {}

    def _log_path(self, name):
        return self.root / "logs" / (hashlib.sha256(name.encode()).hexdigest()[:24] + ".log")

    def _open_log(self, name, flags):
        path = self._log_path(name)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise PermissionError("Log directory must be private and owned by the GUI user")
            fd = os.open(path.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                os.close(fd)
                raise PermissionError("Log must be a regular private file owned by the GUI user")
            os.fchmod(fd, 0o600)
            return fd
        finally:
            os.close(directory)

    def _credentials(self):
        def values(item):
            if isinstance(item, dict):
                for value in item.values():
                    yield from values(value)
            elif isinstance(item, list):
                for value in item:
                    yield from values(value)
            elif isinstance(item, str) and item:
                yield item

        tokens = json.loads((self.root / "token.json").read_text())
        if not isinstance(tokens, dict):
            raise ValueError("Invalid credentials object")
        return set(values(tokens))

    def status(self):
        with self.lock:
            return {
                name: {"running": process.poll() is None, "exit_code": process.poll()}
                for name, (process, _) in self.entries.items()
            }

    def start(self, name):
        with self.lock:
            if self.closed:
                raise ValueError("GUI is shutting down")
            existing = self.entries.get(name)
            if existing and existing[0].poll() is None:
                raise ValueError("Alert is already running")
            if existing:
                existing[1].close()
            try:
                credentials = self._credentials()
            except FileNotFoundError:
                credentials = set()
            fd = self._open_log(name, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
            os.ftruncate(fd, 0)
            self.known_secrets[name] = credentials
            stream = os.fdopen(fd, "ab")
            try:
                process = self.popen(
                    [sys.executable, "-m", "smrti_quant_alerts.main", name],
                    cwd=self.root,
                    env=dict(os.environ, SMRTI_CONFIG_DIR=str(self.root), PYTHONUNBUFFERED="1"),
                    stdin=subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    shell=False,
                    start_new_session=True,
                )
            except Exception:
                stream.close()
                raise
            self.entries[name] = (process, stream)

    def _stop(self, name):
        if name not in self.entries:
            raise ValueError("Alert was not started by this GUI")
        process, stream = self.entries[name]
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        finally:
            stream.close()

    def stop(self, name):
        with self.lock:
            self._stop(name)

    def logs(self, name):
        with self.lock:
            if name not in self.entries:
                raise ValueError("Alert was not started by this GUI")
            fd = self._open_log(name, os.O_RDONLY)
            with os.fdopen(fd, "rb") as stream:
                end = stream.seek(0, 2)
                stream.seek(max(0, end - 16_384))
                text = stream.read(min(end, 16_384)).decode(errors="replace")
            try:
                self.known_secrets[name].update(self._credentials())
            except (OSError, ValueError):
                return "Logs unavailable: credential redaction could not be loaded"
            for secret in sorted(self.known_secrets[name], key=len, reverse=True):
                text = text.replace(secret, "[REDACTED]")
            return redact(text).encode()[-16_384:].decode(errors="ignore")

    def close(self):
        with self.lock:
            self.closed = True
            for name in self.entries:
                self._stop(name)
