from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pardus_find.app import Application, make_handler


class HttpApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        data_dir = Path(self.temporary.name)
        web_dir = PROJECT_ROOT / "src" / "pardus_find" / "web"
        self.application = Application(data_dir, web_dir)
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.application)
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.application.devices.close()
        self.temporary.cleanup()

    def _json(self, path: str) -> dict:
        with urllib.request.urlopen(
            self.base_url + path, timeout=2
        ) as response:
            return json.load(response)

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_health_and_static_panel(self) -> None:
        health = self._json("/api/health")
        self.assertTrue(health["ok"])
        with urllib.request.urlopen(
            self.base_url + "/", timeout=2
        ) as response:
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
            body = response.read().decode("utf-8")
        self.assertIn("Pardus Cihazımı Bul", body)
        with urllib.request.urlopen(
            self.base_url + "/vendor/leaflet/leaflet.js", timeout=2
        ) as response:
            leaflet = response.read().decode("utf-8")
        self.assertIn("Leaflet", leaflet)

    def test_heartbeat_appears_in_devices(self) -> None:
        bootstrap = self._json("/api/bootstrap")
        payload = {
            "device_id": "http-test-device",
            "device_name": "HTTP Test PC",
            "hostname": "pardus-http-test",
            "local_ip": "192.168.1.60",
            "agent_version": "0.1.0",
            "location": {
                "latitude": 41.015,
                "longitude": 28.979,
                "accuracy_m": 35,
                "source": "pardus-location",
                "updated_at": 1785440000,
            },
        }
        request = urllib.request.Request(
            self.base_url + "/api/heartbeat",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Organization-Key": bootstrap["config"]["organization_key"],
            },
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            result = json.load(response)
        self.assertTrue(result["ok"])

        devices = self._json("/api/devices")["devices"]
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["location_source"], "pardus-location")
        self.assertTrue(devices[0]["online"])

    def test_one_button_share_and_stop_flow(self) -> None:
        bootstrap = self._json("/api/bootstrap")
        self.assertFalse(bootstrap["config"]["location_enabled"])
        fake_location = {
            "latitude": 39.9334,
            "longitude": 32.8597,
            "accuracy_m": 40,
            "city": None,
            "region": None,
            "country": None,
            "public_ip": None,
            "source": "pardus-location",
            "updated_at": 1785440000,
        }
        with patch(
            "pardus_find.app.pardus_location", return_value=fake_location
        ):
            enabled = self._post(
                "/api/settings",
                {
                    "location_enabled": True,
                    "center_url": self.base_url,
                },
            )
            self.assertTrue(enabled["config"]["location_enabled"])
            sent = self._post("/api/send-now", {})
            self.assertTrue(sent["ok"])

        devices = self._json("/api/devices")["devices"]
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["location_source"], "pardus-location")

        disabled = self._post(
            "/api/settings", {"location_enabled": False}
        )
        self.assertFalse(disabled["config"]["location_enabled"])
        self.assertEqual(self._json("/api/devices")["devices"], [])

    def test_missing_location_source_is_reported(self) -> None:
        with patch("pardus_find.app.pardus_location", return_value=None):
            enabled = self._post(
                "/api/settings",
                {
                    "location_enabled": True,
                    "center_url": self.base_url,
                },
            )
            self.assertTrue(enabled["config"]["location_enabled"])
            sent = self._post("/api/send-now", {})
            self.assertTrue(sent["ok"])

        bootstrap = self._json("/api/bootstrap")
        self.assertEqual(
            bootstrap["location_status"]["state"], "unavailable"
        )
        self.assertIn(
            "konum kaynağı bulamadı",
            bootstrap["location_status"]["message"],
        )


if __name__ == "__main__":
    unittest.main()
