#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# IDP Platform — Automated Branch Push & GitHub Pull Request Script
# Usage:
#   ./scripts/raise-pr.sh <GITHUB_REPO_URL> [BASE_BRANCH]
# Example:
#   ./scripts/raise-pr.sh git@github.com:your-org/idp-platform.git main
# ==============================================================================

REMOTE_URL="${1:-}"
BASE_BRANCH="${2:-main}"
BRANCH_NAME="feat/idp-architecture-roadmap-and-lanes"

if [ -z "$REMOTE_URL" ]; then
  echo "Usage: ./scripts/raise-pr.sh <GITHUB_REPO_URL> [BASE_BRANCH]"
  echo "Example: ./scripts/raise-pr.sh https://github.com/your-org/idp.git main"
  exit 1
fi

echo "==> Running unit tests before pushing..."
npx --yes tsx --test src/utils/roadmapLogic.test.ts

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi

git checkout -B "$BRANCH_NAME"
git add AGENTS.md PULL_REQUEST.md docs/ src/ index.html package.json tsconfig.json vite.config.ts

if ! git diff --cached --quiet; then
  git commit -m "feat(architecture): add IDP master roadmap, 5 critical lanes spec, and reference kernels"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi

echo "==> Pushing branch '$BRANCH_NAME' to $REMOTE_URL..."
git push -u origin "$BRANCH_NAME"

if command -v gh >/dev/null 2>&1; then
  echo "==> Creating Pull Request via GitHub CLI (gh)..."
  gh pr create \
    --base "$BASE_BRANCH" \
    --head "$BRANCH_NAME" \
    --title "feat(architecture): IDP Master Architecture Roadmap, 5 Critical Lanes Spec & Reference Kernels" \
    --body-file PULL_REQUEST.md
else
  echo "==> Branch pushed! Open a PR on GitHub using PULL_REQUEST.md as the description."
fi
