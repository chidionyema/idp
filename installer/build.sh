#!/bin/sh
# build-installer.sh — builds the IDP Estate .pkg GUI installer.
# Requires: pkgbuild, productbuild (both ship with macOS, no extra install needed).
#
# Run from the repo root:
#   bash installer/build.sh
#
# Output: installer/IDP-Estate.pkg  (double-click to install)
set -e

IDP="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$IDP/installer"
TMP="$(mktemp -d)"
ROOT="$TMP/root"
SCRIPTS="$TMP/scripts"
DIST="$PKG/Distribution.xml"
PRODUCT_PLIST="$PKG/idp-estate.plist"

echo "=== Building IDP Estate .pkg installer ==="

# Clean
rm -rf "$ROOT" "$SCRIPTS"
mkdir -p "$ROOT/usr/local/bin" "$ROOT/Library/LaunchAgents" "$SCRIPTS"

# Copy payload
cp "$IDP/bin/idp-install-all" "$ROOT/usr/local/bin/"
chmod 755 "$ROOT/usr/local/bin/idp-install-all"

# Copy fleetview-backend launchd plist
if [ -f "$IDP/launchd/ai.estate.fleetview-backend.plist.tmpl" ]; then
    # Render template
    PYTHON_BIN="$(command -v python3.12 || command -v python3 || echo python3)"
    IDP="$IDP" HOME="$HOME" PATH="$PATH" TEMPORAL_BIN="" \
        envsubst '${IDP} ${HOME} ${PATH} ${TEMPORAL_BIN} ${PYTHON_BIN}' \
        < "$IDP/launchd/ai.estate.fleetview-backend.plist.tmpl" \
        > "$ROOT/Library/LaunchAgents/ai.estate.fleetview-backend.plist"
else
    echo "WARNING: no launchd template found at $IDP/launchd/"
fi

# Postinstall script
cat > "$SCRIPTS/postinstall" << 'POSTINSTALL'
#!/bin/sh
set -e
IDP="${IDP:-/usr/local/idp}"
STATE="${ESTATE_HOME:-$HOME/.estate}"

mkdir -p "$STATE/bin" "$STATE/intents" "$STATE/libexec" "$STATE/logs" 2>/dev/null || true

# Load fleetview-backend launchd agent
if [ -f "$HOME/Library/LaunchAgents/ai.estate.fleetview-backend.plist" ]; then
    launchctl bootout "gui/$(id -u)/ai.estate.fleetview-backend" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" \
        "$HOME/Library/LaunchAgents/ai.estate.fleetview-backend.plist" 2>/dev/null || true
    echo "fleetview-backend launchd agent loaded."
fi

# Make idp-install-all world-executable
chmod 755 /usr/local/bin/idp-install-all 2>/dev/null || true
echo "IDP Estate installed. Run /usr/local/bin/idp-install-all for full bootstrap."
POSTINSTALL
chmod +x "$SCRIPTS/postinstall"

# GUI assets
cp "$PKG/LICENSE" "$TMP/LICENSE" 2>/dev/null || true
cp "$PKG/README" "$TMP/README" 2>/dev/null || true
cp "$PKG/Conclusion" "$TMP/Conclusion" 2>/dev/null || true

# Distribution XML
cp "$DIST" "$TMP/Distribution.xml" 2>/dev/null || {
    echo "ERROR: Distribution.xml not found at $DIST"
    echo "Copy installer/Distribution.xml.in to installer/Distribution.xml and edit paths."
    exit 1
}

# Build component package
COMPONENT="$TMP/idp-estate.pkg"
pkgbuild --root "$ROOT" \
    --scripts "$SCRIPTS" \
    --identifier ai.estate.pkg \
    --version 0.1.0 \
    --ownership preserve \
    "$COMPONENT"

# Build product (GUI installer)
productbuild --distribution "$TMP/Distribution.xml" \
    --package-path "$TMP" \
    --product "$PRODUCT_PLIST" \
    --resources "$TMP" \
    "$PKG/IDP-Estate.pkg"

echo ""
echo "Built: $PKG/IDP-Estate.pkg"
ls -lh "$PKG/IDP-Estate.pkg"
echo ""
echo "To install: double-click IDP-Estate.pkg, or:"
echo "  sudo installer -pkg $PKG/IDP-Estate.pkg -target /"
