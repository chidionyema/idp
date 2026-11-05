#!/bin/bash
# Restore a verified Node.js runtime for Pi without depending on nvm or sudo.
# Safe to rerun; backs up existing launchers. Designed for macOS 11+.
set -Eeuo pipefail
trap 'rc=$?; echo "ERROR: repair stopped at line $LINENO (exit $rc)" >&2' ERR
fail() { printf 'BLOCKED: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = Darwin ] || fail 'This installer is for macOS only.'
OS=$(/usr/bin/sw_vers -productVersion)
IFS=. read -r OS_MAJOR OS_MINOR OS_PATCH <<< "$OS"
OS_MINOR=${OS_MINOR:-0}
case "$(uname -m)" in
  arm64) ARCH=arm64 ;;
  x86_64) ARCH=x64 ;;
  *) fail "Unsupported processor: $(uname -m)" ;;
esac

if (( OS_MAJOR > 13 || (OS_MAJOR == 13 && OS_MINOR >= 5) )); then
  VERSION=v24.22.2
elif (( OS_MAJOR >= 11 )); then
  VERSION=v22.23.4
else
  fail "macOS $OS cannot run the official Node 22/24 binary required by current Pi. OS upgrade or a separately supported runtime is necessary; no changes made."
fi

ROOT="$HOME/.local/opt/pinned-node"
RUNTIME="$ROOT/$VERSION"
BIN="$HOME/.local/bin"
BACKUP="$HOME/.local/share/pi-node-repair/$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$ROOT" "$BIN" "$BACKUP"

printf 'Mac: %s | CPU: %s | pinned Node: %s\n' "$OS" "$ARCH" "$VERSION"

if [ ! -x "$RUNTIME/bin/node" ] || [ "$("$RUNTIME/bin/node" --version 2>/dev/null || true)" != "$VERSION" ]; then
  echo 'Downloading and verifying official Node release...'
  WORK=$(mktemp -d "$ROOT/.download.XXXXXXXX")
  trap 'rc=$?; rm -rf "$WORK"; if [ "$rc" -ne 0 ]; then echo "ERROR: repair stopped before completion (exit $rc)" >&2; fi' EXIT
  PACKAGE="node-$VERSION-darwin-$ARCH"
  BASE="https://nodejs.org/dist/$VERSION"
  /usr/bin/curl -fLsS --retry 3 --connect-timeout 15 "$BASE/$PACKAGE.tar.gz" -o "$WORK/$PACKAGE.tar.gz" || fail 'Node archive download failed'
  /usr/bin/curl -fLsS --retry 3 --connect-timeout 15 "$BASE/SHASUMS256.txt" -o "$WORK/SHASUMS256.txt" || fail 'Node checksum download failed'
  EXPECTED=$(/usr/bin/awk -v f="$PACKAGE.tar.gz" '$2==f {print $1; exit}' "$WORK/SHASUMS256.txt")
  [ -n "$EXPECTED" ] || fail 'Official checksum was not found'
  ACTUAL=$(/usr/bin/shasum -a 256 "$WORK/$PACKAGE.tar.gz" | /usr/bin/awk '{print $1}')
  [ "$ACTUAL" = "$EXPECTED" ] || fail 'Checksum mismatch. Refusing installation'
  /usr/bin/tar -xzf "$WORK/$PACKAGE.tar.gz" -C "$WORK" || fail 'Archive extraction failed'
  CANDIDATE="$WORK/$PACKAGE"
  [ -x "$CANDIDATE/bin/node" ] || fail 'Downloaded Node executable missing'
  [ "$("$CANDIDATE/bin/node" --version 2>/dev/null || true)" = "$VERSION" ] || fail "Node binary cannot run on macOS $OS"
  if [ -e "$RUNTIME" ]; then mv "$RUNTIME" "$BACKUP/runtime-previous"; fi
  mv "$CANDIDATE" "$RUNTIME"
  rm -rf "$WORK"
  trap - EXIT
fi

[ "$("$RUNTIME/bin/node" --version)" = "$VERSION" ] || fail 'Pinned Node verification failed'

# Put node next to pi. Pi's existing launcher uses `exec node ...`.
# Back up old files/symlinks, including broken symlinks, before replacement.
for CMD in node npm npx; do
  SOURCE="$RUNTIME/bin/$CMD"
  [ -e "$SOURCE" ] || fail "Missing $SOURCE"
  TARGET="$BIN/$CMD"
  if [ -d "$TARGET" ] && [ ! -L "$TARGET" ]; then fail "$TARGET is a directory; refusing to replace"; fi
  if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then mv "$TARGET" "$BACKUP/$CMD"; fi
  ln -s "$SOURCE" "$TARGET"
done

# Idempotent PATH repair for login and interactive Bash/Zsh sessions.
LINE='export PATH="$HOME/.local/bin:$PATH" # pinned-node-for-pi'
for PROFILE in "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.zprofile" "$HOME/.zshrc"; do
  [ -e "$PROFILE" ] || : > "$PROFILE"
  grep -Fqx "$LINE" "$PROFILE" || printf '\n%s\n' "$LINE" >> "$PROFILE"
done

export PATH="$BIN:$PATH"
hash -r
[ "$(node --version)" = "$VERSION" ] || fail 'Current PATH resolves another Node'
command -v pi >/dev/null || fail 'Pi launcher not found on PATH; Node is repaired but Pi needs a separate reinstall'
pi --version || fail 'Pi itself failed its version check'

# Explicitly test actual new interactive login processes, not just this terminal.
export EXPECTED_NODE_VERSION="$VERSION"
BASH_OUTPUT=$(/bin/bash -lic 'test "$(node --version)" = "$EXPECTED_NODE_VERSION" && pi --version && echo PI_BASH_VERIFIED' 2>&1) || fail 'Fresh Bash failed; inspect Bash startup configuration'
case "$BASH_OUTPUT" in *PI_BASH_VERIFIED*) ;; *) fail 'Fresh Bash did not execute verification commands' ;; esac
ZSH_OUTPUT=$(/bin/zsh -lic 'test "$(node --version)" = "$EXPECTED_NODE_VERSION" && pi --version && echo PI_ZSH_VERIFIED' 2>&1) || fail 'Fresh Zsh failed; inspect Zsh startup configuration'
case "$ZSH_OUTPUT" in *PI_ZSH_VERIFIED*) ;; *) fail 'Fresh Zsh did not execute verification commands' ;; esac

printf '\nPASS: Pi and Node verified in the current terminal, fresh Bash, and fresh Zsh.\n'
printf 'Node: %s\n' "$RUNTIME/bin/node"
printf 'Backups: %s\n' "$BACKUP"
printf 'Existing Pi installation left unchanged.\n'
