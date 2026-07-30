#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
VERSION="0.1.7"
PACKAGE_NAME="pardus-cihazimi-bul_${VERSION}_amd64"
BUILD_DIR="$PROJECT_DIR/build"
mkdir -p "$BUILD_DIR"
STAGE_DIR="$(mktemp -d "$BUILD_DIR/.stage.XXXXXXXX")"
PACKAGE_TEMP_DIR="$BUILD_DIR/.package-tmp"
mkdir -p "$PACKAGE_TEMP_DIR"

cleanup() {
    rm -rf "$STAGE_DIR"
}
trap cleanup EXIT INT TERM

cp -a "$PROJECT_DIR/packaging/rootfs/." "$STAGE_DIR/"
install -d -m 0755 "$STAGE_DIR/opt/pardus-cihazimi-bul"
cp -a "$PROJECT_DIR/src/." "$STAGE_DIR/opt/pardus-cihazimi-bul/"
find "$STAGE_DIR/opt/pardus-cihazimi-bul" \
    -type d -name __pycache__ -prune -exec rm -rf {} +
install -m 0644 "$PROJECT_DIR/README.md" "$STAGE_DIR/opt/pardus-cihazimi-bul/README.md"
install -m 0644 "$PROJECT_DIR/LICENSE" "$STAGE_DIR/opt/pardus-cihazimi-bul/LICENSE"

chmod 0755 \
    "$STAGE_DIR/DEBIAN/postinst" \
    "$STAGE_DIR/DEBIAN/prerm" \
    "$STAGE_DIR/DEBIAN/postrm" \
    "$STAGE_DIR/usr/bin/pardus-cihazimi-bul" \
    "$STAGE_DIR/opt/pardus-cihazimi-bul/main.py"

find "$STAGE_DIR/opt/pardus-cihazimi-bul" -type d -exec chmod 0755 {} +
find "$STAGE_DIR/opt/pardus-cihazimi-bul" -type f ! -name main.py -exec chmod 0644 {} +

TMPDIR="$PACKAGE_TEMP_DIR" \
    dpkg-deb --root-owner-group --build "$STAGE_DIR" "$BUILD_DIR/$PACKAGE_NAME.deb"
(
    cd "$BUILD_DIR"
    sha256sum "$PACKAGE_NAME.deb" > "$PACKAGE_NAME.deb.sha256"
)

echo "Hazır: $BUILD_DIR/$PACKAGE_NAME.deb"
