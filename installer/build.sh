#!/bin/sh
# build.sh — builds IDP-Estate.pkg, the GUI installer. The founder types the admin password once;
# the pkg installs the root-owned converger that keeps this laptop on main from then on
# (docs/tickets/2026-09-27-merged-is-operating.md). Requires pkgbuild + productbuild (macOS).
#
# The payload is exactly these two files, so the pkg never re-owns a shared directory such as a
# user-owned /usr/local/bin (Homebrew):
#   /usr/local/estate/sbin/estate-converge           0755 root:wheel
#   /Library/LaunchDaemons/ai.estate.converge.plist  0644 root:wheel
# The pkg is built, never committed: a committed pkg is a stale copy of the converger.
#
# Usage: bash installer/build.sh                    -> installer/IDP-Estate.pkg
#        OUT=/tmp/IDP-Estate.pkg bash installer/build.sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
IDP="${IDP:-$(dirname "$SCRIPT_DIR")}"
PKG="$IDP/installer"
OUT="${OUT:-$PKG/IDP-Estate.pkg}"
LABEL=ai.estate.converge
VERSION=0.2.0
CONVERGE="$IDP/platform/estate/bin/estate-converge"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ROOT="$TMP/root"
SCRIPTS="$TMP/scripts"
RESOURCES="$TMP/resources"

for f in "$CONVERGE" "$PKG/$LABEL.plist" "$PKG/preinstall" "$PKG/postinstall" \
         "$PKG/Distribution.xml.in" "$PKG/idp-estate.plist"; do
    [ -f "$f" ] || { echo "ERROR: $f not found" >&2; exit 1; }
done
plutil -lint "$PKG/$LABEL.plist" >/dev/null
# Never package a converger that fails its own test; postinstall runs it again on the target.
/usr/bin/python3 "$CONVERGE" --self-test >/dev/null

mkdir -p "$ROOT/usr/local/estate/sbin" "$ROOT/Library/LaunchDaemons" "$SCRIPTS" "$RESOURCES"
install -m 0755 "$CONVERGE" "$ROOT/usr/local/estate/sbin/estate-converge"
install -m 0644 "$PKG/$LABEL.plist" "$ROOT/Library/LaunchDaemons/$LABEL.plist"
find "$ROOT" -type d -exec chmod 0755 {} +
install -m 0755 "$PKG/preinstall" "$PKG/postinstall" "$SCRIPTS/"
cp "$PKG/LICENSE" "$PKG/README" "$PKG/Conclusion" "$RESOURCES/"

pkgbuild --root "$ROOT" \
    --scripts "$SCRIPTS" \
    --identifier ai.estate.pkg \
    --version "$VERSION" \
    --ownership recommended \
    "$TMP/idp-estate.pkg" >/dev/null

productbuild --distribution "$PKG/Distribution.xml.in" \
    --package-path "$TMP" \
    --product "$PKG/idp-estate.plist" \
    --resources "$RESOURCES" \
    "$OUT" >/dev/null

echo "Built: $OUT"
