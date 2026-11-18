#!/usr/bin/env bash
# Build the recovery-host bundle. The binary must be an x86_64 Linux static executable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BIN="${1:-$ROOT/target/x86_64-unknown-linux-musl/release/pennyd}"
OUT="${2:-$ROOT/target/recovery/pennyd-bundle.tgz}"
RECOVERY="$ROOT/deploy/recovery"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

file "$BIN" | grep -q 'ELF 64-bit.*x86-64.*statically linked' || {
  echo "refused: $BIN is not a static x86_64 Linux binary" >&2
  exit 2
}

install -m 0755 "$BIN" "$TMP/pennyd"
install -m 0755 "$RECOVERY/prepare-keys" "$TMP/prepare-keys"
install -m 0644 "$RECOVERY/pennyd.toml" "$TMP/pennyd.toml"
install -m 0644 "$RECOVERY/estate-pennyd.service" "$TMP/estate-pennyd.service"
mkdir -p "$TMP/providers"
for provider in zai minimax deepseek gemini groq openrouter; do
  sed '/^api_key_file =/d' "$ROOT/providers/$provider.toml" >"$TMP/providers/$provider.toml"
done

if command -v sha256sum >/dev/null 2>&1; then
  HASH=(sha256sum)
else
  HASH=(shasum -a 256)
fi
(cd "$TMP" && "${HASH[@]}" pennyd prepare-keys pennyd.toml estate-pennyd.service providers/*.toml >SHA256SUMS)
mkdir -p "$(dirname "$OUT")"
tar -czf "$OUT" -C "$TMP" .
echo "$OUT"
