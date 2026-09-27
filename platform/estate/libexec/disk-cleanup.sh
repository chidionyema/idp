#!/usr/bin/env bash
# disk-cleanup -- free the data volume by deleting ONLY regenerable package-manager caches.
#
# bin/idp-disk-guard measures and advises, and deletes nothing by design; this is the executor its
# advice points at. Default is a dry run: every target with its measured size. apply=true deletes
# the allow-list below and nothing else, then proves it: each target must be gone, and the free
# space before/after is measured, not estimated.
#
# Allow-list (all rebuilt on the next install/build, at the cost of a download):
#   yarn berry cache, go build cache, pip cache, Homebrew download cache, npm cache + npx,
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
APPLY="${1:-false}"; TRASH="${2:-false}"; ONLY_BELOW_MB="${3:-0}"
VOL="${DISK_GUARD_PATH:-/System/Volumes/Data}"   # the writable volume, as bin/idp-disk-guard
RUST_ROOTS="${DISK_CLEANUP_RUST_ROOTS:-$HOME/Documents/code/idp}"
[ -n "${HOME:-}" ] && [ "$HOME" != / ] || { echo "REFUSED HOME is unset or /"; exit 1; }
case "$APPLY" in True|true) APPLY=1;; *) APPLY=0;; esac
case "$TRASH" in True|true) TRASH=1;; *) TRASH=0;; esac
case "$ONLY_BELOW_MB" in ''|*[!0-9]*) echo "REFUSED only_below_mb=$ONLY_BELOW_MB is not a number"; exit 1;; esac

free_k() { df -k "$VOL" 2>/dev/null | awk 'NR==2 {print $4}'; }
size_m() { [ -e "$1" ] && du -sk "$1" 2>/dev/null | awk '{printf "%d", $1/1024}' || echo 0; }

# name | path | process that must not be mid-write into it
# (patterns match the tool's entry point, not any path containing its name: /opt/homebrew/bin/*
# would otherwise make every process "brew")
TARGETS="yarn-cache|$HOME/.yarn/berry/cache|yarn-[0-9.]+\.c?js|bin/yarn( |$)
go-build|$HOME/Library/Caches/go-build|go (build|test|install|run|vet) 
pip-cache|$HOME/Library/Caches/pip|pip3? (install|download|wheel)|-m pip 
homebrew-cache|$HOME/Library/Caches/Homebrew|Homebrew/brew\.rb|bin/brew( |$)
npm-cache|$HOME/.npm/_cacache|npm-cli\.js|bin/npm( |$)
npx-cache|$HOME/.npm/_npx|npx-cli\.js|bin/npx( |$)"
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
