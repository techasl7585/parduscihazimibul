#!/usr/bin/python3
from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        import gi

        gi.require_version("Geoclue", "2.0")
        from gi.repository import Geoclue

        simple = Geoclue.Simple.new_sync(
            "pardus-cihazimi-bul",
            Geoclue.AccuracyLevel.EXACT,
            None,
        )
        location = simple.get_location()
        if location is None:
            return 2
        payload = {
            "latitude": location.get_property("latitude"),
            "longitude": location.get_property("longitude"),
            "accuracy": location.get_property("accuracy"),
            "altitude": location.get_property("altitude"),
        }
        sys.stdout.write(json.dumps(payload))
        return 0
    except (ImportError, ValueError, RuntimeError, TypeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
