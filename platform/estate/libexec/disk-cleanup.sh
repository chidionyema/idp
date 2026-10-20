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
# helm), ~/Documents, sibling repo worktrees (other agents'), ~/.nvm, ~/.ollama, app caches.
# Chrome's code-sign clones (beside $TMPDIR, in X/): only those no process holds open.
# Under the floor, the log ends with WHERE the space is (largest dirs, big files, system spots),
# measured, not a fixed list -- see "where the space is" below.
#
# Exit: 0 ok, 3 a target that should be gone is not (verify failed), 1 refused.
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
APPLY="${1:-false}"; TRASH="${2:-false}"; ONLY_BELOW_MB="${3:-0}"; WORKTREES="${4:-false}"
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
SYSTEM_SPOTS="${DISK_CLEANUP_SYSTEM_SPOTS-/System/Volumes/Update /private/var/vm}"
SCAN_FILE="${DISK_CLEANUP_SCAN_FILE:-$HOME/.estate/disk-cleanup.last-scan}"
[ -n "${HOME:-}" ] && [ "$HOME" != / ] || { echo "REFUSED HOME is unset or /"; exit 1; }
case "$APPLY" in True|true) APPLY=1;; *) APPLY=0;; esac
case "$TRASH" in True|true) TRASH=1;; *) TRASH=0;; esac
case "$WORKTREES" in True|true) WORKTREES=1;; *) WORKTREES=0;; esac
for v in WT_IDLE_MIN WT_FRESH_MIN WT_STALE_MIN WT_ARCHIVE_MAX_MB WT_QUARANTINE_DAYS TMP_IDLE_MIN \
         CLONE_FRESH_MIN SCAN_EVERY_MIN SCAN_TOP BIG_FILE_MB T_SCAN; do
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
    echo "ok      another disk-cleanup (pid $holder) is running: nothing done"; exit 0; fi
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || { echo "ok      lost the lock race: nothing done"; exit 0; }
fi
echo $$ >"$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT
size_m() { [ -e "$1" ] && du -sk "$1" 2>/dev/null | awk '{printf "%d", $1/1024}' || echo 0; }

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
while IFS= read -r t; do
  [ -f "${t%/target}/Cargo.toml" ] || continue
  [ -f "$t/CACHEDIR.TAG" ] || [ -f "$t/.rustc_info.json" ] || continue
  TARGETS="$TARGETS
rust-target|$t|(^|/)(cargo|rustc)( |$)"
done <<EOF
$(find $RUST_ROOTS -maxdepth 6 \( -name node_modules -o -name .git -o -path '*/.claude/worktrees' \) -prune \
       -o -type d -name target -prune -print 2>/dev/null)
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
while IFS='|' read -r name path proc; do
  case "$path" in "$HOME"/?*|/private/tmp/?*|/tmp/?*) ;; *) echo "REFUSED $name: $path is not under HOME or /tmp"; exit 1;; esac
  m=$(size_m "$path"); total=$((total + m))
  if [ ! -e "$path" ] || [ "$m" = 0 ]; then echo "  -      $name  absent/empty  $path"; continue; fi
  if [ "$APPLY" = 0 ]; then echo "  would  $name  ${m}M  $path"; continue; fi
  if pgrep -f "$proc" >/dev/null 2>&1 && [ "$proc" != Finder-empty ]; then
    echo "  SKIP   $name  ${m}M  a '$proc' process is running and may be writing into it"; continue; fi
  if [ "$name" = trash ]; then
    find "$path" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
  else
    rm -rf "$path"
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
if [ -x "$DOCKER" ] && [ -x "$RDCTL" ] && tmo "$T_INFO" "$DOCKER" --context rancher-desktop info >/dev/null 2>&1; then
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
elif [ -x "$DOCKER" ]; then
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
if [ "$WORKTREES" = 1 ]; then
  # `git status` refreshes and rewrites the index when it can, which would reset the very idle
  # clock read above: every run would keep the worktree it looked at.
  export GIT_OPTIONAL_LOCKS=0
  CWDS=$(lsof -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
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
    git -C "$repo" worktree list --porcelain | sed -n 's/^worktree //p' | while IFS= read -r wt; do
      [ "$wt" = "$main" ] && continue
      [ -d "$wt" ] || continue
      under=
      case "$wt" in "$HOME"/?*|/private/tmp/?*|/tmp/?*) under=1;; esac
      if [ -n "$TMP_ROOT" ]; then case "$wt" in "$TMP_ROOT"/?*) under=1;; esac; fi
      if [ -z "$under" ]; then echo "  keep   worktree  $wt  (not under HOME, /tmp or \$TMPDIR)"; continue; fi
      why=$(unsettled "$repo" "$wt")
      m=$(size_m "$wt")
      salvage=; case "$why" in "~"*) salvage=${why#\~}; why=;; esac
      if [ -n "$why" ]; then echo "  keep   worktree  ${m}M  $wt  ($why)"; continue; fi
      b=$(git -C "$wt" branch --show-current); b=${b:-detached $(git -C "$wt" rev-parse --short HEAD)}
      if [ "$APPLY" = 0 ]; then echo "  would  worktree  ${m}M  $wt  ($b${salvage:+; archive: $salvage}; restore: git worktree add $wt ${b#detached })"; continue; fi
      kept=
      if [ -n "$salvage" ]; then
        kept=$(archive "$repo" "$wt" "$salvage") || { echo "  keep   worktree  ${m}M  $wt  (archive refused: $kept)"; continue; }
      fi
      # --force only when unsettled() found nothing but rebuildable output, or the leftovers are
      # archived; git still refuses a locked worktree (that needs --force twice).
      force=; { [ -n "$kept" ] || git -C "$wt" status --porcelain 2>/dev/null | grep -q .; } && force=--force
      if git -C "$repo" worktree remove $force "$wt" >/dev/null 2>&1 && [ ! -e "$wt" ]; then
        echo "  freed  worktree  ${m}M  $wt  (restore: git worktree add $wt ${b#detached }${kept:+; leftovers ($salvage): $kept})"
      else
        echo "  !! worktree $wt: git refused to remove it"; fi
    done
  done
fi

# Stale temp (worktrees=true). Measured 2026-10-14: 2.1G in the user's $TMPDIR older than 6h --
# go's go-build* dirs, mktemp -d / tempfile dirs, jest caches -- that nothing deletes (macOS clears
# it only at reboot). An entry goes when it is ours, has a tool's temp name, nothing under it was
# written in TMP_IDLE_MIN (6h), it holds no git checkout (the pass above judges those) and no
# process has a file open or its cwd under it. Only top-level entries of $TMPDIR, never $TMPDIR.
TMP_NAMES='^(go-build[0-9]+|tmp\.[A-Za-z0-9]{6,}|tmp[a-z0-9_]{8}|jest_[a-z0-9]+)$'
if [ "$WORKTREES" = 1 ] && [ -n "$TMP_ROOT" ]; then
  cands=$(find "$TMP_ROOT" -mindepth 1 -maxdepth 1 -user "$(id -u)" -mmin +"$TMP_IDLE_MIN" 2>/dev/null |
          while IFS= read -r p; do printf '%s\n' "${p##*/}" | grep -Eq "$TMP_NAMES" && printf '%s\n' "$p"; done)
  if [ -n "$cands" ]; then
    OPEN=$(lsof -Fn 2>/dev/null | sed -n 's/^n//p')
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
if [ -n "$CLONES" ] && [ -d "$CLONES" ]; then
  held=$(tmo 60 lsof -Fn +D "$CLONES" 2>/dev/null); rc=$?
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

if [ "$APPLY" = 1 ]; then
  after=$(free_k)
  echo "free after: $((after / 1024))M (measured delta $(((after - before) / 1024))M; other writers move this too)"
fi

# Report-only: the big things a human decides about. Sizes measured now, nothing deleted.
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
    k=$(tmo 120 du -sk "$p" 2>/dev/null | awk '{print $1}')
    if [ -n "$k" ]; then echo "  system  $((k / 1024))M  $p"; else echo "  system  unreadable  $p"; fi
  done
}
if [ "$APPLY" = 0 ] || [ "$(($(free_k) / 1024))" -lt "$ONLY_BELOW_MB" ]; then
  echo "where the space is (nothing here is deleted; owner decides):"
  if [ -f "$SCAN_FILE" ] && [ -n "$(find "$SCAN_FILE" -mmin -"$SCAN_EVERY_MIN" -print 2>/dev/null)" ]; then
    cat "$SCAN_FILE"
  else
    mkdir -p "$(dirname "$SCAN_FILE")"
    scan | tee "$SCAN_FILE.tmp" && mv "$SCAN_FILE.tmp" "$SCAN_FILE"
  fi
fi
[ "$fails" = 0 ] || exit 3
