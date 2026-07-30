#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DATA_DIR="${PARDUS_FIND_DEV_DATA:-$PROJECT_DIR/.dev-data}"

exec /usr/bin/python3 \
    "$PROJECT_DIR/src/main.py" \
    --data-dir "$DATA_DIR" \
    --host 127.0.0.1
