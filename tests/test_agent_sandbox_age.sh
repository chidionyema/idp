#!/usr/bin/env bash
# Regression for the Legion cloud runner's age bootstrap (IDP #7972).
set -euo pipefail
cd "$(dirname "$0")/.."

workflow=.github/workflows/agent-sandbox.yml
installer=bin/agent-sandbox-age

# All three trusted jobs must use the identical pinned bootstrap.
count="$(grep -Fc 'bash bin/agent-sandbox-age' "$workflow" || true)"
[[ "$count" = 3 ]] || { echo "FAIL: expected three pinned age installations; found $count"; exit 1; }
if grep -Eq 'apt-get (update|install).*age|apt-get install.*age' "$workflow"; then
  echo "FAIL: workflow still depends on Ubuntu age packages"
  exit 1
fi
grep -Fq 'cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10' "$installer"
grep -Fq 'sha256sum --check --status' "$installer"
grep -Fq 'https://github.com/FiloSottile/age/releases/download/' "$installer"

# A compromised/corrupted upstream archive must be refused before sudo/install.
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/bin"
cat > "$scratch/bin/curl" <<'FAKE_CURL'
#!/usr/bin/env bash
set -euo pipefail
while (( $# )); do
  if [[ "$1" == "--output" ]]; then
    printf 'TAMPERED-AGE-BINARY' > "$2"
    exit 0
  fi
  shift
done
exit 9
FAKE_CURL
cat > "$scratch/bin/sudo" <<'FAKE_SUDO'
#!/usr/bin/env bash
echo 'SUDO-WAS-REACHED' >> "$SUDO_MARKER"
exit 19
FAKE_SUDO
chmod +x "$scratch/bin/curl" "$scratch/bin/sudo"
rc=0
PATH="$scratch/bin:$PATH" SUDO_MARKER="$scratch/sudo-marker" \
  bash "$installer" > "$scratch/stdout" 2> "$scratch/stderr" || rc=$?
[[ "$rc" = 3 ]] || { echo "FAIL: tamper exited $rc instead of 3"; cat "$scratch/stderr"; exit 1; }
grep -Fq 'digest mismatch' "$scratch/stderr" || { cat "$scratch/stderr"; exit 1; }
[[ ! -e "$scratch/sudo-marker" ]] || { echo "FAIL: unverified binary reached sudo"; exit 1; }
echo 'PASS: three jobs pinned; tampered age archive refused before installation'
