#!/bin/bash
# Disk Sentinel forensic diagnostic: read-only, low priority, bounded execution.
# Designed for macOS Bash 3.2. No sudo, Node, Python, Homebrew or downloads.
set -u
export LC_ALL=C
MODE="${1:---deep}"
case "$MODE" in --deep|--quick) ;; -h|--help) echo 'Usage: bash disk_sentinel_forensics_macos.sh [--deep|--quick]'; exit 0 ;; *) echo 'ERROR: use --deep or --quick' >&2; exit 2 ;; esac
if [ "$(/usr/bin/uname -s)" != 'Darwin' ]; then echo 'BLOCKED: macOS only; no changes made.' >&2; exit 2; fi

# tempfile may be unavailable on genuinely exhausted disks; never pretend a report exists.
WORK=$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/sentinel-forensics.XXXXXXXX" 2>/dev/null) || {
  echo 'BLOCKED: No space for even temporary diagnostic output. Immediate read-only telemetry:'
  /bin/df -h "$HOME" /
  exit 3
}
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
TOTAL_BUDGET=185
[ "$MODE" = '--quick' ] && TOTAL_BUDGET=55
START_EPOCH=$(/bin/date +%s)
START_FREE_K=$(/bin/df -kP "$HOME" 2>/dev/null | /usr/bin/awk 'NR==2 {print $4}')
DEADLINE=$(( START_EPOCH + TOTAL_BUDGET ))
SUMMARY="$WORK/summary.tsv"
: > "$SUMMARY"

headr() { printf '\n==== %s ====\n' "$1"; }
# Throttle background disk I/O as well as CPU, when macOS taskpolicy is present.
gentle() {
  local policy
  policy=$(command -v taskpolicy 2>/dev/null || true)
  if [ -n "$policy" ]; then
    "$policy" -b -d throttle /usr/bin/nice -n 15 "$@"
  else
    /usr/bin/nice -n 15 "$@"
  fi
}
nowleft() { echo $(( DEADLINE - $(/bin/date +%s) )); }
# Always print errors and non-completion; incomplete measurements cannot be treated as zero use.
run() {
  local title="$1" secs="$2" limit pid elapsed=0 rc=0 timeout=0
  shift 2
  printf '\n-- %s --\n' "$title"
  limit=$(nowleft)
  if [ "$limit" -le 0 ]; then echo 'SKIPPED: global safety time budget exhausted'; return 124; fi
  [ "$secs" -lt "$limit" ] && limit="$secs"
  : > "$WORK/out"; : > "$WORK/err"
  "$@" > "$WORK/out" 2> "$WORK/err" &
  pid=$!
  while /bin/kill -0 "$pid" 2>/dev/null; do
    if [ "$elapsed" -ge "$limit" ]; then
      timeout=1
      /bin/kill -TERM "$pid" 2>/dev/null || true
      /bin/sleep 1
      /bin/kill -KILL "$pid" 2>/dev/null || true
      break
    fi
    /bin/sleep 1
    elapsed=$((elapsed+1))
  done
  wait "$pid" 2>/dev/null; rc=$?
  if [ "$timeout" -eq 1 ]; then
    echo 'INCOMPLETE: timed out; measurement excluded from ranked totals.'
  elif [ "$rc" -ne 0 ]; then
    echo "PARTIAL/ERROR: command exit $rc; results may omit protected paths."
  else
    echo 'COMPLETE'
  fi
  case "$title" in
    'Home root'*|'Library, one directory level'*|'Current working directory, one directory level'*)
      /usr/bin/sort -nr -k1,1 "$WORK/out" | /usr/bin/head -n 32 ;;
    'Process list'*)
      /usr/bin/sed -n '1,55p' "$WORK/out" ;;
    'Files >500 MiB'*)
      /usr/bin/sort -nr -k1,1 "$WORK/out" | /usr/bin/head -n 35 ;;
    *) /usr/bin/sed -n '1,55p' "$WORK/out" ;;
  esac
  if [ -s "$WORK/err" ]; then
    echo 'Notices (first 5):'
    /usr/bin/sed -n '1,5p' "$WORK/err"
  fi
  [ "$timeout" -eq 0 ] && [ "$rc" -eq 0 ]
}

# For a single path, du counts allocated disk blocks, not apparent file size.
measure() {
  local label="$1" path="$2" secs="$3" limit pid elapsed=0 rc=0 timeout=0 kb
  [ -e "$path" ] || return 0
  limit=$(nowleft)
  if [ "$limit" -le 0 ]; then printf 'SKIPPED (budget)  %-34s %s\n' "$label" "$path"; return; fi
  [ "$secs" -lt "$limit" ] && limit="$secs"
  gentle /usr/bin/du -skx "$path" > "$WORK/out" 2> "$WORK/err" &
  pid=$!
  while /bin/kill -0 "$pid" 2>/dev/null; do
    if [ "$elapsed" -ge "$limit" ]; then
      timeout=1
      /bin/kill -TERM "$pid" 2>/dev/null || true
      /bin/sleep 1
      /bin/kill -KILL "$pid" 2>/dev/null || true
      break
    fi
    /bin/sleep 1
    elapsed=$((elapsed+1))
  done
  wait "$pid" 2>/dev/null; rc=$?
  if [ "$timeout" -eq 1 ]; then
    printf 'TIMEOUT          %-34s %s\n' "$label" "$path"
    return
  fi
  kb=$(/usr/bin/awk 'NR==1 && $1 ~ /^[0-9]+$/ {print $1}' "$WORK/out")
  if [ -z "$kb" ]; then
    printf 'UNKNOWN          %-34s %s\n' "$label" "$path"
    return
  fi
  /usr/bin/awk -v k="$kb" -v l="$label" -v p="$path" -v r="$rc" 'BEGIN {printf "%7.2f GiB  %-34s %s%s\n", k/1048576,l,p,(r==0?"":" [PARTIAL]")}'
  if [ "$rc" -eq 0 ]; then
    printf '%s\t%s\t%s\n' "$kb" "$label" "$path" >> "$SUMMARY"
  fi
}

printf 'DISK SENTINEL / MACOS READ-ONLY ROOT-CAUSE AUDIT\n'
printf 'Captured: %s | Mode: %s\n' "$(/bin/date '+%Y-%m-%d %H:%M:%S %Z')" "$MODE"
echo 'No deletion, process termination (other than this script\047s own bounded probes), sudo, network, or service changes.'
echo 'Inventory paths can contain identifying project/user names. Review/redact before sharing.'

headr 'A. Physical/volume truth'
run 'df: actual capacity and available blocks' 5 /bin/df -h "$HOME" / || true
run 'macOS version and architecture' 4 /usr/bin/sw_vers || true
run 'APFS filesystem and volume details' 8 /usr/sbin/diskutil info "$HOME" || true
run 'APFS volume/container accounting' 12 /usr/sbin/diskutil apfs list || true
run 'Time Machine local snapshot inventory' 8 /usr/bin/tmutil listlocalsnapshots / || true
if [ -d /System/Volumes/Data ]; then
  run 'APFS data-volume snapshot inventory' 10 /usr/sbin/diskutil apfs listSnapshots /System/Volumes/Data || true
fi

headr 'B. Top-level allocated disk occupancy (measurements may be partial under macOS privacy controls)'
run 'Home root, one directory level (GiB values listed in KiB; do not sum parent+child)' 26 gentle /usr/bin/du -kxd 1 "$HOME" || true
run 'Library, one directory level' 25 gentle /usr/bin/du -kxd 1 "$HOME/Library" || true
if [ "$PWD" != "$HOME" ]; then
  run 'Current working directory, one directory level' 15 gentle /usr/bin/du -kxd 1 "$PWD" || true
fi

headr 'C. High-probability engineering consumers: actual allocated GiB, overlapping paths NOT additive'
# Specific high-impact paths are first, so pressure cannot starve all useful evidence.
measure 'Docker.raw (sparse actual blocks)' "$HOME/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw" 3
measure 'Docker.raw alternate location' "$HOME/.docker/desktop/vms/0/data/Docker.raw" 3
measure 'Xcode DerivedData' "$HOME/Library/Developer/Xcode/DerivedData" 6
measure 'Xcode archive/dSYMs' "$HOME/Library/Developer/Xcode/Archives" 5
measure 'iOS simulators' "$HOME/Library/Developer/CoreSimulator/Devices" 6
measure 'iOS device backups' "$HOME/Library/Application Support/MobileSync/Backup" 5
measure 'Colima virtual machines' "$HOME/.colima" 5
measure 'OrbStack virtual machines' "$HOME/.orbstack" 5
measure 'Lima virtual machines' "$HOME/.lima" 5
measure 'Android SDK / emulators' "$HOME/Library/Android" 5
measure 'Docker Desktop VM/container' "$HOME/Library/Containers/com.docker.docker" 8
measure 'Xcode / simulators' "$HOME/Library/Developer" 9
measure 'Application Support' "$HOME/Library/Application Support" 9
measure 'User Library Caches' "$HOME/Library/Caches" 8
measure 'Library Logs' "$HOME/Library/Logs" 5
measure 'npm cache' "$HOME/.npm" 5
measure 'nvm installations / cache' "$HOME/.nvm" 6
measure 'General tool cache' "$HOME/.cache" 5
measure 'Agent and application data' "$HOME/.local/share" 6
measure 'Agent state / logging' "$HOME/.local/state" 5
measure 'Docker CLI context' "$HOME/.docker" 4
measure 'Cargo / Rust' "$HOME/.cargo" 5
measure 'Rustup' "$HOME/.rustup" 5
measure 'Gradle' "$HOME/.gradle" 5
measure 'Maven' "$HOME/.m2" 5
measure '.NET NuGet packages' "$HOME/.nuget" 5
measure 'Claude agent data' "$HOME/.claude" 5
measure 'Codex agent data' "$HOME/.codex" 5
measure 'Kimi agent data' "$HOME/.kimi" 5
measure 'OpenCode state' "$HOME/.opencode" 5
measure 'Downloads' "$HOME/Downloads" 6
measure 'Desktop' "$HOME/Desktop" 5
measure 'Documents' "$HOME/Documents" 5
measure 'Current repository' "$PWD" 7
measure 'System swap (non-destructive)' /private/var/vm 5
measure 'macOS private temp caches' /private/var/folders 5
measure 'MacPorts installation' /opt/local 5
measure 'Homebrew Intel install' /usr/local/Cellar 5
measure 'Homebrew Apple Silicon' /opt/homebrew/Cellar 5
measure 'Users Shared' /Users/Shared 5

headr 'D. Reclaimability diagnostics (advisory only; never prune automatically)'
if command -v docker >/dev/null 2>&1; then
  run 'Docker object and build cache allocation' 10 docker system df || true
else echo 'Docker CLI not on PATH; Docker Desktop volume measurement above may still apply.'; fi
if command -v brew >/dev/null 2>&1; then
  run 'Homebrew supported cleanup DRY-RUN' 10 brew cleanup -n || true
else echo 'Homebrew not on PATH.'; fi
if command -v xcrun >/dev/null 2>&1; then
  run 'Xcode simulator availability inventory' 10 xcrun simctl list devices || true
fi

headr 'E. Sentinel self-health and live workload'
if [ -x "$HOME/.local/share/disk-sentinel/sentinel.sh" ]; then
  run 'Disk Sentinel registered status' 6 "$HOME/.local/share/disk-sentinel/sentinel.sh" status || true
else
  echo 'Disk Sentinel binary not found at its standard installation path.'
fi
run 'System load and swap' 5 /usr/bin/uptime || true
run 'Swap use' 5 /usr/sbin/sysctl vm.swapusage || true
run 'Process list (command names only, includes running tasks)' 8 /bin/ps -axo pid,ppid,%cpu,%mem,etime,comm || true
if command -v lsof >/dev/null 2>&1; then
  run 'Open but unlinked files (may hold allocated disk blocks)' 10 /usr/sbin/lsof -nP +L1 || true
fi

if [ "$MODE" = '--deep' ] && [ "$(nowleft)" -ge 10 ]; then
  headr 'F. Large-file outliers (allocated size may differ for sparse files)'
  run 'Files >500 MiB beneath home; logical byte sizes; protected paths may be hidden' 28 \
    gentle /usr/bin/find "$HOME" -x -type f -size +500M -exec /usr/bin/stat -f '%z  %N' '{}' + || true
  echo 'Cross-check every candidate with du -h before interpreting logical size as actual occupied blocks.'
fi

headr 'G. Ranked complete measurements (do not add rows; they overlap)'
if [ -s "$SUMMARY" ]; then
  /usr/bin/sort -nr -k1,1 "$SUMMARY" | /usr/bin/head -n 25 | /usr/bin/awk -F '\t' '{printf "%7.2f GiB  %-34s %s\n", $1/1048576,$2,$3}'
else
  echo 'None completed; cannot attribute capacity reliably.'
fi

headr 'H. Net consumption during diagnostic window'
END_EPOCH=$(/bin/date +%s)
END_FREE_K=$(/bin/df -kP "$HOME" 2>/dev/null | /usr/bin/awk 'NR==2 {print $4}')
if [ -n "$START_FREE_K" ] && [ -n "$END_FREE_K" ]; then
  /usr/bin/awk -v a="$START_FREE_K" -v b="$END_FREE_K" -v s="$((END_EPOCH-START_EPOCH))" \
    'BEGIN {printf "Elapsed: %ds; net consumed: %.3f GiB (negative means space recovered).\n", s,(a-b)/1048576}'
fi

headr 'I. Root-cause decision rules'
echo '1. Compare df available GiB with the largest COMPLETE du rows (allocated, not nominal capacity).'
echo '2. Docker: compare Docker.raw du usage against docker system df. Never delete Docker.raw or volumes.'
echo '3. If df reports much less free space than visible files explain, investigate snapshots, other APFS volumes, open-unlinked files and restricted folders.'
echo '4. Check whether a current process is producing rapidly growing logs/artifacts before approving any reclaim.'
echo '5. Do not sum nested paths or treat partial/timeout output as evidence of low use.'
echo '6. Recommended sustainable reserve for a 112.7 GiB development volume: approximately 15-20 GiB, adjustable to measured peak workload.'
echo '7. This audit does not modify Disk Sentinel. Add enforcement only after evidence, owner verification and a tested rollback path.'
echo 'AUDIT COMPLETE (capture finished; cause remains unverified until findings are reviewed).'
