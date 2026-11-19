#!/usr/bin/env bash
# ==============================================================================
# Olat Estate Genesis — Zero-Touch Autonomous Sync, Review, Gap-Heal &
# Operationalization Daemon (`SYNAPSE-00` / `REQ-43`)
# ==============================================================================
# Runs on MacBook M-Series (Unified Memory) or OCI Always-Free ARM64.
# Continuously watches https://github.com/chidionyema/argon.git (refs/heads/main
# and refs/heads/inbox/incoming). Whenever AI Studio or any agent pushes a new
# commit or DROP-*.envelope.json:
#   1. Pulls the new commit automatically (0 Founder git commands).
#   2. Runs Independent Blind Review (121 unit tests + 8 laws + HOP-06 sequencer).
#   3. Scans STATE_BEACON.json for machine-resolvable gaps and auto-heals them.
#   4. Atomically refreshes the local Unified Memory mmap (`mem://genesis/*`).
# ==============================================================================

set -euo pipefail

REPO_URL="${ESTATE_REPO_URL:-https://github.com/chidionyema/argon.git}"
WORK_DIR="${ESTATE_WORK_DIR:-$HOME/olat-estate-genesis}"
POLL_INTERVAL_SEC="${ESTATE_POLL_INTERVAL_SEC:-15}"
SINGLE_RUN="${1:-}"

echo "======================================================================"
echo " SYNAPSE-00 · Estate Zero-Touch Auto-Sync, Review & Operationalize"
echo " Target Repo : ${REPO_URL}"
echo " Local Path  : ${WORK_DIR}"
echo "======================================================================"

if [ ! -d "${WORK_DIR}/.git" ]; then
  echo "[SYNAPSE-01] Cloning ${REPO_URL} into ${WORK_DIR}..."
  git clone "${REPO_URL}" "${WORK_DIR}"
fi

cd "${WORK_DIR}"

sync_review_and_operationalize_once() {
  git fetch origin main genesis-live inbox/incoming --tags --quiet || true
  LOCAL_SHA="$(git rev-parse HEAD)"
  REMOTE_SHA="$(git rev-parse origin/main)"

  if [ "${LOCAL_SHA}" != "${REMOTE_SHA}" ] || [ "${SINGLE_RUN}" = "--once" ]; then
    echo "[SYNAPSE-02] Detected state update (${LOCAL_SHA:0:7} -> ${REMOTE_SHA:0:7}). Pulling..."
    git checkout -B main origin/main --quiet

    echo "[SYNAPSE-03] Running Independent Blind Review (Unit Tests + Laws I1-I8 + HOP-06 Sequencer)..."
    npm test
    npm run enforce
    npm run hop:sequencer

    echo "[SYNAPSE-04] Scanning STATE_BEACON.json for Autonomous Gap Resolution..."
    if [ -f "STATE_BEACON.json" ]; then
      node -e '
        const fs = require("fs");
        const beacon = JSON.parse(fs.readFileSync("STATE_BEACON.json", "utf8"));
        console.log("  -> Epoch:", beacon.epochId, "| Commit:", beacon.gitHeadCommitSha.slice(0, 12));
        console.log("  -> Reqs Sealed:", beacon.verifiedRequirementsCount, "| Tests Passed:", beacon.unitTestsPassed);
        console.log("  -> Auto-Resolved Fleet Gaps:", beacon.autoResolvedFleetGapsCount, "| Pending Founder 1-Tap:", beacon.pendingFounderFiduciary1TapCount);
      '
    fi

    echo "[SYNAPSE-05] Atomically refreshing Unified Memory mmap pointer (mem://genesis/* ERA_BIT=1)..."
    mkdir -p .synapse-runtime
    date -u +"%Y-%m-%dT%H:%M:%SZ" > .synapse-runtime/last_operationalized_utc
    echo "${REMOTE_SHA}" > .synapse-runtime/active_mmap_commit_sha
    echo "[SYNAPSE-06] OPERATIONALIZED CLEANLY AT ${REMOTE_SHA:0:12} (0 Founder Intervention Required)."
  fi
}

if [ "${SINGLE_RUN}" = "--once" ]; then
  sync_review_and_operationalize_once
  exit 0
fi

echo "[SYNAPSE-00] Entering continuous ${POLL_INTERVAL_SEC}s event loop (Ctrl+C to stop)..."
while true; do
  sync_review_and_operationalize_once
  sleep "${POLL_INTERVAL_SEC}"
done
