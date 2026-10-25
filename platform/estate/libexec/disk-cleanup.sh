#!/usr/bin/env bash
# disk-cleanup -- free the data volume by deleting ONLY regenerable package-manager caches.
#
# bin/idp-disk-guard measures and advises, and deletes nothing by design; this is the executor its
# advice points at. Default is a dry run: every target with its measured size. apply=true deletes
# the allow-list below and nothing else, then proves it: each target must be gone, and the free
# space before/after is measured, not estimated.
#
# Allow-list (all rebuilt on the next install/build, at the cost of a download):
#   yarn berry cache, go build cache, pip cache, Homebrew download cache, npm cache + npx, uv cache,
#   and every Cargo target/ dir in the idp main checkout (a target/ beside a Cargo.toml that cargo
#   stamped with CACHEDIR.TAG or .rustc_info.json -- `cargo clean`, nothing else). Measured
#   2026-09-27: 3967M of target/ against 1.1G free, the one grower the caches above did not cover.
#   Other agents' worktrees (siblings, /tmp, .claude/worktrees) are never searched: their build
#   output is their workload, and deleting it forces a rebuild on someone mid-task.
# only_below_mb=N: apply only while free space is under N MB, so a schedule can run this hourly
# without re-downloading healthy caches (scheduler/schedule.yml passes bin/idp-disk-guard's floor).
# Opt-in: trash=true empties ~/.Trash -- the user's, so never by default.
# Never touched, only reported: ~/.cache/estate-tools (live tooling: litellm venv, whisper, flux,
# helm), ~/Documents, sibling repo worktrees (other agents'), app caches.
# Under a CRITICAL floor (CRIT_MB, default 10240M free) the toolchain tier below also reclaims
# ~/.ollama/models, old ~/.nvm/versions/node/*, old ~/.rustup/toolchains/* and old
# ~/.local/share/claude/versions/*: toolchains, re-installed on demand. It also REPACKS the
# estate's own git clone (git gc -- the same objects, one packed file) and reclaims the build
# tools' package caches (~/.cargo/registry, ~/go/pkg/mod): re-fetched on demand. See
# "the critical tier".
# Chrome's code-sign clones (beside $TMPDIR, in X/): only those no process holds open.
# Under the floor, the log ends with WHERE the space is (largest dirs, big files, system spots),
# measured, not a fixed list -- see "where the space is" below.
#
# Exit: 0 ok, 3 a target that should be gone is not (verify failed), 4 the time budget ran out
# before every phase ran (run it again), 5 another run holds the lock and did the work instead
# (nothing done here -- 0 would say the disk is clear), 1 refused.
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
APPLY="${1:-false}"; TRASH="${2:-false}"; ONLY_BELOW_MB="${3:-0}"; WORKTREES="${4:-false}"
# A BOUND THE WORK CAN ACTUALLY FIT (2026-10-25). The door that runs this (the estate executor)
# kills any command at CEILING_SEC=100, and the disk intents are run through it. Measured
# 2026-10-25: `disk-free` was SIGTERMed at the ceiling with no output at all -- the run had
# reached the critical tier and the report never printed, so the agent that asked for space
# learned nothing and the free-space number it needed was in a log it never saw. The work here is
# not one unit: docker prune+fstrim, a worktree walk with archives, a git gc, an lsof, a du of
# HOME. A caller that must finish inside a door says how long it has, and each phase either runs
# inside what is left or is skipped BY NAME with the seconds it was denied. Nothing is deleted
# whose phase could not also report it, and a resumed call picks up what was skipped (every phase
# is idempotent: it finds nothing to do the second time).
#
#   $5 seconds  0 (default) = unbounded, so the launchd tick and a human run are unchanged
#   DISK_CLEANUP_PHASES  comma list, or `all` (default): caches,docker,worktrees,temp,clones,critical,scan
#
# Exit 4 = the budget ran out before every phase ran; run it again to continue.
BUDGET="${5:-0}"; PHASES="${DISK_CLEANUP_PHASES:-all}"
T_START=$(date +%s)
budget_hit=0
# remaining: whole seconds left of BUDGET, or a large number when unbounded (so every `-lt` test
# below reads the same way whether a bound was given or not).
remaining() {
  if [ "$BUDGET" = 0 ]; then echo 1000000; return; fi
  local r=$((BUDGET - ($(date +%s) - T_START)))
  [ "$r" -gt 0 ] && echo "$r" || echo 0
}
# phase_is_wanted NAME -> 0 when this run should do it at all
phase_is_wanted() {
  # The subject is ",$PHASES,": an empty PHASES is ",," (two commas), so the empty case is ",,".
  # It was `","` -- one comma -- which can never match a two-comma subject, so an empty
  # DISK_CLEANUP_PHASES skipped every phase instead of running all of them.
  case ",$PHASES," in *,all,*|,,) return 0;; *",$1,"*) return 0;; esac
  echo "  SKIP   $1  (not in DISK_CLEANUP_PHASES=$PHASES)"
  return 1
}
# phase_gate NAME MIN_SECONDS -> 0 when there is room for it; else says so and marks the run short.
phase_gate() {
  phase_is_wanted "$1" || return 1
  local left; left=$(remaining)
  if [ "$left" -lt "$2" ]; then
    echo "  SKIP   $1  ${left}s left of a ${BUDGET}s budget, under the ${2}s this phase needs: run again"
    budget_hit=1; return 1
  fi
  return 0
}
VOL="${DISK_GUARD_PATH:-/System/Volumes/Data}"   # the writable volume, as bin/idp-disk-guard
RUST_ROOTS="${DISK_CLEANUP_RUST_ROOTS:-$HOME/Documents/code/idp}"
WT_REPOS="${DISK_CLEANUP_WT_REPOS:-$HOME/Documents/code/idp}"
WT_IDLE_MIN="${DISK_CLEANUP_WT_IDLE_MIN:-120}"
WT_FRESH_MIN="${DISK_CLEANUP_WT_FRESH_MIN:-60}"
WT_STALE_MIN="${DISK_CLEANUP_WT_STALE_MIN:-4320}"
WT_ARCHIVE_MAX_MB="${DISK_CLEANUP_WT_ARCHIVE_MAX_MB:-64}"
WT_QUARANTINE_DAYS="${DISK_CLEANUP_WT_QUARANTINE_DAYS:-30}"
QUAR="${DISK_CLEANUP_QUARANTINE:-$HOME/.estate/quarantine/worktrees}"
TMP_ROOT="${DISK_CLEANUP_TMP_ROOT-$(getconf DARWIN_USER_TEMP_DIR 2>/dev/null)}"
TMP_IDLE_MIN="${DISK_CLEANUP_TMP_IDLE_MIN:-360}"
CLONE_FRESH_MIN="${DISK_CLEANUP_CLONE_FRESH_MIN:-60}"
SCAN_EVERY_MIN="${DISK_CLEANUP_SCAN_EVERY_MIN:-60}"
SCAN_TOP="${DISK_CLEANUP_SCAN_TOP:-15}"
BIG_FILE_MB="${DISK_CLEANUP_BIG_FILE_MB:-200}"
T_SCAN="${DISK_CLEANUP_SCAN_TIMEOUT:-300}"
# One system spot may not outlive the run's door: du of /System/Volumes/Update took 118s here
# (measured 2026-10-26, no-budget dry run: 118 of 125 total seconds), so a legacy no-budget call
# could be killed by the 100s door mid-scan. BLIND beats a door kill.
T_SPOTS="${DISK_CLEANUP_SPOTS_TIMEOUT:-45}"
SYSTEM_SPOTS="${DISK_CLEANUP_SYSTEM_SPOTS-/System/Volumes/Update /private/var/vm}"
SCAN_FILE="${DISK_CLEANUP_SCAN_FILE:-$HOME/.estate/disk-cleanup.last-scan}"
CRIT_MB="${DISK_CLEANUP_CRIT_MB:-10240}"   # free-space floor under which the toolchain tier runs
# The estate's own git clone: repacked under the floor, never deleted (git gc keeps every
# reachable object). Space-separated; each path is resolved, so a symlinked clone is done once.
GIT_REPOS="${DISK_CLEANUP_GIT_REPOS:-$HOME/.estate/graph/estate-graph}"
REPACK_MIN_KB="${DISK_CLEANUP_REPACK_MIN_KB:-65536}"  # below this much loose object, git gc is not worth the IO
T_REPACK="${DISK_CLEANUP_GIT_TIMEOUT:-300}"          # git gc is bounded: a wedged repo must not hang the tick
CARGO_REGISTRY="${DISK_CLEANUP_CARGO_REGISTRY:-$HOME/.cargo/registry}"
GO_MODCACHE="${DISK_CLEANUP_GO_MODCACHE:-${GOPATH:-$HOME/go}/pkg/mod}"
CARGO_PROC='(^|/)(cargo|rustc)( |$)'
GO_PROC='(^|/)go (build|test|run|vet|mod|install|get|work|list|env)'
GIT_BUSY='git (gc|repack|pack-objects)'
[ -n "${HOME:-}" ] && [ "$HOME" != / ] || { echo "REFUSED HOME is unset or /"; exit 1; }
case "$APPLY" in True|true) APPLY=1;; *) APPLY=0;; esac
case "$TRASH" in True|true) TRASH=1;; *) TRASH=0;; esac
case "$WORKTREES" in True|true) WORKTREES=1;; *) WORKTREES=0;; esac
for v in WT_IDLE_MIN WT_FRESH_MIN WT_STALE_MIN WT_ARCHIVE_MAX_MB WT_QUARANTINE_DAYS TMP_IDLE_MIN \
         CLONE_FRESH_MIN SCAN_EVERY_MIN SCAN_TOP BIG_FILE_MB T_SCAN CRIT_MB REPACK_MIN_KB T_REPACK \
         T_SPOTS BUDGET; do
  case "${!v}" in ''|*[!0-9]*) echo "REFUSED DISK_CLEANUP_$v=${!v} is not a number"; exit 1;; esac
done
case "$ONLY_BELOW_MB" in ''|*[!0-9]*) echo "REFUSED only_below_mb=$ONLY_BELOW_MB is not a number"; exit 1;; esac
# $TMPDIR, resolved (lsof and git report /private/var/...): only a per-user temp dir or a test's.
if [ -n "$TMP_ROOT" ] && [ -d "$TMP_ROOT" ]; then
  TMP_ROOT=$(cd "$TMP_ROOT" && pwd -P)
  case "$TMP_ROOT" in /private/var/folders/?*|/private/tmp/?*|/tmp/?*|"$HOME"/?*) ;; *) TMP_ROOT=;; esac
else TMP_ROOT=; fi
# Chrome's code-sign clones live beside $TMPDIR: <per-user>/T is the temp dir, <per-user>/X holds
# them. No $TMPDIR (a test sets it empty), no clones -- so no test ever reaches the real ones.
CLONES="${DISK_CLEANUP_CHROME_CLONES-${TMP_ROOT:+${TMP_ROOT%/T}/X/com.google.Chrome.code_sign_clone}}"

free_k() { df -k "$VOL" 2>/dev/null | awk 'NR==2 {print $4}'; }
# A bounded call: after $1 seconds its whole process group is killed (exit 142). The group, not
# the pid: a child left alive keeps the $(...) pipe open and the caller waits anyway (the test with
# a hung `image prune` proved it). /usr/bin/perl ships with macOS; `timeout` and `flock` do not,
# and a launchd job's PATH cannot be assumed to find coreutils.
tmo() {
  # NOT `shift`: the perl below takes the timeout off @ARGV as its own first argument, so the
  # shell must hand it over intact. Measured 2026-10-25: shifting here made perl treat the command
  # name as the timeout and exec the first real argument (exit 127, no output) -- one line of
  # cleanup that silently disarmed every bounded call in this script.
  local t="$1"
  # UNDER A BUDGET NO SINGLE COMMAND OUTLIVES IT (2026-10-25). The phase gates decide whether a
  # phase STARTS; they do not stop one that started with 40s left from taking 90. Measured: a
  # disk-free run with budget 78 was killed by the door at 95s inside a phase, so it neither
  # finished nor printed the budget line that tells the operator to run it again -- the exact
  # failure the budget exists to prevent. So every bounded call is capped at what is left, minus
  # a small reserve for the phase to report what it did.
  if [ "${BUDGET:-0}" != 0 ]; then
    local left; left=$(( $(remaining) - 2 ))
    [ "$left" -lt 2 ] && left=2
    [ "$left" -lt "$t" ] && t="$left"
  fi
  [ "$t" -lt 1 ] && t=1
  /usr/bin/perl -e '
    my $t = shift; my $pid = fork; exit 127 unless defined $pid;
    if ($pid == 0) { setpgrp(0, 0); exec @ARGV or exit 127 }
    $SIG{ALRM} = sub { kill "TERM", -$pid; sleep 1; kill "KILL", -$pid; waitpid($pid, 0); exit 142 };
    alarm $t; waitpid($pid, 0); exit($? & 127 ? 128 + ($? & 127) : $? >> 8)' "$@"
}
# One run at a time: a slow Docker prune must not stack a second run on the next 5-minute tick.
LOCK="${DISK_CLEANUP_LOCK:-$HOME/.estate/disk-cleanup.lock}"
mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  holder=$(cat "$LOCK/pid" 2>/dev/null || echo)
  if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
    # NOT 0 (2026-10-25): measured through the disk-free door, a second call answered "nothing done"
    # and the door's verdict printed "every phase ran" -- a caller read a clear disk it never
    # touched. 5 is a distinct status so the verdict can say whose work it is.
    echo "ok      another disk-cleanup (pid $holder) is running: nothing done here"; exit 5; fi
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || { echo "ok      lost the lock race: nothing done here"; exit 5; }
fi
echo $$ >"$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT
size_m() {
  [ -e "$1" ] || { echo 0; return; }
  # Through tmo, so a du of a multi-GB cache or worktree is bounded by the budget as well: this
  # function is called once per target and once per candidate worktree, and an unbounded du here
  # is what ate a 78s budget before the phase gates could help (2026-10-25).
  local k; k=$(tmo 20 du -sk "$1" 2>/dev/null | awk '{print $1}')
  [ -n "$k" ] && echo $((k / 1024)) || echo 0
}

# name | path | process that must not be mid-write into it
# (patterns match the tool's entry point, not any path containing its name: /opt/homebrew/bin/*
# would otherwise make every process "brew")
TARGETS="yarn-cache|$HOME/.yarn/berry/cache|yarn-[0-9.]+\.c?js|bin/yarn( |$)
go-build|$HOME/Library/Caches/go-build|go (build|test|install|run|vet) 
pip-cache|$HOME/Library/Caches/pip|pip3? (install|download|wheel)|-m pip 
homebrew-cache|$HOME/Library/Caches/Homebrew|Homebrew/brew\.rb|bin/brew( |$)
npm-cache|$HOME/.npm/_cacache|npm-cli\.js|bin/npm( |$)
npx-cache|$HOME/.npm/_npx|npx-cli\.js|bin/npx( |$)
uv-cache|$HOME/.cache/uv|(^|/)uv( |$)"
# Cargo target/ dirs: found, not listed, because every checkout and worktree grows its own.
# -prune keeps find out of target/, node_modules, .git and agent worktrees; the Cargo.toml + cargo's own stamp
# is what separates a build dir from any other directory that happens to be called target.
# The find is BOUNDED (T_FIND, default 25s): measured 2026-10-25 on the founder's laptop, a walk of
# ~/Documents (an iCloud-synced folder) had not finished when the door SIGTERMed the whole run at
# 100s, so every phase after it -- the caches, docker, the tier -- never ran and the run said
# nothing. A discovery step that cannot finish is BLIND for that one target family, not a reason to
# lose the rest of the run.
T_FIND="${DISK_CLEANUP_FIND_TIMEOUT:-25}"
found=$(tmo "$T_FIND" find $RUST_ROOTS -maxdepth 6 \( -name node_modules -o -name .git -o -path '*/.claude/worktrees' \) -prune \
       -o -type d -name target -prune -print 2>/dev/null); find_rc=$?
[ "$find_rc" = 142 ] && echo "  BLIND  rust-target  the find of $RUST_ROOTS did not finish in ${T_FIND}s: no Cargo target/ dirs this run"
while IFS= read -r t; do
  [ -f "${t%/target}/Cargo.toml" ] || continue
  [ -f "$t/CACHEDIR.TAG" ] || [ -f "$t/.rustc_info.json" ] || continue
  TARGETS="$TARGETS
rust-target|$t|(^|/)(cargo|rustc)( |$)"
done <<EOF
$found
EOF
[ "$TRASH" = 1 ] && TARGETS="$TARGETS
trash|$HOME/.Trash|Finder-empty"

before=$(free_k)
[ -n "$before" ] || { echo "BLIND cannot read free space on $VOL"; exit 1; }
if [ "$APPLY" = 1 ] && [ "$ONLY_BELOW_MB" -gt 0 ] && [ "$((before / 1024))" -ge "$ONLY_BELOW_MB" ]; then
  echo "ok $((before / 1024))M free on $VOL, not under only_below_mb=${ONLY_BELOW_MB}: nothing deleted"
  exit 0
fi
echo "free before: $((before / 1024))M on $VOL ($([ "$APPLY" = 1 ] && echo apply || echo dry-run))"

fails=0; total=0
caches_on=0; phase_gate caches 5 && caches_on=1
while IFS='|' read -r name path proc; do
  [ "$caches_on" = 1 ] || break
  case "$path" in "$HOME"/?*|/private/tmp/?*|/tmp/?*) ;; *) echo "REFUSED $name: $path is not under HOME or /tmp"; exit 1;; esac
  m=$(size_m "$path"); total=$((total + m))
  if [ ! -e "$path" ] || [ "$m" = 0 ]; then echo "  -      $name  absent/empty  $path"; continue; fi
  if [ "$APPLY" = 0 ]; then echo "  would  $name  ${m}M  $path"; continue; fi
  if pgrep -f "$proc" >/dev/null 2>&1 && [ "$proc" != Finder-empty ]; then
    echo "  SKIP   $name  ${m}M  a '$proc' process is running and may be writing into it"; continue; fi
  if [ "$name" = trash ]; then
    tmo "$(remaining)" find "$path" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
  else
    tmo "$(remaining)" rm -rf "$path"
  fi
  left=$(size_m "$path")
  if [ "$left" -le 1 ]; then echo "  freed  $name  ${m}M"
  else echo "  !! $name still holds ${left}M after delete: $path"; fails=$((fails + 1)); fi
done <<EOF
$TARGETS
EOF

echo "allow-list total: ${total}M"

# Docker (Rancher Desktop). Measured 2026-09-30: the VM disk file held 7.9G on the host while
# `docker system df` showed 1.85G of unused images and 2.39G of build cache; pruning alone freed
# nothing on the host, because the VM's ext4 keeps the blocks until they are trimmed. Prune, then
# fstrim /mnt/data: the file dropped to 2.4G and the host gained 5.0G.
# Images: dangling only (`image prune -f`). `--filter until=` compares an image's CREATION time,
# so an old base image pulled a minute ago for a queued build would be deleted under it (review,
# idp-57, 2026-09-30). Build cache: unused for 24h. A running build of any kind skips the block.
# Every call is bounded (a wedged VM must not hang disk-watch) and a failed call counts in `fails`.
DOCKER="$HOME/.rd/bin/docker"; RDCTL="$HOME/.rd/bin/rdctl"
T_INFO="${DISK_CLEANUP_DOCKER_INFO_TIMEOUT:-20}"; T_STEP="${DISK_CLEANUP_DOCKER_TIMEOUT:-300}"
BUILDING="${DISK_CLEANUP_BUILDING:-docker(-buildx)? (buildx )?(build|bake)|docker[ -]compose( .*)? (build|up .*--build)}"
# under a budget, no single docker call may outlive it: prune-then-fstrim is only useful as a pair,
# so the pair gets what is left rather than each step asking for its own 300s.
if [ "$BUDGET" != 0 ]; then
  _left=$(remaining); _cap=$(( _left > 12 ? (_left - 4) / 3 : 4 ))
  [ "$_cap" -lt "$T_STEP" ] && T_STEP="$_cap"
  [ "$T_INFO" -gt "$_cap" ] && T_INFO="$_cap"
fi
docker_on=0; phase_gate docker 12 && docker_on=1
if [ "$docker_on" = 1 ] && [ -x "$DOCKER" ] && [ -x "$RDCTL" ] && tmo "$T_INFO" "$DOCKER" --context rancher-desktop info >/dev/null 2>&1; then
  if [ "$APPLY" = 0 ]; then
    echo "  would  docker  $(tmo 30 "$DOCKER" --context rancher-desktop system df --format '{{.Type}} {{.Reclaimable}}' 2>/dev/null | tr '\n' ';')  then fstrim"
  elif pgrep -f "$BUILDING" >/dev/null 2>&1; then
    echo "  SKIP   docker  an image build is running"
  else
    d0=$(free_k)
    for step in "image prune -f" "builder prune -af --filter until=24h"; do
      # $step is one of the two fixed argument lists above; it is split on purpose.
      # shellcheck disable=SC2086
      if ! out=$(tmo "$T_STEP" "$DOCKER" --context rancher-desktop $step 2>&1); then
        echo "  !! docker $step failed or timed out: ${out:0:200}"; fails=$((fails + 1)); fi
    done
    if ! out=$(tmo "$T_STEP" "$RDCTL" shell sudo fstrim /mnt/data 2>&1); then
      echo "  !! docker fstrim failed or timed out: ${out:0:200}"; fails=$((fails + 1)); fi
    echo "  freed  docker  $((($(free_k) - d0) / 1024))M on the host (prune + fstrim, measured)"
  fi
elif [ "$docker_on" = 1 ] && [ -x "$DOCKER" ]; then
  echo "  -      docker  engine not answering within ${T_INFO}s: skipped"
fi

# Settled worktrees (worktrees=true). Measured 2026-09-27: 0M of caches left to free while ~9G sat
# in agent worktrees, each new one 260-560M, and the volume hit 160M free. A worktree is only a
# checkout: its branch and commits live in the shared repository and survive `git worktree
# remove`, so `git worktree add <path> <branch>` brings it back. It is removed only when ALL hold:
#   - no modified, staged or untracked file (git status), and no ignored file outside the
#     rebuildable set below (an ignored .env or notes file is someone's, and stays);
#   - every commit reachable from a branch, tag or remote ref (the branch itself counts: removing
#     the checkout leaves the branch and all its commits in the repository);
#   - not locked; no process has its working directory inside it (a live session or server);
#   - its index, HEAD and reflog untouched for WT_IDLE_MIN minutes (default 6h);
#   - and, merged to origin/main or not, not created or touched in the last WT_FRESH_MIN (60m): a
#     fresh `worktree add` of origin/main is clean, merged and has no process in it yet (agent
#     shells do not keep their cwd there), and was removed minutes after it was made (2026-10-14,
#     idp-wt-kyv, twice, mid-fetch).
# Leftovers are archived, not a reason to keep the checkout. Measured 2026-10-14: the volume at
# 323M free while ~24 worktrees (~6.6G) were all kept, most for 0-4M of logs/, estate.db or
# .estate/ state, or for a change nobody had touched in days. So a worktree that passes every check
# above except these has them saved under $QUAR/<utc>-<name>/ first, then is removed with --force:
#   - ignored files outside the rebuildable set -> ignored.tgz (unless one was written in the
#     last WT_IDLE_MIN: a live server's log or db);
#   - uncommitted or untracked work, only once the git dir AND every changed file are untouched
#     for WT_STALE_MIN (3 days) -> work.patch (git diff --binary HEAD) + untracked.tgz;
#   - a detached HEAD's own commits, after the same 3 days -> refs/estate/kept/<utc>-<name>.
# An archive over WT_ARCHIVE_MAX_MB (64M) is dropped and the worktree kept. The quarantine and its
# refs are deleted after WT_QUARANTINE_DAYS (30). Otherwise removal is `git worktree remove`
# WITHOUT --force, so git re-checks cleanliness itself, except when the only changes are
# rebuildable output (then --force, once; a lock still refuses). No process is signalled and
# nothing outside the worktree directory and the quarantine is touched.
REBUILDABLE='(^|/)(node_modules|target|dist|dist-types|build|__pycache__|\.pytest_cache|\.ruff_cache|\.mypy_cache|\.venv|venv|\.tox|coverage|\.coverage|\.turbo|\.next|\.cache|htmlcov)(/|$)|\.pyc$|\.tsbuildinfo$'
# recent_in MIN DIR < paths relative to DIR: is any of them (or anything under one) newer than MIN?
recent_in() {
  local min=$1 dir=$2 p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    [ -n "$(find "$dir/${p%/}" -mmin -"$min" -print 2>/dev/null | head -1)" ] && return 0
  done
  return 1
}
GITDIR_FILES='index
HEAD
logs/HEAD'
# Prints the reason to keep the worktree; nothing to remove it; "~<kinds>" to archive the
# leftovers named by <kinds> (work, ignored, commits) and then remove it.
unsettled() {
  local repo=$1 wt=$2 out gd work ign salvage=
  out=$(git -C "$wt" status --porcelain --ignored=matching 2>/dev/null) || { echo "git status failed"; return; }
  # A change confined to rebuildable output (a branch cut before target/ was untracked, then
  # cargo-cleaned: 1669 " D .../target/..." lines) is build output, not work.
  work=$(printf '%s\n' "$out" | grep -v '^!! ' | cut -c4- | grep -Ev "$REBUILDABLE")
  ign=$(printf '%s\n' "$out" | sed -n 's/^!! //p' | grep -Ev "$REBUILDABLE")
  # Every commit must stay reachable from a ref once the checkout is gone. A branch keeps its own
  # commits (pushed or not, squash-merged or not); a detached HEAD's commits must be on a branch,
  # tag or remote, or `git gc` would eventually take them.
  out=$(git -C "$wt" rev-list -n1 HEAD --not --branches --tags --remotes 2>/dev/null) || { echo "git rev-list failed"; return; }
  git -C "$wt" rev-parse -q --verify HEAD >/dev/null || { echo "commits reachable only from this checkout's HEAD"; return; }
  gd=$(git -C "$wt" rev-parse --absolute-git-dir 2>/dev/null) || { echo "no git dir"; return; }
  [ -n "$work" ] && salvage="$salvage work"
  [ -n "$out" ] && salvage="$salvage commits"
  if [ -n "$salvage" ] && { printf '%s\n' "$GITDIR_FILES" | recent_in "$WT_STALE_MIN" "$gd" ||
       printf '%s\n' "$work" | sed 's/.* -> //' | recent_in "$WT_STALE_MIN" "$wt"; }; then
    if [ -n "$work" ]; then echo "uncommitted or untracked files"; else echo "commits reachable only from this checkout's HEAD"; fi
    return
  fi
  [ -n "$ign" ] && salvage="$salvage ignored"
  if git -C "$repo" worktree list --porcelain | awk -v w="$wt" '$1=="worktree"{c=($2==w)} c&&$1=="locked"{f=1} END{exit !f}'; then
    echo "locked"; return; fi
  # lsof reports resolved paths (/private/tmp), git the path it was given (/tmp): compare both.
  if printf '%s\n' "$CWDS" | awk -v w="$wt" -v r="$(cd "$wt" && pwd -P)" \
       'index($0, w"/")==1 || $0==w || index($0, r"/")==1 || $0==r {f=1} END{exit !f}'; then
    echo "a process is working inside it"; return; fi
  if [ "$WT_FRESH_MIN" -gt 0 ] && printf '%s\n' "$GITDIR_FILES" | recent_in "$WT_FRESH_MIN" "$gd"; then
    echo "created or used in the last ${WT_FRESH_MIN}m"; return; fi
  # A checkout whose HEAD is already in origin/main holds nothing that is not on main: past the
  # fresh floor it needs no idle wait (the wait only guards work in progress, and there is none).
  if ! git -C "$wt" merge-base --is-ancestor HEAD origin/main 2>/dev/null &&
     [ "$WT_IDLE_MIN" -gt 0 ] && printf '%s\n' "$GITDIR_FILES" | recent_in "$WT_IDLE_MIN" "$gd"; then
    echo "used in the last ${WT_IDLE_MIN}m"; return; fi
  if [ -n "$ign" ] && [ "$WT_IDLE_MIN" -gt 0 ] && printf '%s\n' "$ign" | recent_in "$WT_IDLE_MIN" "$wt"; then
    echo "ignored files that are not build output, written in the last ${WT_IDLE_MIN}m"; return; fi
  [ -z "$salvage" ] || echo "~${salvage# }"
}
# archive REPO WT KINDS: save the leftovers, print where; non-zero (and nothing left behind) when
# a step fails or the archive is over the cap.
archive() {
  local repo=$1 wt=$2 kinds=" $3 " q out list
  q="$QUAR/$(date -u +%Y%m%dT%H%M%SZ)-$(basename "$wt")"
  mkdir -p "$q" && chmod 700 "$QUAR" "$q" || { echo "cannot create $q"; return 1; }
  { echo "$wt"; git -C "$wt" branch --show-current; git -C "$wt" rev-parse HEAD; } >"$q/origin"
  out=$(git -C "$wt" status --porcelain --ignored=matching)
  case "$kinds" in *" work "*)
    git -C "$wt" diff --binary HEAD >"$q/work.patch" || { rm -rf "$q"; echo "git diff failed"; return 1; }
    list=$(printf '%s\n' "$out" | sed -n 's/^?? //p' | grep -Ev "$REBUILDABLE")
    if [ -n "$list" ] && ! printf '%s\n' "$list" | tar -czf "$q/untracked.tgz" -C "$wt" -T - 2>/dev/null; then
      rm -rf "$q"; echo "tar of untracked files failed"; return 1; fi;;
  esac
  case "$kinds" in *" ignored "*)
    list=$(printf '%s\n' "$out" | sed -n 's/^!! //p' | grep -Ev "$REBUILDABLE")
    if ! printf '%s\n' "$list" | tar -czf "$q/ignored.tgz" -C "$wt" -T - 2>/dev/null; then
      rm -rf "$q"; echo "tar of ignored files failed"; return 1; fi;;
  esac
  if [ "$(size_m "$q")" -gt "$WT_ARCHIVE_MAX_MB" ]; then
    out=$(size_m "$q"); rm -rf "$q"; echo "${out}M of leftovers, over the ${WT_ARCHIVE_MAX_MB}M archive cap"; return 1; fi
  case "$kinds" in *" commits "*)
    git -C "$repo" update-ref "refs/estate/kept/$(basename "$q")" "$(git -C "$wt" rev-parse HEAD)" ||
      { rm -rf "$q"; echo "update-ref failed"; return 1; };;
  esac
  echo "$q"
}
if [ "$WORKTREES" = 1 ] && phase_gate worktrees 15; then
  # `git status` refreshes and rewrites the index when it can, which would reset the very idle
  # clock read above: every run would keep the worktree it looked at.
  export GIT_OPTIONAL_LOCKS=0
  CWDS=$(tmo 20 lsof -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  # A CLAIMED WORKTREE IS NEVER REMOVED (2026-10-25). Measured 2026-10-24: the governed
  # disk-cleanup intent (worktrees=true) removed a live agent's worktree at
  # ~/.estate/worktrees/deps-zod-mlflow while that agent was working in it -- the checkout is
  # disposable, so the cleaner judged it settled, and the agent's working directory vanished under
  # it and every job it then ran failed. The cleaner asks git; a claim is a GitHub comment. So the
  # estate's own focus register decides: platform/estate/libexec/claimed-worktrees.py prints the
  # worktrees a live claim covers (a `Claim: owner/repo#N` trailer in the branch's commits and N
  # live in the register). A worktree on that list is kept, with the reason printed, whatever else
  # the checks below say -- a claim is a stronger signal than an idle clock.
  CLAIMED=$(tmo 20 python3 "$(dirname "$0")/claimed-worktrees.py" $WT_REPOS 2>/dev/null)
  [ -n "$CLAIMED" ] && echo "  keep   worktrees  $(printf '%s\n' "$CLAIMED" | wc -l | tr -d ' ') claimed by a live claim"
  if [ "$APPLY" = 1 ] && [ -d "$QUAR" ]; then
    find "$QUAR" -mindepth 1 -maxdepth 1 -type d -mtime +"$WT_QUARANTINE_DAYS" 2>/dev/null | while IFS= read -r q; do
      for repo in $WT_REPOS; do git -C "$repo" update-ref -d "refs/estate/kept/${q##*/}" 2>/dev/null; done
      rm -rf "$q" && echo "  freed  quarantine  ${q##*/}  (over ${WT_QUARANTINE_DAYS}d)"
    done
  fi
  for repo in $WT_REPOS; do
    # Said, not skipped: under a launchd job that macOS will not let into ~/Documents (TCC), both
    # checks fail, and a silent `continue` read as "nothing to free" on every tick (2026-10-14).
    [ -d "$repo" ] || { echo "  BLIND  worktrees  cannot see $repo"; fails=$((fails + 1)); continue; }
    main=$(git -C "$repo" rev-parse --show-toplevel 2>&1) || {
      echo "  BLIND  worktrees  cannot read $repo: ${main:0:120}"; fails=$((fails + 1)); continue; }
    # The list is taken once, into a variable, and the walk runs in THIS shell -- not
    # `git ... | sed | while`. Measured 2026-10-25: as a pipeline, the walk sometimes never
    # returned after printing its last worktree (`disk-free` sat at 100s with the whole worktree
    # phase's output already on screen), because the loop waits for EOF from a git process that
    # has finished talking but has not exited in a worktree it just stat'ed. Two other things were
    # wrong with the pipeline too: `break` and `budget_hit=1` set inside it died in the subshell,
    # so a budget stop there was invisible to the exit status. A variable fixes all three.
    wts=$(tmo 15 git -C "$repo" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p')
    while IFS= read -r wt; do
      [ "$wt" = "$main" ] && continue
      [ -d "$wt" ] || continue
      # the walk costs a size_m and a status per worktree, so under a budget it stops cleanly
      # between worktrees instead of being killed inside one.
      if [ "$(remaining)" -lt 6 ]; then
        echo "  SKIP   worktree  $(remaining)s left of a ${BUDGET}s budget: stopped before $wt, run again"
        break
      fi
      under=
      case "$wt" in "$HOME"/?*|/private/tmp/?*|/tmp/?*) under=1;; esac
      if [ -n "$TMP_ROOT" ]; then case "$wt" in "$TMP_ROOT"/?*) under=1;; esac; fi
      if [ -z "$under" ]; then echo "  keep   worktree  $wt  (not under HOME, /tmp or \$TMPDIR)"; continue; fi
      claimed=$(printf '%s\n' "$CLAIMED" | awk -v w="$wt" -F'\t' '$1==w {print $2; exit}')
      if [ -n "$claimed" ]; then echo "  keep   worktree  $wt  ($claimed)"; continue; fi
      why=$(unsettled "$repo" "$wt")
      m=$(size_m "$wt")
      salvage=; case "$why" in "~"*) salvage=${why#\~}; why=;; esac
      if [ -n "$why" ]; then echo "  keep   worktree  ${m}M  $wt  ($why)"; continue; fi
      b=$(git -C "$wt" branch --show-current); b=${b:-detached $(git -C "$wt" rev-parse --short HEAD)}
      if [ "$APPLY" = 0 ]; then echo "  would  worktree  ${m}M  $wt  ($b${salvage:+; archive: $salvage}; restore: git worktree add $wt ${b#detached })"; continue; fi
      # A WORKTREE REMOVAL IS NOT INTERRUPTIBLE (2026-10-25): killing `git worktree remove` half way
      # leaves a directory git still lists and a checkout that is neither here nor there. So it
      # starts only with enough time to finish, and says so when it cannot -- the same rule this
      # script already applies to a toolchain rm -rf.
      if [ "$(remaining)" -lt 20 ]; then
        echo "  SKIP   worktree  ${m}M  $wt  ($(remaining)s left of a ${BUDGET}s budget, under the 20s a removal needs: run again)"
        budget_hit=1; continue
      fi
      kept=
      if [ -n "$salvage" ]; then
        kept=$(archive "$repo" "$wt" "$salvage") || { echo "  keep   worktree  ${m}M  $wt  (archive refused: $kept)"; continue; }
      fi
      # --force only when unsettled() found nothing but rebuildable output, or the leftovers are
      # archived; git still refuses a locked worktree (that needs --force twice).
      force=; { [ -n "$kept" ] || git -C "$wt" status --porcelain 2>/dev/null | grep -q .; } && force=--force
      if tmo "$(remaining)" git -C "$repo" worktree remove $force "$wt" >/dev/null 2>&1 && [ ! -e "$wt" ]; then
        echo "  freed  worktree  ${m}M  $wt  (restore: git worktree add $wt ${b#detached }${kept:+; leftovers ($salvage): $kept})"
      else
        echo "  !! worktree $wt: git refused to remove it"; fi
    done <<EOF
$wts
EOF
  done
fi

# Stale temp (worktrees=true). Measured 2026-10-14: 2.1G in the user's $TMPDIR older than 6h --
# go's go-build* dirs, mktemp -d / tempfile dirs, jest caches -- that nothing deletes (macOS clears
# it only at reboot). An entry goes when it is ours, has a tool's temp name, nothing under it was
# written in TMP_IDLE_MIN (6h), it holds no git checkout (the pass above judges those) and no
# process has a file open or its cwd under it. Only top-level entries of $TMPDIR, never $TMPDIR.
TMP_NAMES='^(go-build[0-9]+|tmp\.[A-Za-z0-9]{6,}|tmp[a-z0-9_]{8}|jest_[a-z0-9]+)$'
if [ "$WORKTREES" = 1 ] && [ -n "$TMP_ROOT" ] && phase_gate temp 8; then
  cands=$(tmo 15 find "$TMP_ROOT" -mindepth 1 -maxdepth 1 -user "$(id -u)" -mmin +"$TMP_IDLE_MIN" 2>/dev/null |
          while IFS= read -r p; do printf '%s\n' "${p##*/}" | grep -Eq "$TMP_NAMES" && printf '%s\n' "$p"; done)
  if [ -n "$cands" ]; then
    # both bounded: a whole-machine lsof listing and a find of $TMPDIR are two of the slowest
    # things here, and under a budget they get what is left rather than all of it.
    OPEN=$(tmo 20 lsof -Fn 2>/dev/null | sed -n 's/^n//p')
    while IFS= read -r p; do
      m=$(size_m "$p")
      if [ -n "$(find "$p" -mmin -"$TMP_IDLE_MIN" -print 2>/dev/null | head -1)" ]; then
        echo "  keep   tmp  ${m}M  $p  (written in the last ${TMP_IDLE_MIN}m)"; continue; fi
      if [ -n "$(find "$p" -maxdepth 3 -name .git -print 2>/dev/null | head -1)" ]; then
        echo "  keep   tmp  ${m}M  $p  (holds a git checkout)"; continue; fi
      if printf '%s\n' "$OPEN" | awk -v w="$p" 'index($0, w"/")==1 || $0==w {f=1} END{exit !f}'; then
        echo "  keep   tmp  ${m}M  $p  (a process has a file open under it)"; continue; fi
      if [ "$APPLY" = 0 ]; then echo "  would  tmp  ${m}M  $p"; continue; fi
      rm -rf "$p"
      if [ -e "$p" ]; then echo "  !! tmp $p still there after delete"; fails=$((fails + 1))
      else echo "  freed  tmp  ${m}M  $p"; fi
    done <<EOF
$cands
EOF
  fi
fi

# Chrome code-sign clones. Measured 2026-10-19: 6.3G in three 2.1G clones of Chrome.app under
# $TMPDIR/../X/com.google.Chrome.code_sign_clone, one held by the running Chrome, two left by
# earlier launches -- the largest single thing on the volume this script could not see, while its
# log said every target was empty and the volume sat at 249M free. Chrome makes a fresh clone at
# launch and only ever opens its own, so a clone no process holds open is a leftover. Kept: any
# clone a process has open, any touched in the last CLONE_FRESH_MIN (a launch mid-copy), and all of
# them when lsof cannot answer (a guess is not a verdict).
#
# One listing of every open file, filtered by path here, never `lsof +D`: +D stats each file under
# the tree, and 2026-10-20 ten clones (15G of Chrome.app copies) took it past the 60s cut-off on
# nearly every run, so the step went BLIND, kept them all, and the volume refilled to 0G. The full
# listing took 0.2s on the same laptop. lsof prints physical paths, so the tree is resolved first
# ($TMPDIR says /var/folders, lsof says /private/var/folders).
if [ -n "$CLONES" ] && [ -d "$CLONES" ] && phase_gate clones 12; then
  CLONES=$(cd "$CLONES" && pwd -P)
  held=$(tmo 60 lsof -nPw -Fn 2>/dev/null); rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "  BLIND  chrome-clones  lsof could not answer (exit $rc): all kept"; fails=$((fails + 1))
  else
    for c in "$CLONES"/code_sign_clone.*; do
      [ -d "$c" ] || continue
      m=$(size_m "$c")
      if printf '%s\n' "$held" | sed -n 's/^n//p' | awk -v w="$c" 'index($0, w"/")==1 || $0==w {f=1} END{exit !f}'; then
        echo "  keep   chrome-clone  ${m}M  $c  (held open: the running Chrome's)"; continue; fi
      if [ -n "$(find "$c" -maxdepth 0 -mmin -"$CLONE_FRESH_MIN" -print 2>/dev/null)" ]; then
        echo "  keep   chrome-clone  ${m}M  $c  (made in the last ${CLONE_FRESH_MIN}m)"; continue; fi
      if [ "$APPLY" = 0 ]; then echo "  would  chrome-clone  ${m}M  $c"; continue; fi
      rm -rf "$c"
      if [ -e "$c" ]; then echo "  !! chrome-clone $c still there after delete"; fails=$((fails + 1))
      else echo "  freed  chrome-clone  ${m}M  $c"; fi
    done
  fi
fi

# THE CRITICAL TIER. Measured 2026-10-24 on the founder's laptop: the volume sat at 7.7Gi free
# (92% used) with every allow-list target empty, because the growers were never on it --
# ~/.nvm/versions/node 2570M, ~/.rustup/toolchains 2659M, ~/.local/share/claude/versions 545M
# (three superseded builds) and ~/.ollama/models 3.5G before the founder killed the laptop's
# ollama on 2026-09-10 ("no i killed ollama because machine is slow"). The allow-list deletes
# CACHES; these are the same kind of thing one level up: a toolchain, re-installed on demand.
#
# The same day, later: the volume was back under the floor at 8725M free and the tier above had
# nothing left to give -- the ollama weights were gone, one node version and one rustup
# toolchain remained, and the claude builds were one. The growers that were left were the
# estate's own: the graph clone's loose git objects (3.05 GiB, repacked, not deleted) and the
# build tools' package caches (~/.cargo/registry 1081M, ~/go/pkg/mod 774M, both re-fetched on
# demand). A safeguard that cannot reach a healthy disk is a safeguard that stays armed and
# does nothing, so the tier grew those families too -- each with the same evidence and the same
# way back.
#
# It runs only under a critical floor (CRIT_MB, default 10240M free -- 10G on a 113Gi volume,
# which is macOS's own 10% headroom advice; a 4000M floor would not have fired on this machine,
# whose free space was 7885M) and only with apply=true. Under the floor the alternative is a
# machine that cannot write (bin/idp-disk-guard: "writes fail in ways that read as unrelated
# faults"), and the founder's order is "we must never be in trouble". Above the floor every one
# of these is listed and nothing is touched.
#
# KEPT, per target, and why:
#   - the newest of a family: the one a command with no pin resolves to;
#   - a version the estate's own runtime names (~/.estate/libexec/*, platform/estate/libexec/*):
#     pi and cline run node out of a pinned path, and deleting it breaks them mid-task;
#   - anything a running process holds open (one lsof listing, the same one the Chrome-clone
#     pass uses): a file open under it is a file in use;
#   - rustup's own default toolchain, and any ollama server that is running;
#   - a cargo/rustc or a go build that is running, and a git gc/repack already in flight:
#     those are writing into what they would reclaim.
# Everything else goes, and every line says how to get it back.
crit_held=""
crit_reclaim() {  # NAME PATH HOW-TO-GET-IT-BACK
  local name=$1 path=$2 regen=$3 m left
  # An rm -rf of several GB cannot be undone mid-way, so under a budget it is only started when
  # there is room to finish and report: a half-deleted node version is a broken node version.
  m=$(size_m "$path")
  if [ "$(remaining)" -lt 10 ]; then
    echo "  SKIP   $name  ${m}M  $path  ($(remaining)s left of a ${BUDGET}s budget: run again)"
    budget_hit=1; return 0
  fi
  if [ "$APPLY" = 0 ]; then echo "  would  $name  ${m}M  $path  ($regen)"; return 0; fi
  rm -rf "$path"
  left=$(size_m "$path")
  if [ "$left" -le 1 ]; then echo "  freed  $name  ${m}M  $path  ($regen)"
  else echo "  !! $name still holds ${left}M after delete: $path"; fails=$((fails + 1)); fi
}
crit_in_use() {  # 0 when a process holds a file open under $1
  printf '%s\n' "$crit_held" | awk -v w="$1" 'index($0, w"/")==1 || $0==w {f=1} END{exit !f}'
}
# A REPACK is not a delete: git gc rewrites the same objects into one pack file and keeps every
# reachable one (git's own guarantee). Only unreachable objects older than gc.pruneExpire (two
# weeks by default) are pruned. Measured before and after, so the line states what it freed.
crit_repack() {  # NAME REPO
  local name=$1 repo=$2 before_m after_m loose_before loose_after out rc
  loose_before=$(git -C "$repo" count-objects -v 2>/dev/null | awk '$1=="size:"{print $2}')
  case "$loose_before" in ''|*[!0-9]*) loose_before=0;; esac
  before_m=$(size_m "$repo/.git")
  out=$(tmo "$T_REPACK" git -C "$repo" gc --quiet 2>&1); rc=$?
  loose_after=$(git -C "$repo" count-objects -v 2>/dev/null | awk '$1=="size:"{print $2}')
  case "$loose_after" in ''|*[!0-9]*) loose_after=0;; esac
  after_m=$(size_m "$repo/.git")
  if [ "$rc" -ne 0 ]; then
    echo "  !! $name  git gc did not finish (exit $rc): $(printf '%s' "$out" | tail -1)"
    fails=$((fails + 1)); return 0
  fi
  if [ "$loose_after" -ge "$loose_before" ]; then
    echo "  keep   $name  ${after_m}M  $repo/.git  (git gc left ${loose_after}K of loose objects)"; return 0
  fi
  echo "  freed  $name  $(((loose_before - loose_after) / 1024))M of loose objects  $repo/.git  (${before_m}M -> ${after_m}M on disk; git gc: the same objects, one packed file)"
}
crit_pinned_nodes() {  # the node versions the estate's own runtime names
  local d
  for d in "$HOME/.estate/libexec" "$RUST_ROOTS/platform/estate/libexec"; do
    [ -d "$d" ] || continue
    grep -hoa '\.nvm/versions/node/[A-Za-z0-9._-]*' "$d"/* 2>/dev/null
  done | sed 's|.*/||' | sort -u
}
crit_tier() {
  local free_mb=$1 v name m newest pinned default keep held rc
  echo "critical tier: ${free_mb}M free on $VOL is under CRIT_MB=${CRIT_MB}M -- the toolchains below are re-installed on demand"
  held=$(tmo 60 lsof -nPw -Fn 2>/dev/null); rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "  BLIND  critical-tier  lsof could not answer (exit $rc): everything kept"; fails=$((fails + 1)); return 0
  fi
  crit_held=$(printf '%s\n' "$held" | sed -n 's/^n//p')

  # 1. ollama's weights. The founder killed the laptop's ollama on 2026-09-10; if a server is
  #    running now, someone is serving from these and they stay.
  if [ -d "$HOME/.ollama/models" ]; then
    if pgrep -x ollama >/dev/null 2>&1; then
      echo "  keep   ollama-models  $(size_m "$HOME/.ollama/models")M  $HOME/.ollama/models  (an ollama server is running)"
    else
      crit_reclaim ollama-models "$HOME/.ollama/models" "ollama pull <model>"
    fi
  fi

  # 2. node versions under nvm.
  if [ -d "$HOME/.nvm/versions/node" ]; then
    newest=$(ls -1 "$HOME/.nvm/versions/node" 2>/dev/null | sort -V | tail -1)
    pinned=$(crit_pinned_nodes)
    if [ -z "$newest" ]; then
      echo "  keep   node-version  all  (no version could be ordered: nothing is removed)"
    else
      for v in "$HOME/.nvm/versions/node"/*; do
        [ -d "$v" ] || continue
        name=${v##*/}
        m=$(size_m "$v")
        if [ "$name" = "$newest" ]; then echo "  keep   node-version  ${m}M  $v  (the newest installed)"; continue; fi
        if [ -n "$pinned" ] && printf '%s\n' "$pinned" | grep -qx "$name"; then
          echo "  keep   node-version  ${m}M  $v  (the estate's runtime names it)"; continue; fi
        if crit_in_use "$v"; then echo "  keep   node-version  ${m}M  $v  (a process holds it open)"; continue; fi
        crit_reclaim node-version "$v" "nvm install $name"
      done
    fi
  fi

  # 3. rustup toolchains.
  if [ -d "$HOME/.rustup/toolchains" ]; then
    default=$(sed -n 's/^default_toolchain = "\(.*\)"/\1/p' "$HOME/.rustup/settings.toml" 2>/dev/null | head -1)
    for v in "$HOME/.rustup/toolchains"/*; do
      [ -d "$v" ] || continue
      name=${v##*/}
      m=$(size_m "$v")
      keep=0
      if [ -n "$default" ]; then
        case "$name" in "$default"|"$default"-*) keep=1;; esac
      fi
      if [ "$keep" = 1 ]; then echo "  keep   rust-toolchain  ${m}M  $v  (rustup's default toolchain)"; continue; fi
      if crit_in_use "$v"; then echo "  keep   rust-toolchain  ${m}M  $v  (a process holds it open)"; continue; fi
      crit_reclaim rust-toolchain "$v" "rustup toolchain install $name"
    done
  fi

  # 4. superseded claude-code builds.
  if [ -d "$HOME/.local/share/claude/versions" ]; then
    newest=$(ls -1 "$HOME/.local/share/claude/versions" 2>/dev/null | sort -V | tail -1)
    for v in "$HOME/.local/share/claude/versions"/*; do
      [ -d "$v" ] || continue
      name=${v##*/}
      m=$(size_m "$v")
      if [ -n "$newest" ] && [ "$name" = "$newest" ]; then
        echo "  keep   claude-version  ${m}M  $v  (the newest installed)"; continue; fi
      if crit_in_use "$v"; then echo "  keep   claude-version  ${m}M  $v  (a process holds it open)"; continue; fi
      crit_reclaim claude-version "$v" "claude's updater re-downloads it"
    done
  fi

  # 5. the estate's own git clone: loose objects, repacked. Measured 2026-10-24 on the founder's
  #    laptop: ~/.estate/graph/estate-graph held 5415 loose objects = 3.05 GiB while its pack held
  #    11 MiB -- every session transcript the router drained into it was written as a loose
  #    object and never repacked. `git fsck --unreachable` found none: all 8340 objects are
  #    reachable, so this is not garbage, it is the same content stored as 5415 files instead of
  #    one pack. `git gc` repacks it: no reachable object is lost, and only unreachable objects
  #    older than gc.pruneExpire (two weeks by default) are pruned. This is the one place the
  #    tier rewrites rather than deletes, and it is why it is measured before and after.
  for repo in $GIT_REPOS; do
    [ -d "$repo/.git" ] || continue
    repo=$(cd "$repo" 2>/dev/null && pwd -P) || continue
    [ -n "$repo" ] || continue
    loose=$(git -C "$repo" count-objects -v 2>/dev/null | awk '$1=="size:"{print $2}')
    case "$loose" in ''|*[!0-9]*) loose=0;; esac
    if [ "$loose" -lt "$REPACK_MIN_KB" ]; then
      echo "  keep   git-repack  $((loose / 1024))M  $repo  (only ${loose}K of loose objects)"; continue
    fi
    if pgrep -f "$GIT_BUSY" >/dev/null 2>&1; then
      echo "  keep   git-repack  $((loose / 1024))M  $repo  (a git gc/repack is already running)"; continue
    fi
    if crit_in_use "$repo/.git"; then
      echo "  keep   git-repack  $((loose / 1024))M  $repo  (a process holds it open)"; continue
    fi
    if [ "$APPLY" = 0 ]; then
      echo "  would  git-repack  $((loose / 1024))M  $repo/.git  (git gc: the same objects, one packed file)"; continue
    fi
    crit_repack git-repack "$repo"
  done

  # 6. cargo's registry: the crates it downloaded. Measured 2026-10-24: ~/.cargo/registry held
  #    1081M (src 1018M, index 59M, cache 4M). `cargo fetch` re-downloads and re-extracts all of
  #    it, so it is a download cache one level up from the build caches the allow-list deletes.
  #    A cargo or rustc process running means a build may be writing into it: it stays.
  if [ -d "$CARGO_REGISTRY" ]; then
    if pgrep -f "$CARGO_PROC" >/dev/null 2>&1; then
      echo "  keep   cargo-registry  $(size_m "$CARGO_REGISTRY")M  $CARGO_REGISTRY  (a cargo/rustc process is running)"
    elif crit_in_use "$CARGO_REGISTRY"; then
      echo "  keep   cargo-registry  $(size_m "$CARGO_REGISTRY")M  $CARGO_REGISTRY  (a process holds it open)"
    else
      crit_reclaim cargo-registry "$CARGO_REGISTRY" "cargo fetch"
    fi
  fi

  # 7. the Go module cache: the modules it downloaded. Measured 2026-10-24: ~/go/pkg/mod held
  #    774M (golang.org 341M, github.com 222M, the download cache 212M). `go mod download`
  #    re-fetches every one of them.
  if [ -d "$GO_MODCACHE" ]; then
    if pgrep -f "$GO_PROC" >/dev/null 2>&1; then
      echo "  keep   go-modcache  $(size_m "$GO_MODCACHE")M  $GO_MODCACHE  (a go build is running)"
    elif crit_in_use "$GO_MODCACHE"; then
      echo "  keep   go-modcache  $(size_m "$GO_MODCACHE")M  $GO_MODCACHE  (a process holds it open)"
    else
      crit_reclaim go-modcache "$GO_MODCACHE" "go mod download"
    fi
  fi
}

# The tier fires on the space as it stands now, after the caches, the worktrees and the Chrome
# clones above have had their turn: a floor that was crossed by them is no longer a floor.
now_mb=$(( $(free_k) / 1024 ))
if [ "$CRIT_MB" -gt 0 ] && [ "$now_mb" -lt "$CRIT_MB" ] && phase_gate critical 25; then
  crit_tier "$now_mb"
fi

if [ "$APPLY" = 1 ]; then
  after=$(free_k)
  echo "free after: $((after / 1024))M (measured delta $(((after - before) / 1024))M; other writers move this too)"
fi

# Report-only: the big things a human decides about. Sizes measured now, nothing deleted.
# (The toolchain paths are listed here too: under the critical floor above they are reclaimed,
# and only then -- this list is what the founder reads when the floor is not reached.)
echo "not touched (owner decides):"
for p in "$HOME/.cache/estate-tools" "$HOME/.nvm/versions/node" "$HOME/.ollama" "$HOME/.rustup" \
         "$HOME/Library/Caches/Google" "$HOME/Library/Application Support/rancher-desktop"; do
  [ -e "$p" ] && echo "  $(size_m "$p")M  $p"
done
[ "$TRASH" = 1 ] || echo "  $(size_m "$HOME/.Trash")M  $HOME/.Trash  (trash=true to empty)"
git -C "$HOME/Documents/code/idp" worktree list 2>/dev/null | awk 'NR>1 {print $1}' | while read -r wt; do
  [ -d "$wt" ] && echo "  $(size_m "$wt")M  worktree $wt"
done

# WHERE THE SPACE IS (2026-10-20). The list above is fixed, so on 2026-10-19 the log read "nothing
# left to free" at 249M free while 6.3G of Chrome clones, an 8.6G staged macOS update and 0.8G of
# ~/.estate logs and ledgers sat outside it -- the owner could not tell from the log what to decide
# about. So whenever a run ends under the floor (and on every dry run) the log ends with a
# measurement: the largest directories one and two levels under HOME, every file over BIG_FILE_MB under
# HOME (a log or ledger with no rotation), and the system spots du can read. A du of HOME takes
# minutes, so it is measured at most every SCAN_EVERY_MIN and the last measurement re-printed with
# its time in between; nothing here deletes anything.
scan() {
  local out rc rel k p
  echo "measured $(date -u +%Y-%m-%dT%H:%MZ)"
  echo "  largest directories under HOME (one and two levels; a parent includes its children):"
  out=$(tmo "$T_SCAN" du -xk -d 2 "$HOME" 2>/dev/null); rc=$?
  [ "$rc" = 142 ] && echo "    BLIND  du of HOME did not finish in ${T_SCAN}s"
  printf '%s\n' "$out" | sort -rn | while IFS=$'\t' read -r k p; do
    rel=${p#"$HOME"/}
    [ "$rel" != "$p" ] || continue
    case "$rel" in */*/*) continue;; esac
    echo "    $((k / 1024))M  $p"
  done | head -"$SCAN_TOP"
  echo "  files over ${BIG_FILE_MB}M under HOME (logs and ledgers grow until rotated):"
  tmo "$T_SCAN" find "$HOME" -xdev \( -name node_modules -o -name .git \) -prune -o \
      -type f -size +"$((BIG_FILE_MB * 2048))" -print 2>/dev/null | while IFS= read -r p; do
    echo "    $(size_m "$p")M  $p"
  done | sort -rn | head -"$SCAN_TOP"
  for p in $SYSTEM_SPOTS; do
    [ -e "$p" ] || continue
    k=$(tmo "$T_SPOTS" du -sk "$p" 2>/dev/null)
    rc=$?
    k=$(printf '%s\n' "$k" | awk '{print $1}')
    if [ "$rc" = 142 ]; then echo "  BLIND  spots  du of $p did not finish in ${T_SPOTS}s"
    elif [ -n "$k" ]; then echo "  system  $((k / 1024))M  $p"
    else echo "  system  unreadable  $p"; fi
  done
}
if [ "$APPLY" = 0 ] || [ "$(($(free_k) / 1024))" -lt "$ONLY_BELOW_MB" ]; then
  echo "where the space is (nothing here is deleted; owner decides):"
  # A du of HOME takes minutes, so under a budget the scan either fits in what is left or is not
  # started: T_SCAN is narrowed to the remaining seconds (du then says BLIND if that was not
  # enough) and a run with less than 20s left says so instead of being killed inside du.
  scan_left=$(remaining)
  if [ "$BUDGET" != 0 ] && [ "$scan_left" -lt 20 ]; then
    echo "  SKIP   scan  ${scan_left}s left of a ${BUDGET}s budget: run again (the last measurement is in $SCAN_FILE)"
    budget_hit=1
  elif [ -f "$SCAN_FILE" ] && [ -n "$(find "$SCAN_FILE" -mmin -"$SCAN_EVERY_MIN" -print 2>/dev/null)" ]; then
    cat "$SCAN_FILE"
  else
    [ "$BUDGET" != 0 ] && T_SCAN=$(( scan_left > 20 ? scan_left - 5 : scan_left ))
    mkdir -p "$(dirname "$SCAN_FILE")"
    scan | tee "$SCAN_FILE.tmp" && mv "$SCAN_FILE.tmp" "$SCAN_FILE"
  fi
fi
[ "$fails" = 0 ] || exit 3
# 4, not 0: the phases that did not run are work still owed, and a caller that reads 0 would
# report a disk it never finished clearing. The output above names every phase that was skipped.
if [ "$budget_hit" = 1 ]; then
  echo "budget: $(( $(date +%s) - T_START ))s of ${BUDGET}s used; some phases were skipped -- run it again to continue"
  exit 4
fi
