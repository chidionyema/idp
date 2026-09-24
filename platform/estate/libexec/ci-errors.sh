#!/usr/bin/env bash
set -e
REPO="${CI_REPO:-chidionyema/idp}"

if [ -n "${CI_PR:-}" ]; then
  BRANCH=$(gh pr view "$CI_PR" --repo "$REPO" --json headRefName -q .headRefName)
  RUN=$(gh run list --repo "$REPO" --status failure --limit 1 \
    --field head_branch="$BRANCH" \
    --json databaseId -q '.[0].databaseId')
elif [ -z "${CI_RUN:-}" ]; then
  RUN=$(gh run list --repo "$REPO" --status failure --limit 1 \
    --json databaseId -q '.[0].databaseId')
else
  RUN="$CI_RUN"
fi

[ -n "$RUN" ] || { echo "no failing run found"; exit 1; }

echo "=== run $RUN ($REPO) ==="
gh run view "$RUN" --repo "$REPO" \
  --json displayTitle,headBranch,conclusion,url \
  -q '"[\(.conclusion)]  \(.headBranch)  \(.url)\n\(.displayTitle)"'
echo

echo "=== failing jobs/steps ==="
gh api "repos/$REPO/actions/runs/$RUN/jobs" \
  --jq '.jobs[] | select(.conclusion=="failure") | .name as $j | .steps[] | select(.conclusion=="failure") | "\($j)  ->  \(.name)"'
echo

echo "=== errors ==="
for JOB in $(gh api "repos/$REPO/actions/runs/$RUN/jobs" \
  --jq '.jobs[] | select(.conclusion=="failure") | .id'); do
  JOB_NAME=$(gh api "repos/$REPO/actions/jobs/$JOB" --jq '.name')
  echo "--- $JOB_NAME ---"
  gh api "repos/$REPO/actions/jobs/$JOB/logs" 2>/dev/null \
    | grep -nE 'FAIL|error:|Error|panic|AssertionError' \
    | grep -vE 'git clone|sig-notation|::|node_modules|xterm|HTMLCanvas' \
    | head -40
  echo
done
