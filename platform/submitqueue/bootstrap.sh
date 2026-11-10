#!/usr/bin/env bash
# Reuse Uber's Apache-2.0 implementation pinned to an audited full commit.
# Never auto-switch IDP's release authority to a demo service.
set -euo pipefail
UPSTREAM=https://github.com/uber/submitqueue.git
PIN=694373f380bb405d562dd359f27832d6bdb120f0
TARGET="${SQ_WORKTREE:-${TMPDIR:-/tmp}/idp-uber-submitqueue}"
MODE="${1:-git}"
if [[ "$MODE" != git && "$MODE" != fake ]]; then
  echo "REFUSED: production GitHub provider requires approved protected-main adapter; this installer cannot confer privileges." >&2
  exit 3
fi
command -v git >/dev/null
command -v docker >/dev/null
if [[ ! -d "$TARGET/.git" ]]; then
  mkdir -p "$(dirname "$TARGET")"
  git clone --filter=blob:none --no-checkout "$UPSTREAM" "$TARGET"
fi
git -C "$TARGET" fetch --no-tags origin "$PIN"
git -C "$TARGET" checkout -f --detach "$PIN"
actual="$(git -C "$TARGET" rev-parse HEAD)"
[[ "$actual" == "$PIN" ]] || { echo "REFUSED: upstream pin mismatch" >&2; exit 4; }
echo "UPSTREAM_PROVEN_REV=$actual PROVIDER=$MODE"
# Only explicit test harness; the full upstream service boots, not a local clone of
# its algorithms. No GitHub token, no production mutation and no fake CI certification.
cd "$TARGET"
PROVIDER="$MODE" make local-submitqueue-start
