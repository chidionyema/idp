#!/bin/sh
# Installs persistent Git remotes and background post-commit auto-push inside .git/
# so credentials survive Cloud Run container restarts & chat compaction without
# polluting tracked files in the repository working tree.
#
# Usage:
#   GITHUB_TOKEN=<your_fine_grained_pat> ./scripts/install-persistent-git-uplink.sh
#
set -eu

TOKEN="${1:-${GITHUB_TOKEN:-}}"
BRANCH_REF="${CRESCENDO_UPLINK_REF:-refs/heads/aistudio/meridian-hermes-live}"

if [ -z "$TOKEN" ]; then
  echo "Error: Provide a fine-grained PAT via GITHUB_TOKEN env var or first argument." >&2
  echo "Example: GITHUB_TOKEN=github_pat_... $0" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config remote.argon-sync.url "https://x-access-token:${TOKEN}@github.com/chidionyema/argon-sync.git"
git config remote.gemini-sync.url "https://x-access-token:${TOKEN}@github.com/chidionyema/gemini-sync.git"

HOOK_PATH="$REPO_ROOT/.git/hooks/post-commit"
cat > "$HOOK_PATH" <<EOF
#!/bin/sh
git push -f argon-sync HEAD:${BRANCH_REF} >/dev/null 2>&1 &
git push -f gemini-sync HEAD:${BRANCH_REF} >/dev/null 2>&1 &
EOF
chmod +x "$HOOK_PATH"

echo "Persistent .git/config remotes & post-commit hook installed."
echo "Pushing HEAD ($(git rev-parse --short HEAD)) -> ${BRANCH_REF}..."
git push -f argon-sync "HEAD:${BRANCH_REF}"
git push -f gemini-sync "HEAD:${BRANCH_REF}"
echo "Verified remotes:"
git ls-remote argon-sync "${BRANCH_REF}"
git ls-remote gemini-sync "${BRANCH_REF}"
