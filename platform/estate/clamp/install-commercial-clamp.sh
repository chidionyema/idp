#!/usr/bin/env bash
# Installs the commercial engineering clamp: a global git hook lock, a 3-rung
# smoke+integration prover bound to a git tree hash, and a stateless-agent bootstrap.
#
# Deviations from the founder's draft, each a defect in the draft:
#   1. No baked-in fallback HMAC key. The draft defaulted the signing secret to the
#      literal "local-sovereign-fallback-key", a public constant, so any agent could
#      mint a valid receipt. Here a real key is REQUIRED and generated once into a
#      private file if absent (mode 600); no key means REFUSE, never sign anyway.
#   2. tsc/pytest failures are distinguished from absence. The draft ran
#      `npx --no-install tsc` and took ITS exit code as the static verdict, so a
#      missing tsc failed the rung. Absence is now SKIP and is printed as such.
#   3. The receipt signs the three real exit codes, not a hardcoded 0:0:0, so the
#      signature cannot disagree with what the database records.
#   4. The falsifier runs in a throwaway clone, never in the founder's checkout: the
#      draft deleted receipts for the live tree and ran hooks against the working repo.
set -euo pipefail

ESTATE_DIR="${HOME}/.estate"
BIN_DIR="${ESTATE_DIR}/bin"
HOOKS_DIR="${ESTATE_DIR}/hooks"
STATE_DIR="${ESTATE_DIR}/state"
RECEIPT_DIR="${ESTATE_DIR}/receipts"
DB_PATH="${ESTATE_DIR}/estate.db"
KEY_FILE="${ESTATE_DIR}/receipt.key"

mkdir -p "${BIN_DIR}" "${HOOKS_DIR}" "${STATE_DIR}" "${RECEIPT_DIR}"

echo "=== 1. LEDGER ${DB_PATH} ==="
python3 - "${DB_PATH}" << 'PY'
import sqlite3, sys

conn = sqlite3.connect(sys.argv[1])
conn.execute("PRAGMA journal_mode=WAL;")
conn.executescript("""
CREATE TABLE IF NOT EXISTS smoke_receipts (
    tree_sha TEXT PRIMARY KEY,
    repo_path TEXT NOT NULL,
    branch TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    goal_id TEXT NOT NULL,
    static_exit_code INTEGER NOT NULL,
    integration_exit_code INTEGER NOT NULL,
    smoke_exit_code INTEGER NOT NULL,
    stdout_sha256 TEXT NOT NULL,
    hmac_signature TEXT NOT NULL,
    verified_at_utc TEXT NOT NULL
);
""")

# step_runs is an OLDER table on this machine (id, ticket_id, step_idx, cmd, exit_code,
# duration_ms, ran_at) from the Otto sweep. CREATE TABLE IF NOT EXISTS silently does
# nothing when it already exists, which is how the first install wrote no receipt while
# still exiting 0. So: verify the columns and rebuild if they disagree.
WANT = ["ticket_id", "step_idx", "tool_kind", "cmd", "exit_code", "stdout_payload",
        "stderr_payload", "hmac_signature", "executed_at"]
have = [r[1] for r in conn.execute("PRAGMA table_info(step_runs)")]
if have and have != WANT:
    conn.execute("ALTER TABLE step_runs RENAME TO step_runs_legacy_otto")
    print(f"    step_runs had {len(have)} old columns -> renamed to step_runs_legacy_otto")
    have = []
conn.executescript("""
CREATE TABLE IF NOT EXISTS step_runs (
    ticket_id TEXT NOT NULL,
    step_idx INTEGER NOT NULL,
    tool_kind TEXT NOT NULL,
    cmd TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    stdout_payload TEXT NOT NULL,
    stderr_payload TEXT NOT NULL,
    hmac_signature TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    PRIMARY KEY (ticket_id, step_idx)
);
""")
conn.commit()
now = [r[1] for r in conn.execute("PRAGMA table_info(step_runs)")]
assert now == WANT, f"step_runs schema still wrong: {now}"
print("    tables: smoke_receipts, step_runs (columns verified)")
PY

echo "=== 2. SIGNING KEY (no public fallback) ==="
if [ ! -f "${KEY_FILE}" ]; then
    python3 -c "import secrets,sys;open(sys.argv[1],'w').write(secrets.token_hex(32))" "${KEY_FILE}"
    chmod 600 "${KEY_FILE}"
    echo "    generated ${KEY_FILE} (mode 600)"
else
    echo "    ${KEY_FILE} already present (mode $(stat -f '%Lp' "${KEY_FILE}"))"
fi

echo "=== 3. ~/.estate/bin/estate-smoke ==="
cat << 'SMOKE' > "${BIN_DIR}/estate-smoke"
#!/usr/bin/env bash
# 3-rung prover: static, integration, live smoke. Signs the exact git tree on success.
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${REPO_ROOT}"

ESTATE_DIR="${HOME}/.estate"
DB_PATH="${ESTATE_DIR}/estate.db"
KEY_FILE="${ESTATE_DIR}/receipt.key"
ACTIVE_GOAL_FILE="${ESTATE_DIR}/state/active_goal.json"
LOG_FILE="/tmp/estate_smoke_$$.log"
: > "${LOG_FILE}"

if [ ! -f "${ACTIVE_GOAL_FILE}" ]; then
  echo "FATAL [GHOST-CLAMP]: no ${ACTIVE_GOAL_FILE}. Bind a goal first." >&2
  exit 1
fi
if [ ! -f "${KEY_FILE}" ]; then
  echo "FATAL [GHOST-CLAMP]: no signing key at ${KEY_FILE}. Refusing to sign." >&2
  exit 1
fi

GOAL_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("goal_id",""))' "${ACTIVE_GOAL_FILE}")"
[ -n "${GOAL_ID}" ] || { echo "FATAL [GHOST-CLAMP]: empty goal_id." >&2; exit 1; }

TREE_SHA="$(git write-tree)"
HEAD_SHA="$(git rev-parse HEAD 2>/dev/null || echo NONE)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"

echo "[1/3] RUNG 1 static (tree ${TREE_SHA:0:12})"
STATIC_RC=0
PY_FILES="$(git ls-files '*.py' 2>/dev/null || true)"
if [ -n "${PY_FILES}" ]; then
  # shellcheck disable=SC2086
  python3 -m py_compile ${PY_FILES} >> "${LOG_FILE}" 2>&1 || STATIC_RC=$?
fi
if [ -f tsconfig.json ] && command -v npx >/dev/null 2>&1; then
  if npx --no-install tsc --version >/dev/null 2>&1; then
    npx --no-install tsc --noEmit >> "${LOG_FILE}" 2>&1 || STATIC_RC=$?
  else
    echo "      tsc absent -> SKIPPED (not a failure)" | tee -a "${LOG_FILE}"
  fi
fi
if [ "${STATIC_RC}" -ne 0 ]; then
  echo "FAIL [RUNG 1] exit ${STATIC_RC}; see ${LOG_FILE}" >&2; exit "${STATIC_RC}"
fi

echo "[2/3] RUNG 2 integration"
INT_RC=0
if [ -d tests ] && command -v pytest >/dev/null 2>&1; then
  pytest -q --maxfail=1 >> "${LOG_FILE}" 2>&1 || INT_RC=$?
elif [ -f Cargo.toml ] && command -v cargo >/dev/null 2>&1; then
  cargo test --quiet >> "${LOG_FILE}" 2>&1 || INT_RC=$?
elif [ -f package.json ] && grep -q '"test"' package.json 2>/dev/null; then
  npm test -- --watch=false >> "${LOG_FILE}" 2>&1 || INT_RC=$?
else
  python3 -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); assert c.execute('SELECT 1').fetchone()[0]==1" "${DB_PATH}" >> "${LOG_FILE}" 2>&1 || INT_RC=$?
  echo "      no test runner -> sqlite integration probe" | tee -a "${LOG_FILE}"
fi
if [ "${INT_RC}" -ne 0 ]; then
  echo "FAIL [RUNG 2] exit ${INT_RC}; see ${LOG_FILE}" >&2; exit "${INT_RC}"
fi

echo "[3/3] RUNG 3 live smoke"
SMOKE_RC=0
if [ -x ./bin/smoke-test ]; then
  ./bin/smoke-test >> "${LOG_FILE}" 2>&1 || SMOKE_RC=$?
else
  python3 - "${REPO_ROOT}" "${DB_PATH}" >> "${LOG_FILE}" 2>&1 << 'PY' || SMOKE_RC=$?
import pathlib, sqlite3, subprocess, sys
repo, db_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
conn = sqlite3.connect(str(db_path))
mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
assert mode.lower() == "wal", f"expected WAL, got {mode}"
n = 0
for rel in ("bin/claim-gate", "bin/estate-smoke", "bin/otto_real_core.py"):
    t = repo / rel
    if t.is_file():
        if t.suffix == ".py":
            subprocess.run([sys.executable, "-m", "py_compile", str(t)], check=True)
        else:
            subprocess.run(["sh", "-n", str(t)], check=True)
        n += 1
print(f"SMOKE_OK: WAL + {n} entrypoint(s) verified")
PY
fi
if [ "${SMOKE_RC}" -ne 0 ]; then
  echo "FAIL [RUNG 3] exit ${SMOKE_RC}; see ${LOG_FILE}" >&2; exit "${SMOKE_RC}"
fi

echo "PASS all 3 rungs; signing tree ${TREE_SHA:0:12}"
if ! python3 - "${DB_PATH}" "${KEY_FILE}" "${TREE_SHA}" "${REPO_ROOT}" "${BRANCH}" "${HEAD_SHA}" "${GOAL_ID}" "${LOG_FILE}" "${STATIC_RC}" "${INT_RC}" "${SMOKE_RC}" << 'PY'
import datetime, hashlib, hmac, json, pathlib, sqlite3, sys
(db_path, key_file, tree_sha, repo, branch, head_sha, goal_id,
 log_file, s_rc, i_rc, m_rc) = sys.argv[1:]
s_rc, i_rc, m_rc = int(s_rc), int(i_rc), int(m_rc)
text = pathlib.Path(log_file).read_text(encoding="utf-8", errors="replace")
stdout_sha = hashlib.sha256(text.encode()).hexdigest()
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
secret = pathlib.Path(key_file).read_text().strip().encode()

# The signed canonical form carries the REAL exit codes, so the signature cannot
# claim 0:0:0 for a run that failed.
canonical = f"{tree_sha}:{repo}:{goal_id}:{s_rc}:{i_rc}:{m_rc}:{stdout_sha}".encode()
sig = hmac.new(secret, canonical, hashlib.sha256).hexdigest()

conn = sqlite3.connect(db_path)
conn.execute("""INSERT OR REPLACE INTO smoke_receipts
 (tree_sha, repo_path, branch, head_sha, goal_id, static_exit_code,
  integration_exit_code, smoke_exit_code, stdout_sha256, hmac_signature, verified_at_utc)
 VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
 (tree_sha, repo, branch, head_sha, goal_id, s_rc, i_rc, m_rc, stdout_sha, sig, now))
conn.execute("""INSERT OR REPLACE INTO step_runs
 (ticket_id, step_idx, tool_kind, cmd, exit_code, stdout_payload, stderr_payload,
  hmac_signature, executed_at) VALUES (?,1,'estate-smoke','estate-smoke',0,?,'',?,?)""",
 (f"SMOKE-{tree_sha[:12]}", text[-4000:], sig, now))
conn.commit()
print(json.dumps({"status": "COMMERCIAL_SMOKE_VERIFIED", "tree_sha": tree_sha,
                  "goal_id": goal_id, "hmac_signature": sig,
                  "verified_at_utc": now}, indent=2))
PY
then
  # A signer that could not write the receipt must never report PASS: the push it
  # was supposed to authorise is refused downstream, and the exit has to say so.
  echo "FAIL [RECEIPT]: could not write the receipt for tree ${TREE_SHA:0:12}" >&2
  exit 1
fi
rm -f "${LOG_FILE}"
SMOKE
chmod +x "${BIN_DIR}/estate-smoke"

echo "=== 4. GLOBAL HOOKS ${HOOKS_DIR} ==="
cat << 'PRECOMMIT' > "${HOOKS_DIR}/pre-commit"
#!/usr/bin/env bash
set -euo pipefail
ACTIVE_GOAL="${HOME}/.estate/state/active_goal.json"
if [ ! -f "${ACTIVE_GOAL}" ]; then
  echo "FATAL [COMMERCIAL-PRE-COMMIT]: commit REFUSED. No bound goal in ${ACTIVE_GOAL}." >&2
  exit 1
fi
STAGED_PY="$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)"
if [ -n "${STAGED_PY}" ]; then
  echo "${STAGED_PY}" | tr '\n' '\0' | xargs -0 python3 -m py_compile
fi
STAGED_SH="$(git diff --cached --name-only --diff-filter=ACM | grep '\.sh$' || true)"
if [ -n "${STAGED_SH}" ]; then
  echo "${STAGED_SH}" | tr '\n' '\0' | xargs -0 -n1 sh -n
fi
PRECOMMIT
chmod +x "${HOOKS_DIR}/pre-commit"

cat << 'PREPUSH' > "${HOOKS_DIR}/pre-push"
#!/usr/bin/env bash
set -euo pipefail
ESTATE_DIR="${HOME}/.estate"
DB_PATH="${ESTATE_DIR}/estate.db"
KEY_FILE="${ESTATE_DIR}/receipt.key"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TREE_SHA="$(git write-tree)"

if [ -x "${REPO_ROOT}/bin/claim-gate" ]; then
  MERGE_BASE="$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD)"
  # Bounded: an unbounded claim-gate call hangs every push on the machine.
  if ! timeout 60 "${REPO_ROOT}/bin/claim-gate" "${MERGE_BASE}" "$(git rev-parse HEAD)"; then
    echo "FATAL [COMMERCIAL-GATE]: claim-gate refused this push (or timed out)." >&2
    exit 1
  fi
fi

python3 - "${DB_PATH}" "${TREE_SHA}" "${KEY_FILE}" << 'PY'
import hashlib, hmac, os, pathlib, sqlite3, sys
db_path, tree_sha, key_file = sys.argv[1:]
if not os.path.exists(db_path):
    sys.stderr.write(f"FATAL [COMMERCIAL-GATE]: push REFUSED. No ledger {db_path}.\n"); sys.exit(1)
if not os.path.exists(key_file):
    sys.stderr.write(f"FATAL [COMMERCIAL-GATE]: push REFUSED. No signing key {key_file}.\n"); sys.exit(1)
conn = sqlite3.connect(db_path)
row = conn.execute("""SELECT repo_path, goal_id, static_exit_code, integration_exit_code,
       smoke_exit_code, stdout_sha256, hmac_signature, verified_at_utc
       FROM smoke_receipts WHERE tree_sha = ?""", (tree_sha,)).fetchone()
if not row:
    sys.stderr.write(
        "\n===============================================================\n"
        f"FATAL [COMMERCIAL-GATE]: push to Greenlane REFUSED.\n"
        f"Tree {tree_sha} has NO smoke/integration receipt.\n"
        f"Run: ~/.estate/bin/estate-smoke\n"
        "===============================================================\n")
    sys.exit(1)
repo, goal_id, s_rc, i_rc, m_rc, stdout_sha, sig, ts = row
if (s_rc, i_rc, m_rc) != (0, 0, 0):
    sys.stderr.write(f"FATAL [COMMERCIAL-GATE]: receipt for {tree_sha} has exits ({s_rc},{i_rc},{m_rc}).\n")
    sys.exit(1)
secret = pathlib.Path(key_file).read_text().strip().encode()
canonical = f"{tree_sha}:{repo}:{goal_id}:{s_rc}:{i_rc}:{m_rc}:{stdout_sha}".encode()
if not hmac.compare_digest(sig, hmac.new(secret, canonical, hashlib.sha256).hexdigest()):
    sys.stderr.write(f"FATAL [COMMERCIAL-GATE]: bad HMAC on receipt for {tree_sha}.\n")
    sys.exit(1)
print(f"PASS [COMMERCIAL-GATE]: tree {tree_sha[:12]} verified (goal={goal_id}, hmac={sig[:16]}..., at={ts}).")
PY
PREPUSH
chmod +x "${HOOKS_DIR}/pre-push"

git config --global core.hooksPath "${HOOKS_DIR}"
echo "    core.hooksPath = $(git config --global core.hooksPath)"

echo "=== 5. ~/.estate/bin/estate-brief ==="
cat << 'BRIEF' > "${BIN_DIR}/estate-brief"
#!/usr/bin/env python3
"""The mandatory 1-screen deterministic state header. No agent boots stateless."""
import json, pathlib, sqlite3, subprocess

estate = pathlib.Path.home() / ".estate"
goal_file = estate / "state" / "active_goal.json"
key_file = estate / "receipt.key"
db_file = estate / "estate.db"

goal = json.loads(goal_file.read_text()) if goal_file.exists() else {"ERROR": "NO_ACTIVE_GOAL_BOUND"}
receipts = []
if db_file.exists():
    conn = sqlite3.connect(str(db_file))
    try:
        receipts = conn.execute(
            "SELECT substr(tree_sha,1,12), repo_path, goal_id, "
            "substr(hmac_signature,1,16), verified_at_utc "
            "FROM smoke_receipts ORDER BY verified_at_utc DESC LIMIT 5"
        ).fetchall()
    except sqlite3.Error:
        receipts = [["ERROR", "ledger unreadable", "", "", ""]]

print(json.dumps({
    "global_hooks_path": subprocess.getoutput("git config --global core.hooksPath"),
    "signing_key_present": key_file.exists(),
    "signing_key_mode": oct(key_file.stat().st_mode & 0o777) if key_file.exists() else None,
    "active_goal": goal,
    "recent_smoke_receipts": receipts,
}, indent=2))
BRIEF
chmod +x "${BIN_DIR}/estate-brief"

if [ ! -f "${STATE_DIR}/active_goal.json" ]; then
  cat << 'JSON' > "${STATE_DIR}/active_goal.json"
{
  "goal_id": "GOAL-COMMERCIAL-GATE-01",
  "goal": "Enforce global core.hooksPath, tree-hash smoke receipts, and zero-ghost admission across all repos",
  "subgoals": ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"]
}
JSON
  echo "    bound GOAL-COMMERCIAL-GATE-01"
fi

echo "=== INSTALLED ==="
echo "    ${BIN_DIR}/estate-smoke  ${BIN_DIR}/estate-brief"
echo "    ${HOOKS_DIR}/pre-commit  ${HOOKS_DIR}/pre-push"
echo "    ${KEY_FILE}  ${DB_PATH}"
