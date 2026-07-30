from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class DeviceStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    hostname TEXT NOT NULL,
                    local_ip TEXT,
                    public_ip TEXT,
                    latitude REAL,
                    longitude REAL,
                    accuracy_m REAL,
                    city TEXT,
                    region TEXT,
                    country TEXT,
                    location_source TEXT,
                    location_updated_at REAL,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    agent_version TEXT NOT NULL
                )
                """
            )

    def upsert(self, payload: dict[str, Any], now: float | None = None) -> None:
        now = now or time.time()
        location = payload.get("location") or {}
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO devices (
                    device_id, device_name, hostname, local_ip, public_ip,
                    latitude, longitude, accuracy_m, city, region, country,
                    location_source, location_updated_at, first_seen, last_seen,
                    agent_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    device_name = excluded.device_name,
                    hostname = excluded.hostname,
                    local_ip = excluded.local_ip,
                    public_ip = excluded.public_ip,
                    latitude = COALESCE(excluded.latitude, devices.latitude),
                    longitude = COALESCE(excluded.longitude, devices.longitude),
                    accuracy_m = COALESCE(excluded.accuracy_m, devices.accuracy_m),
                    city = COALESCE(excluded.city, devices.city),
                    region = COALESCE(excluded.region, devices.region),
                    country = COALESCE(excluded.country, devices.country),
                    location_source = COALESCE(
                        excluded.location_source, devices.location_source
                    ),
                    location_updated_at = COALESCE(
                        excluded.location_updated_at, devices.location_updated_at
                    ),
                    last_seen = excluded.last_seen,
                    agent_version = excluded.agent_version
                """,
                (
                    str(payload["device_id"]),
                    str(payload.get("device_name") or "Pardus Cihazı"),
                    str(payload.get("hostname") or ""),
                    payload.get("local_ip"),
                    location.get("public_ip"),
                    location.get("latitude"),
                    location.get("longitude"),
                    location.get("accuracy_m"),
                    location.get("city"),
                    location.get("region"),
                    location.get("country"),
                    location.get("source"),
                    location.get("updated_at"),
                    now,
                    now,
                    str(payload.get("agent_version") or "bilinmiyor"),
                ),
            )

    def list_devices(
        self, online_timeout_seconds: int, now: float | None = None
    ) -> list[dict[str, Any]]:
        now = now or time.time()
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM devices ORDER BY last_seen DESC"
            ).fetchall()
        devices: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["online"] = now - item["last_seen"] <= online_timeout_seconds
            devices.append(item)
        return devices

    def delete(self, device_id: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM devices WHERE device_id = ?", (device_id,)
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()
