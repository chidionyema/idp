#!/usr/bin/env bash
set -euo pipefail

# Kimi Execution Contract — Argo Sync & GitOps Publisher
# Scope: IDP + Argon Genesis Estate

REPO_URL="${1:-${GITHUB_REPO_URL:-git@github.com:argon-genesis/capability-first-estate.git}}"
BRANCH="${2:-main}"

echo "=========================================================="
echo "  Kimi Capability-First Estate — Argo GitOps Sync"
echo "  Target Repo: ${REPO_URL}"
echo "  Target Branch: ${BRANCH}"
echo "=========================================================="

# 1. Verify working directory
if [ ! -d ".git" ]; then
  echo "Error: Not in a git repository."
  exit 1
fi

# 2. Run verification suite
echo "[1/4] Running authoritative unit tests & contract validation..."
npx tsx --test src/core/resolution.test.ts

echo "[2/4] Verifying TypeScript & Lint..."
npm run lint

# 3. Configure remote
echo "[3/4] Configuring Git remote 'origin' -> ${REPO_URL}..."
if git remote | grep -q "^origin$"; then
  git remote set-url origin "${REPO_URL}"
else
  git remote add origin "${REPO_URL}"
fi

# 4. Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
  echo "Committing pending estate manifests..."
  git add -A
  git commit -m "feat(argo): sync capability-first estate manifests and ArgoCD application"
fi

COMMIT_SHA=$(git rev-parse HEAD)
echo "[4/4] Prepared commit ${COMMIT_SHA} for branch ${BRANCH}."
echo ""
echo "To push to your private GitHub repository, run:"
echo "  git push -u origin ${BRANCH}"
echo ""
echo "ArgoCD will automatically reconcile via syncPolicy.automated:"
echo "  Application: kimi-capability-first-engine"
echo "  Manifest: deploy/argocd/application.yaml"
echo "=========================================================="
