from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pardus_find.config import ConfigStore
from pardus_find.location import (
    parse_beacondb_payload,
    parse_geoclue_payload,
    parse_positon_payload,
    pardus_location,
    wifi_access_points,
)
from pardus_find.store import DeviceStore


class ConfigTests(unittest.TestCase):
    def test_config_is_created_and_secrets_are_not_public(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            store = ConfigStore(path)
            private = store.snapshot()
            public = store.public()
            self.assertTrue(path.exists())
            self.assertEqual(len(private["viewer_code"]), 8)
            self.assertFalse(private["location_enabled"])
            self.assertNotIn("admin_token", public)
            self.assertNotIn("organization_key", public)
            self.assertNotIn("viewer_code", public)

    def test_invalid_center_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ConfigStore(Path(directory) / "config.json")
            with self.assertRaises(ValueError):
                store.update({"center_url": "example.com"})


class LocationTests(unittest.TestCase):
    def test_geoclue_payload_is_normalized(self) -> None:
        parsed = parse_geoclue_payload(
            {
                "latitude": 41.015,
                "longitude": 28.979,
                "accuracy": 32.0,
                "altitude": 18.0,
            }
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["source"], "pardus-location")
        self.assertEqual(parsed["accuracy_m"], 32.0)

    def test_null_island_is_rejected(self) -> None:
        self.assertIsNone(
            parse_geoclue_payload(
                {
                    "latitude": 0,
                    "longitude": 0,
                    "accuracy": 999999,
                }
            )
        )

    def test_beacondb_ip_fallback_is_normalized(self) -> None:
        parsed = parse_beacondb_payload(
            {
                "accuracy": 25000,
                "fallback": "ipf",
                "location": {"lat": 40.3442, "lng": 26.6856},
            },
            used_wifi=True,
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["source"], "pardus-network")
        self.assertEqual(parsed["accuracy_m"], 25000.0)

    def test_positon_wifi_result_is_normalized(self) -> None:
        parsed = parse_positon_payload(
            {
                "location": {
                    "lat": 40.152171,
                    "lng": 26.404988,
                    "alt": 5,
                },
                "accuracy": 124,
            },
            used_wifi=True,
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["source"], "pardus-positon")
        self.assertEqual(parsed["accuracy_m"], 124.0)
        self.assertEqual(parsed["altitude_m"], 5.0)

    def test_positon_ip_fallback_is_rejected(self) -> None:
        self.assertIsNone(
            parse_positon_payload(
                {
                    "fallback": "ipf",
                    "location": {"lat": 40.3442, "lng": 26.6856},
                    "accuracy": 25000,
                },
                used_wifi=True,
            )
        )

    def test_wifi_scan_is_converted_and_private_ssids_are_skipped(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(
                "Okul:AA:BB:CC:DD:EE:FF:80\n"
                "Kutup:hane:11:22:33:44:55:66:42\n"
                "Ev_nomap:22:33:44:55:66:77:60\n"
                ":33:44:55:66:77:88:50\n"
                "gecersiz:70\n"
            ),
            stderr="",
        )
        with patch(
            "pardus_find.location.subprocess.run",
            return_value=completed,
        ):
            points = wifi_access_points()
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["macAddress"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(points[0]["signalStrength"], -60)

    def test_positon_is_used_before_beacondb(self) -> None:
        result = {
            "latitude": 40.152171,
            "longitude": 26.404988,
            "source": "pardus-positon",
        }
        points = [{"macAddress": "AA:BB:CC:DD:EE:FF", "signalStrength": -60}]
        with (
            patch(
                "pardus_find.location.geoclue_location",
                return_value=None,
            ),
            patch(
                "pardus_find.location.wifi_access_points",
                return_value=points,
            ),
            patch(
                "pardus_find.location.positon_location",
                return_value=result,
            ) as positon,
            patch(
                "pardus_find.location.beacondb_location",
            ) as beacondb,
        ):
            self.assertEqual(pardus_location(), result)
        positon.assert_called_once_with(points)
        beacondb.assert_not_called()

    def test_beacondb_is_used_when_geoclue_has_no_result(self) -> None:
        fallback = {
            "latitude": 40.3442,
            "longitude": 26.6856,
            "source": "pardus-network",
        }
        with (
            patch(
                "pardus_find.location.geoclue_location",
                return_value=None,
            ),
            patch(
                "pardus_find.location.wifi_access_points",
                return_value=[],
            ),
            patch(
                "pardus_find.location.positon_location",
                return_value=None,
            ),
            patch(
                "pardus_find.location.beacondb_location",
                return_value=fallback,
            ),
        ):
            self.assertEqual(pardus_location(), fallback)


class DeviceStoreTests(unittest.TestCase):
    def test_heartbeat_creates_online_device(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DeviceStore(Path(directory) / "devices.sqlite3")
            now = time.time()
            store.upsert(
                {
                    "device_id": "device-1",
                    "device_name": "Laboratuvar PC",
                    "hostname": "pardus-lab",
                    "local_ip": "192.168.1.20",
                    "agent_version": "0.1.0",
                    "location": {
                        "latitude": 39.93,
                        "longitude": 32.86,
                        "city": "Ankara",
                        "source": "ip",
                        "updated_at": now,
                    },
                },
                now=now,
            )
            devices = store.list_devices(60, now=now + 10)
            self.assertEqual(len(devices), 1)
            self.assertTrue(devices[0]["online"])
            self.assertEqual(devices[0]["device_name"], "Laboratuvar PC")
            store.close()

    def test_old_heartbeat_is_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DeviceStore(Path(directory) / "devices.sqlite3")
            store.upsert(
                {
                    "device_id": "device-2",
                    "device_name": "Eski PC",
                    "hostname": "pardus-eski",
                    "agent_version": "0.1.0",
                },
                now=1000,
            )
            devices = store.list_devices(60, now=1061)
            self.assertFalse(devices[0]["online"])
            store.close()

    def test_delete_removes_device(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DeviceStore(Path(directory) / "devices.sqlite3")
            store.upsert(
                {
                    "device_id": "device-delete",
                    "device_name": "Silinecek PC",
                    "hostname": "pardus-delete",
                    "agent_version": "0.1.0",
                }
            )
            store.delete("device-delete")
            self.assertEqual(store.list_devices(60), [])
            store.close()


if __name__ == "__main__":
    unittest.main()
