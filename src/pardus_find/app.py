from __future__ import annotations

import fcntl
import hmac
import ipaddress
import json
import mimetypes
import socket
import struct
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pardus_find import __version__
from pardus_find.config import ConfigStore
from pardus_find.location import pardus_location
from pardus_find.store import DeviceStore


MAX_BODY = 64 * 1024
PRECISE_LOCATION_MAX_AGE = 30 * 60
LOCATION_REFRESH = 5 * 60


def local_ip() -> str | None:
    interfaces: list[str] = []
    try:
        with open("/proc/net/route", "r", encoding="ascii") as routes:
            for line in routes.read().splitlines()[1:]:
                fields = line.split()
                if len(fields) >= 4 and fields[1] == "00000000":
                    interfaces.append(fields[0])
    except OSError:
        pass
    try:
        interfaces.extend(
            name for _index, name in socket.if_nameindex() if name != "lo"
        )
    except OSError:
        pass

    seen: set[str] = set()
    for interface in interfaces:
        if interface in seen:
            continue
        seen.add(interface)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            request = struct.pack("256s", interface[:15].encode("utf-8"))
            response = fcntl.ioctl(sock.fileno(), 0x8915, request)
            address = socket.inet_ntoa(response[20:24])
            if not address.startswith("127."):
                return address
        except OSError:
            continue
        finally:
            sock.close()
    try:
        candidates = socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET
        )
        for candidate in candidates:
            address = str(candidate[4][0])
            if not address.startswith("127."):
                return address
    except OSError:
        pass
    return None


def is_loopback(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


class Application:
    def __init__(self, data_dir: Path, web_dir: Path):
        self.data_dir = data_dir
        self.web_dir = web_dir
        self.config = ConfigStore(data_dir / "config.json")
        self.devices = DeviceStore(data_dir / "devices.sqlite3")
        self._location_lock = threading.RLock()
        self._precise_location: dict[str, Any] | None = None
        self._automatic_location: dict[str, Any] | None = None
        self._automatic_location_state = "idle"
        self._automatic_location_message = ""
        self._location_checked_at = 0.0
        self._stop = threading.Event()
        self._agent_thread: threading.Thread | None = None

    def start_agent(self) -> None:
        if self._agent_thread and self._agent_thread.is_alive():
            return
        self._agent_thread = threading.Thread(
            target=self._agent_loop, name="location-agent", daemon=True
        )
        self._agent_thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._agent_thread:
            self._agent_thread.join(timeout=3)
        self.devices.close()

    def set_precise_location(self, payload: dict[str, Any]) -> dict[str, Any]:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        accuracy = float(payload.get("accuracy") or 0)
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("Geçersiz koordinat")
        if accuracy < 0 or accuracy > 1_000_000:
            raise ValueError("Geçersiz hassasiyet")
        location = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_m": accuracy or None,
            "city": None,
            "region": None,
            "country": None,
            "public_ip": None,
            "source": "browser",
            "updated_at": time.time(),
        }
        with self._location_lock:
            self._precise_location = location
        return location

    def _current_location(self) -> dict[str, Any] | None:
        config = self.config.snapshot()
        if not config["location_enabled"]:
            return None
        now = time.time()
        with self._location_lock:
            if (
                self._precise_location
                and now - self._precise_location["updated_at"]
                <= PRECISE_LOCATION_MAX_AGE
            ):
                return dict(self._precise_location)
            if now - self._location_checked_at >= LOCATION_REFRESH:
                self._location_checked_at = now
                refresh = True
            else:
                refresh = False
        if refresh:
            with self._location_lock:
                self._automatic_location_state = "searching"
                self._automatic_location_message = (
                    "Pardus Konum Servisi uygun konum kaynağını arıyor."
                )
            found = pardus_location()
            with self._location_lock:
                if found:
                    self._automatic_location = found
                    self._automatic_location_state = "available"
                    source = found.get("source")
                    if source == "pardus-positon":
                        self._automatic_location_message = (
                            "Bilgisayarın çevresindeki Wi-Fi ağlarıyla "
                            "konum bulundu."
                        )
                    elif source == "pardus-wifi":
                        self._automatic_location_message = (
                            "Yakındaki Wi-Fi ağlarıyla yaklaşık konum bulundu."
                        )
                    elif source == "pardus-network":
                        self._automatic_location_message = (
                            "Ağ bağlantısıyla yaklaşık konum bulundu."
                        )
                    else:
                        self._automatic_location_message = (
                            "Pardus Konum Servisi konumu buldu."
                        )
                else:
                    self._automatic_location_state = "unavailable"
                    self._automatic_location_message = (
                        "Pardus Konum Servisi konum kaynağı bulamadı. "
                        "Bilgisayarda GPS olmayabilir veya Wi-Fi konum "
                        "hizmeti kullanılamıyor olabilir."
                    )
        with self._location_lock:
            return (
                dict(self._automatic_location)
                if self._automatic_location
                else None
            )

    def location_status(self) -> dict[str, str]:
        with self._location_lock:
            return {
                "state": self._automatic_location_state,
                "message": self._automatic_location_message,
            }

    def _heartbeat_payload(self) -> dict[str, Any]:
        config = self.config.snapshot()
        return {
            "device_id": config["device_id"],
            "device_name": config["device_name"],
            "hostname": socket.gethostname(),
            "local_ip": local_ip(),
            "agent_version": __version__,
            "location": self._current_location(),
        }

    def send_heartbeat(self) -> tuple[bool, str]:
        config = self.config.snapshot()
        if not config["location_enabled"]:
            return False, "Konum paylaşımı kapalı"
        endpoint = f"{config['center_url']}/api/heartbeat"
        payload = self._heartbeat_payload()
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Organization-Key": config["organization_key"],
                "User-Agent": f"Pardus-Cihazimi-Bul/{__version__}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status != HTTPStatus.OK:
                    return False, f"Merkez HTTP {response.status} döndürdü"
            if payload["location"] is None:
                return (
                    True,
                    "Cihaz bilgisi gönderildi; konum kaynağı henüz bulunamadı.",
                )
            return True, "Konum merkeze gönderildi"
        except (OSError, urllib.error.URLError) as exc:
            return False, str(exc)

    def _agent_loop(self) -> None:
        while not self._stop.is_set():
            config = self.config.snapshot()
            if config["location_enabled"]:
                self.send_heartbeat()
            seconds = int(config.get("heartbeat_seconds", 15))
            self._stop.wait(max(5, seconds))


def make_handler(application: Application) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"PardusCihazimiBul/{__version__}"

        def log_message(self, message: str, *args: object) -> None:
            print(
                f"{self.log_date_time_string()} {self.client_address[0]} "
                f"{message % args}"
            )

        def _is_local(self) -> bool:
            return is_loopback(str(self.client_address[0]))

        def _authorized_admin(self) -> bool:
            if self._is_local():
                return True
            config = application.config.snapshot()
            header = self.headers.get("Authorization", "")
            supplied = header.removeprefix("Bearer ").strip()
            return bool(supplied) and (
                hmac.compare_digest(supplied, config["admin_token"])
                or hmac.compare_digest(supplied, config["viewer_code"])
            )

        def _json_body(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("Geçersiz istek uzunluğu") from exc
            if length <= 0 or length > MAX_BODY:
                raise ValueError("İstek gövdesi boş veya çok büyük")
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Geçersiz JSON") from exc

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_file(self, relative: str) -> None:
            root = application.web_dir.resolve()
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "frame-src 'none'; "
                "style-src 'self'; script-src 'self'; "
                "img-src 'self' data: https://tile.openstreetmap.org; "
                "connect-src 'self'",
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._serve_file("index.html")
                return
            if path == "/app.js":
                self._serve_file("app.js")
                return
            if path == "/styles.css":
                self._serve_file("styles.css")
                return
            if path.startswith("/vendor/"):
                self._serve_file(path.removeprefix("/"))
                return
            if path == "/api/health":
                self._send_json(
                    HTTPStatus.OK,
                    {"ok": True, "version": __version__, "time": time.time()},
                )
                return
            if path == "/api/bootstrap":
                if not self._authorized_admin():
                    self._send_json(
                        HTTPStatus.UNAUTHORIZED,
                        {"ok": False, "error": "Yönetici anahtarı gerekli"},
                    )
                    return
                config = application.config.public()
                if self._is_local():
                    private = application.config.snapshot()
                    config["admin_token"] = private["admin_token"]
                    config["organization_key"] = private["organization_key"]
                    config["viewer_code"] = private["viewer_code"]
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "local": self._is_local(),
                        "server_local_ip": local_ip() if self._is_local() else None,
                        "config": config,
                        "location_status": application.location_status(),
                    },
                )
                return
            if path == "/api/devices":
                if not self._authorized_admin():
                    self._send_json(
                        HTTPStatus.UNAUTHORIZED,
                        {"ok": False, "error": "Yetkisiz erişim"},
                    )
                    return
                timeout = int(
                    application.config.snapshot()["online_timeout_seconds"]
                )
                devices = application.devices.list_devices(timeout)
                self._send_json(
                    HTTPStatus.OK,
                    {"ok": True, "devices": devices, "server_time": time.time()},
                )
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = self._json_body()
                if path == "/api/heartbeat":
                    expected = application.config.snapshot()["organization_key"]
                    supplied = self.headers.get("X-Organization-Key", "")
                    if not supplied or not hmac.compare_digest(supplied, expected):
                        self._send_json(
                            HTTPStatus.UNAUTHORIZED,
                            {"ok": False, "error": "Kurum anahtarı geçersiz"},
                        )
                        return
                    if not payload.get("device_id"):
                        raise ValueError("device_id eksik")
                    application.devices.upsert(payload)
                    self._send_json(HTTPStatus.OK, {"ok": True})
                    return
                if path == "/api/settings":
                    if not self._is_local():
                        self._send_json(
                            HTTPStatus.FORBIDDEN,
                            {"ok": False, "error": "Ayarlar yalnızca bu cihazdan değiştirilebilir"},
                        )
                        return
                    config = application.config.update(payload)
                    if payload.get("location_enabled") is False:
                        device_id = application.config.snapshot()["device_id"]
                        application.devices.delete(device_id)
                        with application._location_lock:
                            application._precise_location = None
                            application._automatic_location = None
                            application._automatic_location_state = "idle"
                            application._automatic_location_message = ""
                    self._send_json(HTTPStatus.OK, {"ok": True, "config": config})
                    return
                if path == "/api/precise-location":
                    if not self._is_local():
                        self._send_json(
                            HTTPStatus.FORBIDDEN,
                            {"ok": False, "error": "Konum yalnızca bu cihazdan paylaşılabilir"},
                        )
                        return
                    location = application.set_precise_location(payload)
                    sent, message = application.send_heartbeat()
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "ok": True,
                            "location": location,
                            "heartbeat_sent": sent,
                            "message": message,
                        },
                    )
                    return
                if path == "/api/send-now":
                    if not self._is_local():
                        self._send_json(
                            HTTPStatus.FORBIDDEN,
                            {"ok": False, "error": "Bu işlem yalnızca yerel cihazda kullanılabilir"},
                        )
                        return
                    sent, message = application.send_heartbeat()
                    self._send_json(
                        HTTPStatus.OK if sent else HTTPStatus.BAD_GATEWAY,
                        {"ok": sent, "message": message},
                    )
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except (KeyError, TypeError, ValueError) as exc:
                self._send_json(
                    HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)}
                )

    return Handler


def run(application: Application, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(application))
    server.daemon_threads = True
    application.start_agent()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        application.stop()
