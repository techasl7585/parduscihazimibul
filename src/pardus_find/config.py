from __future__ import annotations

import json
import os
import secrets
import socket
import tempfile
import threading
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_PORT = 8765


def _device_name() -> str:
    try:
        return socket.gethostname().strip() or "Pardus Cihazı"
    except OSError:
        return "Pardus Cihazı"


def default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "device_id": str(uuid.uuid4()),
        "device_name": _device_name(),
        "center_url": f"http://127.0.0.1:{DEFAULT_PORT}",
        "organization_key": secrets.token_urlsafe(24),
        "admin_token": secrets.token_urlsafe(32),
        "viewer_code": f"{secrets.randbelow(100_000_000):08d}",
        "location_enabled": False,
        "heartbeat_seconds": 15,
        "online_timeout_seconds": 60,
    }


class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._data = self._load_or_create()

    def _load_or_create(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            merged = default_config()
            merged.update(loaded)
            return merged

        created = default_config()
        self._write(created)
        return created

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=".config-", suffix=".json", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def public(self) -> dict[str, Any]:
        with self._lock:
            return {
                key: deepcopy(value)
                for key, value in self._data.items()
                if key not in {"admin_token", "organization_key", "viewer_code"}
            }

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "device_name",
            "center_url",
            "organization_key",
            "location_enabled",
        }
        with self._lock:
            updated = deepcopy(self._data)
            for key, value in changes.items():
                if key not in allowed:
                    continue
                if key in {"device_name", "center_url", "organization_key"}:
                    value = str(value).strip()
                    if not value:
                        raise ValueError(f"{key} boş bırakılamaz")
                if key == "center_url":
                    value = value.rstrip("/")
                    if not value.startswith(("http://", "https://")):
                        raise ValueError("Merkez adresi http:// veya https:// ile başlamalı")
                if key == "organization_key" and len(value) < 12:
                    raise ValueError("Kurum anahtarı en az 12 karakter olmalı")
                if key == "location_enabled":
                    value = bool(value)
                updated[key] = value
            self._write(updated)
            self._data = updated
            return self.public()
