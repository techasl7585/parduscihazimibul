from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pardus_find import __version__


GEOCLUE_HELPER = Path(__file__).resolve().with_name("geoclue_probe.py")
POSITON_URL = "https://api.positon.xyz/v1/geolocate"
POSITON_KEY_FILE = Path("/etc/pardus-cihazimi-bul/positon-api-key")
BEACONDB_URL = "https://api.beacondb.net/v1/geolocate"
NMCLI = "/usr/bin/nmcli"
MAC_ADDRESS = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_geoclue_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    latitude = _number(payload.get("latitude"))
    longitude = _number(payload.get("longitude"))
    if latitude is None or longitude is None:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    if latitude == 0 and longitude == 0:
        return None
    return {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": _number(payload.get("accuracy")),
        "altitude_m": _number(payload.get("altitude")),
        "city": None,
        "region": None,
        "country": None,
        "public_ip": None,
        "source": "pardus-location",
        "updated_at": time.time(),
    }


def parse_beacondb_payload(
    payload: dict[str, Any], used_wifi: bool
) -> dict[str, Any] | None:
    location = payload.get("location")
    if not isinstance(location, dict):
        return None
    latitude = _number(location.get("lat"))
    longitude = _number(location.get("lng"))
    if latitude is None or longitude is None:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    if latitude == 0 and longitude == 0:
        return None
    source = (
        "pardus-network"
        if payload.get("fallback") == "ipf" or not used_wifi
        else "pardus-wifi"
    )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": _number(payload.get("accuracy")),
        "altitude_m": None,
        "city": None,
        "region": None,
        "country": None,
        "public_ip": None,
        "source": source,
        "updated_at": time.time(),
    }


def parse_positon_payload(
    payload: dict[str, Any], used_wifi: bool
) -> dict[str, Any] | None:
    if payload.get("fallback") == "ipf" or not used_wifi:
        return None
    location = payload.get("location")
    if not isinstance(location, dict):
        return None
    latitude = _number(location.get("lat"))
    longitude = _number(location.get("lng"))
    if latitude is None or longitude is None:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    if latitude == 0 and longitude == 0:
        return None
    return {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": _number(payload.get("accuracy")),
        "altitude_m": _number(location.get("alt")),
        "city": None,
        "region": None,
        "country": None,
        "public_ip": None,
        "source": "pardus-positon",
        "updated_at": time.time(),
    }


def wifi_access_points(timeout: float = 3.0) -> list[dict[str, Any]]:
    try:
        completed = subprocess.run(
            [
                NMCLI,
                "--terse",
                "--escape",
                "no",
                "--fields",
                "SSID,BSSID,SIGNAL",
                "device",
                "wifi",
                "list",
                "--rescan",
                "no",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []

    access_points: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in completed.stdout.splitlines():
        try:
            fields = line.strip().rsplit(":", 7)
            if len(fields) != 8:
                continue
            ssid = fields[0]
            bssid = ":".join(fields[1:7])
            signal_text = fields[7]
            signal = max(0, min(100, int(signal_text)))
        except (ValueError, AttributeError):
            continue
        if not ssid or ssid.endswith("_nomap"):
            continue
        bssid = bssid.upper()
        if not MAC_ADDRESS.fullmatch(bssid) or bssid in seen:
            continue
        seen.add(bssid)
        access_points.append(
            {
                "macAddress": bssid,
                "signalStrength": round(signal / 2 - 100),
            }
        )
        if len(access_points) >= 40:
            break
    return access_points


def _post_location_request(
    url: str, payload: dict[str, Any], timeout: float
) -> dict[str, Any] | None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"Pardus-Cihazimi-Bul/{__version__}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except (
        OSError,
        ValueError,
        urllib.error.HTTPError,
        urllib.error.URLError,
    ):
        return None
    if not isinstance(result, dict):
        return None
    return result


def positon_api_key() -> str:
    try:
        key = POSITON_KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        key = ""
    return key or "test"


def positon_location(
    access_points: list[dict[str, Any]] | None = None,
    timeout: float = 8.0,
) -> dict[str, Any] | None:
    points = wifi_access_points() if access_points is None else access_points
    if not points:
        return None
    key = urllib.parse.quote(positon_api_key(), safe="")
    result = _post_location_request(
        f"{POSITON_URL}?key={key}",
        {
            "considerIp": False,
            "fallbacks": {"ipf": False},
            "wifiAccessPoints": points,
        },
        timeout,
    )
    if result is None:
        return None
    return parse_positon_payload(result, True)


def beacondb_location(
    access_points: list[dict[str, Any]] | None = None,
    timeout: float = 8.0,
) -> dict[str, Any] | None:
    points = wifi_access_points() if access_points is None else access_points
    payload: dict[str, Any] = {"considerIp": True}
    if points:
        payload["wifiAccessPoints"] = points
    result = _post_location_request(BEACONDB_URL, payload, timeout)
    if result is None:
        return None
    return parse_beacondb_payload(result, bool(points))


def geoclue_location(timeout: float = 4.0) -> dict[str, Any] | None:
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(GEOCLUE_HELPER)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return parse_geoclue_payload(payload)


def pardus_location(timeout: float = 4.0) -> dict[str, Any] | None:
    geoclue = geoclue_location(timeout)
    if geoclue:
        return geoclue
    access_points = wifi_access_points()
    return positon_location(access_points) or beacondb_location(access_points)
