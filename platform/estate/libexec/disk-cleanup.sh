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
#
# Exit: 0 ok, 3 a target that should be gone is not (verify failed), 1 refused.
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
APPLY="${1:-false}"; TRASH="${2:-false}"; ONLY_BELOW_MB="${3:-0}"; WORKTREES="${4:-false}"
VOL="${DISK_GUARD_PATH:-/System/Volumes/Data}"   # the writable volume, as bin/idp-disk-guard
RUST_ROOTS="${DISK_CLEANUP_RUST_ROOTS:-$HOME/Documents/code/idp}"
WT_REPOS="${DISK_CLEANUP_WT_REPOS:-$HOME/Documents/code/idp}"
WT_IDLE_MIN="${DISK_CLEANUP_WT_IDLE_MIN:-360}"
[ -n "${HOME:-}" ] && [ "$HOME" != / ] || { echo "REFUSED HOME is unset or /"; exit 1; }
case "$APPLY" in True|true) APPLY=1;; *) APPLY=0;; esac
case "$TRASH" in True|true) TRASH=1;; *) TRASH=0;; esac
case "$WORKTREES" in True|true) WORKTREES=1;; *) WORKTREES=0;; esac
case "$WT_IDLE_MIN" in ''|*[!0-9]*) echo "REFUSED DISK_CLEANUP_WT_IDLE_MIN=$WT_IDLE_MIN is not a number"; exit 1;; esac
case "$ONLY_BELOW_MB" in ''|*[!0-9]*) echo "REFUSED only_below_mb=$ONLY_BELOW_MB is not a number"; exit 1;; esac

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
    echo "  SKIP   docker  a docker build is running"
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
#   - its index, HEAD and reflog untouched for WT_IDLE_MIN minutes (default 6h).
# Removal is `git worktree remove` WITHOUT --force, so git re-checks cleanliness itself, except when
# the only changes are rebuildable output (then --force, once; a lock still refuses). No
# process is signalled and nothing outside the worktree directory is touched.
REBUILDABLE='(^|/)(node_modules|target|dist|dist-types|build|__pycache__|\.pytest_cache|\.ruff_cache|\.mypy_cache|\.venv|venv|\.tox|coverage|\.coverage|\.turbo|\.next|\.cache|htmlcov)(/|$)|\.pyc$|\.tsbuildinfo$'
unsettled() {
  local repo=$1 wt=$2 out gd
  out=$(git -C "$wt" status --porcelain --ignored=matching 2>/dev/null) || { echo "git status failed"; return; }
  # A change confined to rebuildable output (a branch cut before target/ was untracked, then
  # cargo-cleaned: 1669 " D .../target/..." lines) is build output, not work.
  if printf '%s\n' "$out" | grep -v '^!! ' | cut -c4- | grep -Ev "$REBUILDABLE" | grep -q .; then echo "uncommitted or untracked files"; return; fi
  if printf '%s\n' "$out" | sed -n 's/^!! //p' | grep -Ev "$REBUILDABLE" | grep -q .; then
    echo "ignored files that are not build output"; return; fi
  # Every commit must stay reachable from a ref once the checkout is gone. A branch keeps its own
  # commits (pushed or not, squash-merged or not); a detached HEAD's commits must be on a branch,
  # tag or remote, or `git gc` would eventually take them.
  out=$(git -C "$wt" rev-list -n1 HEAD --not --branches --tags --remotes 2>/dev/null) || { echo "git rev-list failed"; return; }
  if [ -n "$out" ] || ! git -C "$wt" rev-parse -q --verify HEAD >/dev/null; then
    echo "commits reachable only from this checkout's HEAD"; return; fi
  if git -C "$repo" worktree list --porcelain | awk -v w="$wt" '$1=="worktree"{c=($2==w)} c&&$1=="locked"{f=1} END{exit !f}'; then
    echo "locked"; return; fi
  # lsof reports resolved paths (/private/tmp), git the path it was given (/tmp): compare both.
  if printf '%s\n' "$CWDS" | awk -v w="$wt" -v r="$(cd "$wt" && pwd -P)" \
       'index($0, w"/")==1 || $0==w || index($0, r"/")==1 || $0==r {f=1} END{exit !f}'; then
    echo "a process is working inside it"; return; fi
  gd=$(git -C "$wt" rev-parse --absolute-git-dir 2>/dev/null) || { echo "no git dir"; return; }
  # A checkout whose HEAD is already in origin/main holds nothing that is not on main: it needs no
  # idle wait (the wait only guards work in progress, and there is none to lose).
  git -C "$wt" merge-base --is-ancestor HEAD origin/main 2>/dev/null && return
  if [ "$WT_IDLE_MIN" -gt 0 ] && [ -n "$(find "$gd/index" "$gd/HEAD" "$gd/logs/HEAD" -mmin -"$WT_IDLE_MIN" 2>/dev/null | head -1)" ]; then
    echo "used in the last ${WT_IDLE_MIN}m"; return; fi
}
if [ "$WORKTREES" = 1 ]; then
  CWDS=$(lsof -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  for repo in $WT_REPOS; do
    [ -d "$repo" ] || continue
    main=$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null) || continue
    git -C "$repo" worktree list --porcelain | sed -n 's/^worktree //p' | while IFS= read -r wt; do
      [ "$wt" = "$main" ] && continue
      [ -d "$wt" ] || continue
      case "$wt" in "$HOME"/?*|/private/tmp/?*|/tmp/?*) ;; *) echo "  keep   worktree  $wt  (not under HOME or /tmp)"; continue;; esac
      why=$(unsettled "$repo" "$wt")
      m=$(size_m "$wt")
      if [ -n "$why" ]; then echo "  keep   worktree  ${m}M  $wt  ($why)"; continue; fi
      b=$(git -C "$wt" branch --show-current); b=${b:-detached $(git -C "$wt" rev-parse --short HEAD)}
      if [ "$APPLY" = 0 ]; then echo "  would  worktree  ${m}M  $wt  ($b; restore: git worktree add $wt ${b#detached })"; continue; fi
      # --force only when unsettled() found nothing but rebuildable output; git still refuses a
      # locked worktree (that needs --force twice).
      force=; git -C "$wt" status --porcelain 2>/dev/null | grep -q . && force=--force
      if git -C "$repo" worktree remove $force "$wt" >/dev/null 2>&1 && [ ! -e "$wt" ]; then
        echo "  freed  worktree  ${m}M  $wt  (restore: git worktree add $wt ${b#detached })"
      else
        echo "  !! worktree $wt: git refused to remove it"; fi
    done
  done
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
[ "$fails" = 0 ] || exit 3
