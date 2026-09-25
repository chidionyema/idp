#!/bin/sh
# build-installer.sh — builds the IDP Estate .pkg GUI installer.
# Requires: pkgbuild, productbuild (ship with macOS, no extra install needed).
#
# Usage:
#   IDP=/path/to/idp bash installer/build.sh
#   Or run from repo root: bash installer/build.sh
#
set -e

# Resolve the repo root: script is at <IDP>/installer/build.sh
# When run from <IDP>/: SCRIPT_DIR = <IDP>/installer, IDP = <IDP>
# Use realpath for reliable resolution regardless of CWD.
SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
IDP="${IDP:-$SCRIPT_DIR}"

PKG="$IDP/installer"
TMP="$(mktemp -d)"
ROOT="$TMP/root"
SCRIPTS="$TMP/scripts"
DIST="$PKG/Distribution.xml.in"
PRODUCT_PLIST="$PKG/idp-estate.plist"

echo "=== Building IDP Estate .pkg installer ==="
echo "IDP: $IDP"
echo "Output: $PKG/IDP-Estate.pkg"

# Verify sources exist
if [ ! -f "$IDP/bin/idp-install-all" ]; then
    echo "ERROR: $IDP/bin/idp-install-all not found"
    echo "This script must be run from a checkout that includes the fleetview_backend restructure."
    exit 1
fi
if [ ! -f "$DIST" ]; then
    echo "ERROR: $DIST not found"
    exit 1
fi

# Clean build dirs
rm -rf "$ROOT" "$SCRIPTS"
mkdir -p "$ROOT/usr/local/bin" "$ROOT/Library/LaunchAgents" "$SCRIPTS"

# Payload: idp-install-all
cp "$IDP/bin/idp-install-all" "$ROOT/usr/local/bin/"
chmod 755 "$ROOT/usr/local/bin/idp-install-all"

# Payload: launchd plist (render template if available)
if [ -f "$IDP/launchd/ai.estate.fleetview-backend.plist.tmpl" ]; then
    PYTHON_BIN="$(command -v python3.12 || command -v python3 || echo python3)"
    IDP="$IDP" HOME="$HOME" PATH="$PATH" TEMPORAL_BIN="" PYTHON_BIN="$PYTHON_BIN" \
        envsubst '${IDP} ${HOME} ${PATH} ${TEMPORAL_BIN} ${PYTHON_BIN}' \
        < "$IDP/launchd/ai.estate.fleetview-backend.plist.tmpl" \
        > "$ROOT/Library/LaunchAgents/ai.estate.fleetview-backend.plist"
    echo "  rendered launchd plist from template"
elif [ -f "$HOME/Library/LaunchAgents/ai.estate.fleetview-backend.plist" ]; then
    cp "$HOME/Library/LaunchAgents/ai.estate.fleetview-backend.plist" \
       "$ROOT/Library/LaunchAgents/"
    echo "  copied existing launchd plist"
fi

# Postinstall script
cat > "$SCRIPTS/postinstall" << 'POSTINSTALL'
#!/bin/sh
set -e
IDP="${IDP:-/usr/local/idp}"
STATE="${ESTATE_HOME:-$HOME/.estate}"

# Create estate state dirs
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
echo "IDP Estate installed."
POSTINSTALL
chmod +x "$SCRIPTS/postinstall"

# Copy GUI assets
cp "$PKG/LICENSE" "$TMP/LICENSE" 2>/dev/null || true
cp "$PKG/README" "$TMP/README" 2>/dev/null || true
cp "$PKG/Conclusion" "$TMP/Conclusion" 2>/dev/null || true

# Copy Distribution.xml
cp "$DIST" "$TMP/Distribution.xml"

# Build component package (.pkg)
COMPONENT="$TMP/idp-estate.pkg"
pkgbuild --root "$ROOT" \
    --scripts "$SCRIPTS" \
    --identifier ai.estate.pkg \
    --version 0.1.0 \
    --ownership preserve \
    "$COMPONENT"
echo "  component package built"

# Build product (GUI .pkg with installer wizard)
productbuild --distribution "$TMP/Distribution.xml" \
    --package-path "$TMP" \
    --product "$PRODUCT_PLIST" \
    --resources "$TMP" \
    "$PKG/IDP-Estate.pkg"

echo ""
echo "Built: $PKG/IDP-Estate.pkg"
ls -lh "$PKG/IDP-Estate.pkg"
echo ""
echo "To install: double-click IDP-Estate.pkg"
echo "Or:         sudo installer -pkg $PKG/IDP-Estate.pkg -target /"
