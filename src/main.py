#!/usr/bin/python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_ROOT))

from pardus_find.app import Application, run  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pardus Cihazımı Bul servisi")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("PARDUS_FIND_DATA_DIR", "/var/lib/pardus-cihazimi-bul")),
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("PARDUS_FIND_HOST", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PARDUS_FIND_PORT", "8765")),
    )
    parser.add_argument(
        "--web-dir",
        type=Path,
        default=PACKAGE_ROOT / "pardus_find" / "web",
    )
    return parser.parse_args()


def main() -> None:
    args = arguments()
    application = Application(args.data_dir, args.web_dir)
    run(application, args.host, args.port)


if __name__ == "__main__":
    main()
