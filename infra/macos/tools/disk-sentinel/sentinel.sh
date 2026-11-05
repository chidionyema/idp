#!/bin/bash
# Disk Sentinel - macOS disk pressure observer, read-only inventory, self-owned retention.
# No automatic deletion of any third-party path.
set -u
umask 077

APP="${DISK_SENTINEL_APP:-$HOME/.local/share/disk-sentinel}"
STATE="${DISK_SENTINEL_STATE:-$HOME/.local/state/disk-sentinel}"
DASH="$APP/dashboard.html"
HISTORY="$STATE/history.tsv"
INVENTORY="$STATE/inventory.tsv"
STATUS="$STATE/status.env"
RESERVE="$STATE/emergency.reserve"
LABEL="dev.disksentinel.monitor"

mkdir -p "$APP" "$STATE" 2>/dev/null || { echo 'BLOCKED: cannot create sentinel state directory (disk full or permissions)' >&2; exit 1; }

bytes_gib() { awk -v k="$1" 'BEGIN {printf "%.1f",k/1048576}' ; }
escape_html() { printf '%s' "$1" | sed -e 's/\&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g'; }
notify() {
  command -v osascript >/dev/null 2>&1 || return 0
  local message="$1"
  /usr/bin/osascript -e "display notification \"$message\" with title \"Disk Sentinel\"" >/dev/null 2>&1 || true
}

lock_acquire() {
  local lock="$1" pid=""
  if mkdir "$lock" 2>/dev/null; then
    printf '%s\n' "$$" > "$lock/pid" 2>/dev/null || true
    return 0
  fi
  if [ -r "$lock/pid" ]; then read -r pid < "$lock/pid" || true; fi
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  if kill -0 "$pid" 2>/dev/null; then return 1; fi
  # Reclaim only dead-process locks. Never delete another living process's lock.
  rm -f "$lock/pid" 2>/dev/null || true
  rmdir "$lock" 2>/dev/null || return 1
  mkdir "$lock" 2>/dev/null || return 1
  printf '%s\n' "$$" > "$lock/pid" 2>/dev/null || true
}
lock_release() { rm -f "$1/pid" 2>/dev/null || true; rmdir "$1" 2>/dev/null || true; }

get_space() {
  local line
  line=$(/bin/df -kP "$HOME" 2>/dev/null | /usr/bin/awk 'NR==2 {print $2, $4}') || return 1
  read -r TOTAL_K AVAILABLE_K <<< "$line"
  case "$TOTAL_K:$AVAILABLE_K" in *[!0-9:]*|:*|*:) return 1 ;; esac
  [ "$TOTAL_K" -gt 0 ] || return 1
}

find_trend() {
  RATE_KPH=0; ETA_HOURS="--"
  [ -s "$HISTORY" ] || return 0
  local now="$1" current="$2" result delta_dt delta_k
  # Sample nearest to 6 hours ago, falling back to oldest sample >=30 minutes old.
  result=$(/usr/bin/awk -F '\t' -v n="$now" '
    $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && $1 < n-1800 && $1 >= n-86400 {
      gap=(n-21600)-$1; if (gap<0) gap=-gap
      if (!found || gap<best) { best=gap; ts=$1; kb=$2; found=1 }
    }
    END { if (found) print ts, kb }
  ' "$HISTORY")
  [ -n "$result" ] || return 0
  read -r old_t old_k <<< "$result"
  delta_dt=$((now-old_t))
  [ "$delta_dt" -gt 0 ] || return 0
  delta_k=$((old_k-current))
  RATE_KPH=$(/usr/bin/awk -v k="$delta_k" -v sec="$delta_dt" 'BEGIN {printf "%.0f",k*3600/sec}')
  if [ "$RATE_KPH" -gt 102400 ]; then
    ETA_HOURS=$(/usr/bin/awk -v k="$current" -v r="$RATE_KPH" 'BEGIN {printf "%.1f",k/r}')
  fi
}

metric_status() {
  # Use both absolute and proportional guards, with a maximum on each severity.
  local warn=$((15*1048576)) crit=$((5*1048576)) emergency=$((2*1048576))
  [ $((TOTAL_K/10)) -gt "$warn" ] && warn=$((TOTAL_K/10))
  [ $((TOTAL_K/20)) -gt "$crit" ] && crit=$((TOTAL_K/20))
  [ $((TOTAL_K/50)) -gt "$emergency" ] && emergency=$((TOTAL_K/50))
  SEVERITY="HEALTHY"
  [ "$AVAILABLE_K" -lt "$warn" ] && SEVERITY="WARNING"
  [ "$AVAILABLE_K" -lt "$crit" ] && SEVERITY="CRITICAL"
  [ "$AVAILABLE_K" -lt "$emergency" ] && SEVERITY="EMERGENCY"
  # Predictive flag: 12-hour projected exhaustion if measured sustained growth.
  if [ "$RATE_KPH" -gt 102400 ] && [ $((AVAILABLE_K/RATE_KPH)) -le 12 ]; then
    [ "$SEVERITY" = "HEALTHY" ] && SEVERITY="WARNING"
  fi
}

# The storage-pressure control plane (founder, 2026-11-05). Four modes by ABSOLUTE free space,
# because "15% of 113 GiB" is not the same safety margin as "15% of 1 TiB": what matters is whether
# there is room to work. Each mode says what the supervisor is allowed to do, so an expensive
# investigation cannot start on a volume that is already failing.
# The reserve is the line an owner must not cross: below it, discretionary disk-heavy work is
# refused and only reclamation/observation may run. Provisional 15 GiB on a 113 GiB volume
# (founder, 2026-11-05), overridable without editing code.
DISK_SENTINEL_RESERVE_GIB=${DISK_SENTINEL_RESERVE_GIB:-15}
DISK_SENTINEL_WARNING_GIB=${DISK_SENTINEL_WARNING_GIB:-20}

policy_load() {
  local f="$STATE/policy.conf" line k v
  [ -r "$f" ] || return 0
  while IFS='=' read -r k v; do
    case "$k" in
      RESERVE_GIB) case "$v" in ''|*[!0-9]*) ;; *) DISK_SENTINEL_RESERVE_GIB=$v ;; esac ;;
      WARNING_GIB) case "$v" in ''|*[!0-9]*) ;; *) DISK_SENTINEL_WARNING_GIB=$v ;; esac ;;
    esac
  done < "$f"
}

storage_mode() {
  local avail=${1:-$AVAILABLE_K} reserve warning
  reserve=$(( ${DISK_SENTINEL_RESERVE_GIB:-15} * 1048576 ))
  warning=$(( ${DISK_SENTINEL_WARNING_GIB:-20} * 1048576 ))
  case "$avail" in ''|*[!0-9]*) echo UNKNOWN; return 0 ;; esac
  if [ "$avail" -gt "$warning" ]; then echo NORMAL
  elif [ "$avail" -ge "$reserve" ]; then echo WARNING
  elif [ "$avail" -ge $((3*1048576)) ]; then echo CRITICAL
  else echo EMERGENCY; fi
}

mode_policy() {
  case "$1" in
    NORMAL) echo 'capacity tracking, growth attribution, retention accounting' ;;
    WARNING) echo 'identify fast-growing owners, report reclaimable capacity' ;;
    CRITICAL) echo 'expensive scans suspended; verify low-risk reclamation before acting' ;;
    EMERGENCY) echo 'optional investigations stopped; preserve headroom and notify' ;;
    *) echo 'free space could not be measured; refusing nothing on a BLIND reading' ;;
  esac
}

# Given the current free space, may an optional (expensive) investigation start?
# BLIND is not a refusal: an unmeasurable volume must not be mistaken for a full one.
# One reader for "how much is free right now", with a test seam: the thresholds are the part
# that must be provable without filling a disk, so a test can name the number instead of
# pretending the machine is full.
current_avail_k() {
  if [ -n "${DISK_SENTINEL_TEST_AVAIL_K:-}" ]; then printf '%s\n' "$DISK_SENTINEL_TEST_AVAIL_K"; return 0; fi
  /bin/df -kP "$HOME" 2>/dev/null | /usr/bin/awk 'NR==2 {print $4}'
}

optional_allowed() {
  local avail mode
  avail=$(current_avail_k)
  case "$avail" in ''|*[!0-9]*) return 0 ;; esac
  mode=$(storage_mode "$avail")
  case "$mode" in CRITICAL|EMERGENCY) return 1 ;; *) return 0 ;; esac
}

refuse_optional() {
  local what=$1 avail mode
  avail=$(current_avail_k)
  mode=$(storage_mode "$avail")
  printf 'REFUSED: %s is an optional investigation and %s mode suspends it (%s free).\n' \
    "$what" "$mode" "$(bytes_gib "${avail:-0}") GiB"
  printf '  Policy: %s\n' "$(mode_policy "$mode")"
  echo '  Reclaim capacity first, or pass --force to run it anyway (still read-only, still bounded).'
  return 75
}

# Event-triggered capture (founder, 2026-11-05). Scanning hundreds of thousands of files is
# the wrong instrument for "something is eating the disk right now": the monitor already takes
# one sample a minute, so a sharp fall is a machine-observable event. When free space drops past
# a threshold inside a window, capture the cheap evidence once - no walk, no sudo, bounded work.
DISK_SENTINEL_DROP_MIB=${DISK_SENTINEL_DROP_MIB:-512}
DISK_SENTINEL_DROP_WINDOW_MIN=${DISK_SENTINEL_DROP_WINDOW_MIN:-5}
DISK_SENTINEL_CAPTURE_COOLDOWN_MIN=${DISK_SENTINEL_CAPTURE_COOLDOWN_MIN:-15}
CAPTURES="$STATE/captures"
CAPTURE_COOLDOWN="$STATE/capture.cooldown"

policy_load_capture() {
  local f="$STATE/policy.conf" k v
  [ -r "$f" ] || return 0
  while IFS='=' read -r k v; do
    case "$k" in
      DROP_MIB) case "$v" in ''|*[!0-9]*) ;; *) DISK_SENTINEL_DROP_MIB=$v ;; esac ;;
      DROP_WINDOW_MIN) case "$v" in ''|*[!0-9]*) ;; *) DISK_SENTINEL_DROP_WINDOW_MIN=$v ;; esac ;;
      CAPTURE_COOLDOWN_MIN) case "$v" in ''|*[!0-9]*) ;; *) DISK_SENTINEL_CAPTURE_COOLDOWN_MIN=$v ;; esac ;;
    esac
  done < "$f"
}

# KB lost between the oldest sample inside the window and the newest one.
window_drop_k() {
  local now=$1 win=$(( ${DISK_SENTINEL_DROP_WINDOW_MIN:-5} * 60 ))
  [ -s "$HISTORY" ] || return 0
  /usr/bin/awk -v now="$now" -v win="$win" -F '\t' '
    ($1+0) >= (now-win) { if (!n) first=$2; last=$2; n++ }
    END { if (n >= 2 && first+0 > last+0) printf "%d", first-last }
  ' "$HISTORY"
}

capture_now() {
  local drop_k=$1 stamp file
  stamp=$(/bin/date '+%Y%m%d-%H%M%S')
  file="$CAPTURES/capture-$stamp.txt"
  /bin/mkdir -p "$CAPTURES" 2>/dev/null || return 0
  {
    printf 'DISK SENTINEL / TRIGGERED CAPTURE\n'
    printf 'Captured: %s | free-space drop %s MiB inside %s min\n\n' \
      "$(/bin/date '+%Y-%m-%d %H:%M:%S %Z')" "$((drop_k/1024))" "${DISK_SENTINEL_DROP_WINDOW_MIN:-5}"
    printf '=== CAPACITY ===\n'; /bin/df -h "$HOME" 2>/dev/null
    printf '\n=== SWAP ===\n'; /usr/sbin/sysctl -n vm.swapusage 2>/dev/null
    printf '\n=== MODE ===\n%s\n' "$(storage_mode "${AVAILABLE_K:-0}")"
    printf '\n=== SAMPLES IN WINDOW (epoch, free KiB) ===\n'
    /usr/bin/tail -n 8 "$HISTORY" 2>/dev/null
    printf '\n=== TOP CPU (may be unavailable under I/O starvation) ===\n'
    /usr/bin/timeout 5 /bin/ps -axo pid,%cpu,%mem,comm 2>/dev/null | /usr/bin/sort -k2 -nr | /usr/bin/head -6 \
      || printf 'unavailable: ps did not answer in 5s\n'
    printf '\n=== LARGEST OPEN FILES OF THIS USER (bounded) ===\n'
    /usr/bin/timeout 8 /usr/sbin/lsof -nP 2>/dev/null \
      | /usr/bin/awk 'NR>1 && $5=="REG" && $7 ~ /^[0-9]+$/ && $7 > 52428800 {printf "%7.1f MiB  %s %s\n", $7/1048576, $1, $9}' \
      | /usr/bin/sort -rn | /usr/bin/head -10 || true
    printf '\nNote: no root view. Deleted-but-open files of system daemons need sudo lsof.\n'
  } > "$file" 2>/dev/null
  # Keep the last 20 captures; they are small text and the point is the recent shape.
  /bin/ls -1t "$CAPTURES" 2>/dev/null | /usr/bin/tail -n +21 | while IFS= read -r old; do
    /bin/rm -f "$CAPTURES/$old" 2>/dev/null || true
  done
  printf '%s\n' "$(cat "$file" 2>/dev/null | /usr/bin/head -n 12)"
}

maybe_capture() {
  local now=$1 last=0 drop
  if [ -s "$CAPTURE_COOLDOWN" ]; then read -r last < "$CAPTURE_COOLDOWN" 2>/dev/null || true; fi
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  [ $((now-last)) -lt $(( ${DISK_SENTINEL_CAPTURE_COOLDOWN_MIN:-15} * 60 )) ] && return 0
  drop=$(window_drop_k "$now")
  [ -n "$drop" ] || return 0
  [ "$drop" -lt $(( ${DISK_SENTINEL_DROP_MIB:-512} * 1024 )) ] && return 0
  printf '%s\n' "$now" > "$CAPTURE_COOLDOWN" 2>/dev/null || true
  capture_now "$drop"
}

reserve_maintain() {
  # Dedicated self-owned emergency reserve: released automatically under pressure.
  # Never allocate at installation when disk is already tight.
  if [ "$SEVERITY" = "EMERGENCY" ] && [ -f "$RESERVE" ]; then
    /bin/rm -f "$RESERVE" && notify 'Emergency reserve released (64 MiB)'
  elif [ "$SEVERITY" = "HEALTHY" ] && [ "$AVAILABLE_K" -ge $((25*1048576)) ] && [ ! -e "$RESERVE" ]; then
    # mkfile allocates real blocks on macOS. Failure is non-fatal.
    if [ -x /usr/bin/mkfile ]; then
      /usr/bin/mkfile 64m "$RESERVE.tmp" 2>/dev/null && /bin/mv -f "$RESERVE.tmp" "$RESERVE" || /bin/rm -f "$RESERVE.tmp"
    fi
  fi
}

managed_gc() {
  # Never touches other software or user's working directories.
  [ -d "$STATE/diagnostics" ] && /usr/bin/find "$STATE/diagnostics" -type f -mtime +14 -delete 2>/dev/null || true
  # Constrain sample history to 7 days / 10,080 minute records.
  if [ -s "$HISTORY" ] && [ "$(/usr/bin/wc -l < "$HISTORY" | /usr/bin/tr -d ' ')" -gt 10080 ]; then
    /usr/bin/tail -n 10080 "$HISTORY" > "$HISTORY.tmp" 2>/dev/null && /bin/mv -f "$HISTORY.tmp" "$HISTORY" || /bin/rm -f "$HISTORY.tmp"
  fi
}

inventory_rows() {
  [ -s "$INVENTORY" ] || { echo '<p class="muted">No directory inventory yet. Run <code>disk-sentinel scan</code> to collect read-only measurements.</p>'; return; }
  local label kb risk note size class count=0
  while IFS='|' read -r label kb risk note; do
    [ -n "$kb" ] || continue
    case "$kb" in *[!0-9]*) continue ;; esac
    size=$(bytes_gib "$kb")
    class="caution"; [ "$risk" = 'Protected' ] && class="protected"
    printf '<div class="candidate"><div><strong>%s</strong><p>%s</p></div><div class="right"><b>%s GiB</b><span class="risk %s">%s</span></div></div>\n' "$(escape_html "$label")" "$(escape_html "$note")" "$size" "$class" "$(escape_html "$risk")"
    count=$((count+1)); [ "$count" -ge 10 ] && break
  done < "$INVENTORY"
}

render_dashboard() {
  MODE=${MODE:-$(storage_mode "${AVAILABLE_K:-0}")}
  local now_human free_gib total_gib used_pct growth labelg trend_text reserve_state chart_data scan_age scan_note color
  now_human=$(/bin/date '+%Y-%m-%d %H:%M:%S %Z')
  free_gib=$(bytes_gib "$AVAILABLE_K")
  total_gib=$(bytes_gib "$TOTAL_K")
  used_pct=$(/usr/bin/awk -v a="$AVAILABLE_K" -v t="$TOTAL_K" 'BEGIN {printf "%.1f",100*(t-a)/t}')
  growth=$(/usr/bin/awk -v rate="$RATE_KPH" 'BEGIN {printf "%.2f",rate/1048576}')
  trend_text="Forecast requires >=30 minutes of observations"
  if [ "$RATE_KPH" -gt 102400 ]; then trend_text="Net consumption ${growth} GiB/hour - projected depletion in ${ETA_HOURS} hours (estimate)"; fi
  if [ "$RATE_KPH" -le 0 ] && [ -s "$HISTORY" ]; then
    local first_t
    first_t=$(/usr/bin/awk -F '\t' 'NR==1 {print $1}' "$HISTORY")
    case "$first_t" in *[!0-9]*|'') ;; *)
      [ $((now-first_t)) -ge 1800 ] && trend_text="No sustained net consumption detected in the observed window" ;;
    esac
  fi
  reserve_state="Not allocated"; [ -f "$RESERVE" ] && reserve_state="64 MiB allocated - automatic release at emergency"
  scan_note="Not yet scanned"; [ -s "$STATE/scan.completed" ] && scan_note="Last complete read-only scan: $(cat "$STATE/scan.completed")"
  if [ -s "$STATE/scan.state" ]; then
    local scan_timestamp scan_status scan_details
    IFS='|' read -r scan_timestamp scan_status scan_details < "$STATE/scan.state"
    scan_note="$scan_note - Latest attempt: $scan_status ($scan_timestamp) - $scan_details"
  fi
  chart_data=""
  if [ -s "$HISTORY" ]; then
    chart_data=$(/usr/bin/awk -F '\t' 'BEGIN{sep=""} $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ && NR % 10 == 1 {printf "%s[%s,%.3f]",sep,$1,$2/1048576; sep=","}' "$HISTORY")
  fi
  case "$SEVERITY" in HEALTHY) color='good' ;; WARNING) color='warn' ;; *) color='bad' ;; esac
  local tmp="$DASH.tmp.$$"
  {
  cat <<HTML
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="60"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Disk Sentinel - Mission Control</title>
<style>
:root{color-scheme:dark;--bg:#090e18;--panel:#121b2b;--border:#25334a;--text:#edf3ff;--muted:#9aabc5;--accent:#63b4ff;--green:#4cdfa3;--yellow:#ffd26d;--red:#ff707f}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 85% -15%,#173152 0,transparent 42%),var(--bg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--text)}main{max-width:1250px;margin:0 auto;padding:32px 24px 60px}.head{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}.eyebrow{font-size:11px;letter-spacing:2.5px;font-weight:800;color:#75b9ff}h1{margin:4px 0;font-size:30px;letter-spacing:-.8px}.muted{color:var(--muted)}.live{border:1px solid var(--border);padding:9px 14px;border-radius:30px;font-size:12px}.dot{display:inline-block;width:8px;height:8px;background:var(--green);border-radius:50%;box-shadow:0 0 11px var(--green);margin-right:8px}.top{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-top:26px}.card,.panel{background:linear-gradient(150deg,#172239,#111927);border:1px solid var(--border);border-radius:16px;padding:23px}.metric{font-size:34px;letter-spacing:-1.2px;font-weight:760;margin:7px 0}.label{font-size:12px;text-transform:uppercase;letter-spacing:1.3px;color:var(--muted)}.hint{font-size:12px;color:var(--muted)}.good{color:var(--green)}.warn{color:var(--yellow)}.bad{color:var(--red)}.columns{display:grid;grid-template-columns:1.55fr 1fr;gap:16px;margin-top:17px}.panel h2{font-size:17px;margin:0 0 5px}.section-note{font-size:12px;color:var(--muted);margin:0 0 17px}.graph{width:100%;height:205px;display:block}.bar{height:9px;background:#253750;border-radius:20px;margin:20px 0 8px;overflow:hidden}.bar span{display:block;height:100%;background:linear-gradient(90deg,#3b8cf7,#f4ae54);border-radius:20px}.candidate{display:flex;justify-content:space-between;border-bottom:1px solid #27364b;padding:15px 0;gap:16px}.candidate:last-child{border:0}.candidate p{margin:3px 0 0;font-size:12px;color:var(--muted)}.right{min-width:90px;text-align:right;display:flex;flex-direction:column;align-items:flex-end}.risk{font-size:10px;margin-top:4px;border:1px solid #826d39;border-radius:6px;padding:1px 6px;color:#ffce71}.risk.protected{border-color:#754b65;color:#ffacbe}.guidance{margin-top:17px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.guide{padding:17px;border-radius:12px;background:#121b2b;border:1px solid var(--border);font-size:13px}.guide strong{display:block;margin-bottom:5px}.guide p{color:var(--muted);margin:0}code{background:#19263a;color:#b9dbff;padding:2px 6px;border-radius:5px;font-size:12px;word-break:break-word}.actions{display:flex;flex-wrap:wrap;gap:10px;margin:13px 0}.action{background:#223956;color:#e5f4ff;border:1px solid #3c6388;border-radius:9px;padding:10px 13px;cursor:pointer;font-weight:650;font-size:12px}.action:active{transform:scale(.98)}footer{font-size:12px;color:var(--muted);padding:20px 0}.pill{display:inline-block;font-size:11px;padding:4px 9px;border-radius:8px;border:1px solid var(--border)}@media(max-width:850px){.columns{grid-template-columns:1fr}.top{grid-template-columns:1fr 1fr}.guidance{grid-template-columns:1fr}}@media(max-width:540px){.top{grid-template-columns:1fr}h1{font-size:24px}main{padding:20px 14px}.metric{font-size:28px}}
</style></head><body><main>
<div class="head"><div><div class="eyebrow">DISK SENTINEL / LOCAL ESTATE</div><h1>Storage mission control</h1><div class="muted">Capacity, growth and protected remediation - local-only</div></div><div class="live" id="heartbeat" data-epoch="$now"><span class="dot" id="pulse"></span> Updated $(escape_html "$now_human")</div></div>
<div class="top"><div class="card"><div class="label">Available capacity</div><div class="metric">$free_gib <small style="font-size:16px">GiB</small></div><div class="hint">Volume capacity: $total_gib GiB</div></div><div class="card"><div class="label">Disk-pressure state</div><div class="metric $color" style="font-size:27px">$SEVERITY</div><div class="hint">Mode: $MODE - $(escape_html "$(mode_policy "$MODE")")</div></div><div class="card"><div class="label">Forecast to depletion</div><div class="metric">$ETA_HOURS <small style="font-size:16px">hours</small></div><div class="hint">Trend-based estimate, not a guarantee</div></div></div>
<div class="columns"><section class="panel"><h2>Capacity trajectory</h2><p class="section-note">Previous seven days of samples - 60-second monitoring cadence</p><svg class="graph" id="graph" role="img" aria-label="Recent available disk space chart"><text x="20" y="40" fill="#9aabc5">Collecting observations...</text></svg><div class="bar"><span style="width:$used_pct%"></span></div><div class="hint">$used_pct% of reported capacity in use - $(escape_html "$trend_text")</div></section><section class="panel"><h2>Safety controls</h2><p class="section-note">Hard restrictions - mission-critical default</p><div class="candidate"><div><strong>Third-party deletion</strong><p>Not allowed without independent approval</p></div><span class="risk protected">Protected</span></div><div class="candidate"><div><strong>Agents, builds and source</strong><p>Never touched by unattended maintenance</p></div><span class="risk protected">Protected</span></div><div class="candidate"><div><strong>Emergency write reserve</strong><p>$(escape_html "$reserve_state")</p></div><span class="risk caution">Managed</span></div><div class="candidate"><div><strong>Snapshot safeguards</strong><p>No Time Machine or APFS snapshot deletion</p></div><span class="risk protected">Protected</span></div></section></div>
<div class="columns"><section class="panel"><h2>Storage opportunities</h2><p class="section-note">$(escape_html "$scan_note") - Sizes overlap where one folder contains another; do not add totals.</p>
HTML
  inventory_rows
  cat <<HTML
</section><section class="panel"><h2>Operator actions</h2><p class="section-note">Observe first. Every cleanup remains supervised.</p><div class="actions"><button class="action" onclick="copyCmd('disk-sentinel scan')">Copy scan command</button><button class="action" onclick="copyCmd('disk-sentinel review')">Copy review command</button><button class="action" onclick="copyCmd('disk-sentinel status')">Copy status command</button></div><p class="muted">Paste the copied command into Terminal. The dashboard cannot perform destructive actions.</p><div style="margin-top:20px"><strong>Self-protection</strong><p class="muted">Own diagnostics older than 14 days are pruned automatically. Sample history is bounded. No Git repositories, databases, Docker volumes, AI sessions, npm caches or Xcode build products are deleted.</p></div></section></div>
<div class="guidance"><div class="guide"><strong>01 - Detect pressure</strong><p>Track free space, severity transitions and growth rates; notify before exhaustion.</p></div><div class="guide"><strong>02 - Attribute growth</strong><p>Read-only inventory of high-probability development caches with low scheduling priority.</p></div><div class="guide"><strong>03 - Authorise recovery</strong><p>Explain reclaim options and blockers. Never substitute size for proof of safe deletion.</p></div></div>
<footer>Disk Sentinel - User-session launchd - Browser refreshes every minute - Monitoring pauses while the Mac sleeps or is powered off.</footer>
<script>
const lastUpdate=Number(document.getElementById('heartbeat').dataset.epoch);
if(Date.now()/1000-lastUpdate>180){document.getElementById('heartbeat').textContent='MONITOR STALE - last update: '+new Date(lastUpdate*1000).toLocaleString();document.getElementById('heartbeat').style.color='#ff707f';}
const history=[$chart_data];
const svg=document.getElementById('graph');
if(history.length>=2){
  const w=760,h=205,p=24,ts=history.map(x=>x[0]),ys=history.map(x=>x[1]);
  let lo=Math.min(...ys),hi=Math.max(...ys);if(hi-lo<1){lo=Math.max(0,lo-.6);hi+=.6;}
  const x=t=>p+(t-Math.min(...ts))/(Math.max(...ts)-Math.min(...ts)||1)*(w-p*2);
  const y=v=>h-p-(v-lo)/(hi-lo)*(h-p*2);
  let points=history.map(([t,v])=>x(t).toFixed(2)+','+y(v).toFixed(2)).join(' ');
  svg.setAttribute('viewBox','0 0 '+w+' '+h);
  svg.innerHTML='<line x1="24" y1="181" x2="736" y2="181" stroke="#364860"/>'+
    '<line x1="24" y1="24" x2="736" y2="24" stroke="#364860"/>'+
    '<polyline fill="none" stroke="#63b4ff" stroke-width="3" vector-effect="non-scaling-stroke" points="'+points+'"/>'+
    '<text x="28" y="19" fill="#9aabc5" font-size="14">'+hi.toFixed(1)+' GiB</text>'+
    '<text x="28" y="199" fill="#9aabc5" font-size="14">'+lo.toFixed(1)+' GiB</text>';
}
function copyCmd(s){if(navigator.clipboard?.writeText){navigator.clipboard.writeText(s).then(()=>alert('Copied: '+s)).catch(()=>prompt('Copy this command:',s))}else{prompt('Copy this command:',s)}}
</script></main></body></html>
HTML
  } > "$tmp" 2>/dev/null && /bin/mv -f "$tmp" "$DASH" || { /bin/rm -f "$tmp" 2>/dev/null || true; echo 'WARNING: dashboard could not be written (disk may be full)' >&2; return 1; }
}

tick() {
  local lock="$STATE/tick.lock" prev="" now
  lock_acquire "$lock" || return 0
  trap "lock_release '$lock'" EXIT INT TERM
  get_space || { notify 'Could not measure home-volume capacity'; echo 'BLOCKED: disk telemetry unavailable' >&2; return 1; }
  now=$(/bin/date +%s)
  find_trend "$now" "$AVAILABLE_K"
  metric_status
  MODE=$(storage_mode "$AVAILABLE_K")
  printf '%s\n' "$MODE" > "$STATE/mode" 2>/dev/null || true
  maybe_capture "$now"
  reserve_maintain
  prev=$(cat "$STATE/last_severity" 2>/dev/null || true)
  if [ "$SEVERITY" != "$prev" ]; then
    [ "$SEVERITY" != HEALTHY ] && notify "Disk $SEVERITY: $(bytes_gib "$AVAILABLE_K") GiB available"
    printf '%s\n' "$SEVERITY" > "$STATE/last_severity.tmp" 2>/dev/null && /bin/mv -f "$STATE/last_severity.tmp" "$STATE/last_severity" || true
  fi
  printf '%s\t%s\n' "$now" "$AVAILABLE_K" >> "$HISTORY" 2>/dev/null || true
  managed_gc
  printf '%s|%s|%s|%s|%s\n' "$now" "$TOTAL_K" "$AVAILABLE_K" "$SEVERITY" "$RATE_KPH" > "$STATUS.tmp" 2>/dev/null && /bin/mv -f "$STATUS.tmp" "$STATUS" || true
  render_dashboard
}

# Read-only inventory with bounded execution and explicit retryable outcomes.
# A postponed scan is never reported as a successful inventory.
scan_state_write() {
  local state="$1" detail="$2" now
  now=$(/bin/date '+%Y-%m-%d %H:%M:%S')
  printf '%s|%s|%s\n' "$now" "$state" "$detail" > "$STATE/scan.state.tmp.$$" 2>/dev/null && \
    /bin/mv -f "$STATE/scan.state.tmp.$$" "$STATE/scan.state" 2>/dev/null || true
}

# du is read-only but can still consume I/O; cap each traversal and run at low CPU priority.
# No process other than the du launched by THIS invocation is ever signalled.
bounded_du() {
  local path="$1" output="$2" limit="${3:-12}" pid elapsed=0 rc=0
  /usr/bin/nice -n 18 /usr/bin/du -skx "$path" > "$output" 2>/dev/null &
  pid=$!
  SCAN_DU_PID="$pid"
  while /bin/kill -0 "$pid" 2>/dev/null; do
    if [ "$elapsed" -ge "$limit" ]; then
      /bin/kill -TERM "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      SCAN_DU_PID=""
      return 124
    fi
    /bin/sleep 1
    elapsed=$((elapsed+1))
  done
  wait "$pid" || rc=$?
  SCAN_DU_PID=""
  return "$rc"
}

scan() {
  local mode="${2:-}" now last_success=0
  now=$(/bin/date +%s)
  if [ "$mode" != '--force' ] && ! optional_allowed; then
    scan_state_write DEFERRED 'Storage pressure: optional inventory suspended by the control plane'
    echo 'DEFERRED: storage pressure suspends the optional inventory. This is NOT a completed scan.'
    return 75
  fi
  if [ "$mode" = '--auto' ] && [ -r "$STATE/scan.completed.epoch" ]; then
    read -r last_success < "$STATE/scan.completed.epoch" || true
    case "$last_success" in ''|*[!0-9]*) last_success=0 ;; esac
    if [ $((now-last_success)) -lt 86400 ] && [ "$now" -ge "$last_success" ]; then
      return 0
    fi
  fi
  # Avoid contention with in-flight builds. Automatically retry 30 minutes later.
  if [ "$mode" != '--force' ] && [ -x /usr/sbin/sysctl ]; then
    local cores load1 busy
    cores=$(/usr/sbin/sysctl -n hw.logicalcpu 2>/dev/null || echo 1)
    load1=$(/usr/sbin/sysctl -n vm.loadavg 2>/dev/null | /usr/bin/awk '{gsub(/[{}]/, "");print $1}')
    busy=$(/usr/bin/awk -v l="$load1" -v c="$cores" 'BEGIN {if(c>0 && l>c*0.8) print 1; else print 0}')
    if [ "$busy" = 1 ]; then
      scan_state_write DEFERRED 'System busy; retry scheduled in 30 minutes'
      echo 'DEFERRED: system busy. This is NOT a completed scan; automatic retry is scheduled.'
      return 75
    fi
  fi

  local lock="$STATE/scan.lock" entries="$STATE/inventory.unsorted.$$" tmp="$STATE/inventory.tmp.$$"
  lock_acquire "$lock" || { scan_state_write DEFERRED 'Another inventory is running'; echo 'DEFERRED: scan already active'; return 75; }
  SCAN_DU_PID=""
  SCAN_LOCK="$lock"; SCAN_ENTRIES="$entries"; SCAN_TMP="$tmp"; SCAN_DU_TMP="$STATE/du.tmp.$$"
  trap 'if [ -n "${SCAN_DU_PID:-}" ]; then /bin/kill -TERM "$SCAN_DU_PID" 2>/dev/null || true; fi; lock_release "$SCAN_LOCK"; /bin/rm -f "$SCAN_ENTRIES" "$SCAN_TMP" "$SCAN_DU_TMP" 2>/dev/null || true' EXIT INT TERM
  : > "$entries" || { scan_state_write FAILED 'Cannot write inventory (disk full or permissions)'; echo 'BLOCKED: insufficient disk space for scan inventory' >&2; return 1; }
  local label path risk note kb measured=0 skipped=0 candidates=0 start_ts run_sec
  start_ts=$(/bin/date +%s)
  while IFS='|' read -r label path risk note; do
    [ -d "$path" ] || continue
    candidates=$((candidates+1))
    run_sec=$(( $(/bin/date +%s) - start_ts ))
    if [ "$run_sec" -ge 90 ]; then skipped=$((skipped+1)); continue; fi
    if bounded_du "$path" "$STATE/du.tmp.$$" 12; then
      kb=$(/usr/bin/awk 'NR==1 {print $1}' "$STATE/du.tmp.$$")
      case "$kb" in ''|*[!0-9]*) skipped=$((skipped+1)); continue ;; esac
      printf '%s|%s|%s|%s\n' "$label" "$kb" "$risk" "$note" >> "$entries" || { scan_state_write FAILED 'Disk full while recording inventory'; return 1; }
      measured=$((measured+1))
    else
      skipped=$((skipped+1))
    fi
    /bin/rm -f "$STATE/du.tmp.$$" 2>/dev/null || true
  done <<EOF_CANDIDATES
Node/npm downloaded packages|$HOME/.npm/_cacache|Review|Reclaim only after confirming no package operation is active
nvm downloaded archives|$HOME/.nvm/.cache|Review|May include in-progress Node downloads or compiles
Homebrew cache|$HOME/Library/Caches/Homebrew|Review|Use brew cleanup preview first; avoid concurrent brew jobs
Python pip cache|$HOME/Library/Caches/pip|Review|Avoid in-flight package installation
Python alternative cache|$HOME/.cache/pip|Review|Avoid in-flight package installation
Cargo crate archives|$HOME/.cargo/registry/cache|Review|Verify no cargo task and retained offline requirements
Gradle caches|$HOME/.gradle/caches|Review|May be in use by running Gradle builds
Xcode DerivedData|$HOME/Library/Developer/Xcode/DerivedData|Protected|Active builds and indexing may use these files
Apple simulator data|$HOME/Library/Developer/CoreSimulator|Protected|Includes persistent simulator devices and app data
Docker VM storage|$HOME/Library/Containers/com.docker.docker/Data/vms|Protected|Never delete Docker.raw or volumes; inspect through Docker
General user caches|$HOME/Library/Caches|Protected|Mixed ownership; never bulk-delete blindly
CLI and agent caches|$HOME/.cache|Protected|Includes active models, sessions and build data
EOF_CANDIDATES
  /usr/bin/sort -t '|' -k2,2nr "$entries" > "$tmp" || { scan_state_write FAILED 'Unable to sort inventory'; return 1; }
  /bin/mv -f "$tmp" "$INVENTORY" || { scan_state_write FAILED 'Unable to publish inventory'; return 1; }
  if [ "$skipped" -gt 0 ]; then
    scan_state_write PARTIAL "Measured $measured of $candidates available locations; $skipped timed out or deferred; retry pending"
    echo "PARTIAL INVENTORY: measured $measured locations, $skipped incomplete; will retry automatically."
  else
    scan_state_write COMPLETE "Measured $measured locations"
    /bin/date '+%Y-%m-%d %H:%M:%S' > "$STATE/scan.completed" 2>/dev/null || true
    /bin/date '+%s' > "$STATE/scan.completed.epoch" 2>/dev/null || true
    echo "COMPLETE: measured $measured locations."
  fi
  /usr/bin/head -n 10 "$INVENTORY" | /usr/bin/awk -F '|' '{printf "%-32s %8.1f GiB  %s\n",$1,$2/1048576,$3}'
  /bin/bash "$APP/sentinel.sh" tick >/dev/null 2>&1 || true
  [ "$skipped" -eq 0 ] || return 75
}

review() {
  echo 'DISK SENTINEL / REMEDIATION POLICY'
  echo 'No third-party files are deleted automatically. Candidate sizes are advisory.'
  echo 'First: check active build, install, backup, database and agent work.'
  echo
  [ -s "$STATE/scan.state" ] && echo "Latest attempt: $(cat "$STATE/scan.state")"
  [ -s "$INVENTORY" ] && /usr/bin/head -n 12 "$INVENTORY" | /usr/bin/awk -F '|' '{printf "%-32s %8.1f GiB  %s\n",$1,$2/1048576,$3}' || echo 'No inventory yet: automatic retry will run every 30 minutes' 
  cat <<'EOM'

APPROVED REVIEW COMMANDS (READ-ONLY):
  df -h "$HOME"                             # Report home volume space
  docker system df -v                       # Docker usage (if installed)
  brew cleanup -n                           # Homebrew dry-run (if installed)
  xcrun simctl list devices                 # Simulator inventory (if installed)
  tmutil listlocalsnapshots /               # Snapshot inventory, do not force remove

BEFORE APPROVING ANY CLEANUP:
  - Verify affected service and build processes have finished.
  - Confirm artifact can be reconstructed or is independently backed up.
  - Never delete Docker.raw, volumes, databases, repos, archives or dSYMs blindly.
  - Prefer owner-supported cleanup commands; measure freed disk capacity afterwards.
  - Renaming into Trash on the same APFS volume does NOT free that capacity.
EOM
}

status() {
  if [ -s "$STATUS" ]; then
    local ts total avail sev rate
    IFS='|' read -r ts total avail sev rate < "$STATUS"
    printf 'Current cached status: %s\nFree: %s GiB / %s GiB | Pressure: %s\n' "$(/bin/date -r "$ts" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "$ts")" "$(bytes_gib "$avail")" "$(bytes_gib "$total")" "$sev"
  else echo 'No samples yet; run: disk-sentinel tick'; fi
  local cur_mode cur_avail
  cur_avail=$(current_avail_k)
  cur_mode=$(storage_mode "${cur_avail:-0}")
  printf 'Mode: %s - %s\n' "$cur_mode" "$(mode_policy "$cur_mode")"
  echo "Dashboard: $DASH"
  if [ -s "$STATE/scan.state" ]; then
    printf 'Investigation: %s\n' "$(cat "$STATE/scan.state")"
  else
    echo 'Investigation: NEVER RUN - no scan attempt recorded'
  fi
  [ -s "$STATE/scan.completed" ] && echo "Last completed inventory: $(cat "$STATE/scan.completed")"
  if command -v launchctl >/dev/null 2>&1; then
    /bin/launchctl print "gui/$(/usr/bin/id -u)/$LABEL" >/dev/null 2>&1 && echo 'Monitor: registered with launchd' || echo 'Monitor: not running or outside active GUI session'
  fi
}

# Split --force from the arguments an investigation understands: the sub-scripts reject
# unknown flags, and the control plane must be able to override a refusal explicitly.
OPT_ARGS=()
OPT_FORCE=0
optional_args() {
  local a
  OPT_ARGS=(); OPT_FORCE=0
  for a in "$@"; do
    case "$a" in --force) OPT_FORCE=1 ;; *) OPT_ARGS+=("$a") ;; esac
  done
}

refuse_unless_forced() {
  [ "${2:-0}" -eq 1 ] && return 0
  optional_allowed && return 0
  refuse_optional "$1"
}

policy_load
policy_load_capture

case "${1:-}" in
  tick) tick ;;
  scan) scan "$@" ;;
  review) review ;;
  status) status ;;
  open) [ -f "$DASH" ] && /usr/bin/open "$DASH" || { tick && /usr/bin/open "$DASH"; } ;;
  admit)
    # The one-line capacity gate an estate job calls before starting discretionary work.
    policy_load
    admit_avail=$(current_avail_k)
    admit_mode=$(storage_mode "$admit_avail")
    case "$admit_mode" in
      NORMAL|WARNING) printf 'ADMIT: %s, %s GiB free (reserve %s GiB)\n' "$admit_mode" "$(bytes_gib "$admit_avail")" "$DISK_SENTINEL_RESERVE_GIB"; exit 0 ;;
      *) printf 'REFUSED: %s, %s GiB free against a %s GiB reserve. Discretionary work must wait.\n' "$admit_mode" "$(bytes_gib "${admit_avail:-0}")" "$DISK_SENTINEL_RESERVE_GIB"; exit 75 ;;
    esac ;;
  verify)
    # A cleanup that ran is not a cleanup that recovered anything (founder, 2026-11-05):
    # deleting a file that is still held open frees the directory entry, not the blocks, and a
    # system cache can be rebuilt before the next sample. This measures physical free space
    # before and after the command and refuses to call it recovery unless the space came back.
    shift
    [ "${1:-}" = "--" ] && shift
    [ $# -gt 0 ] || { echo 'usage: disk-sentinel verify -- <command...>' >&2; exit 2; }
    verify_before=$(current_avail_k)
    verify_t0=$(/bin/date +%s)
    "$@" ; verify_rc=$?
    verify_after=$(current_avail_k)
    verify_dt=$(( $(/bin/date +%s) - verify_t0 ))
    case "$verify_before$verify_after" in *[!0-9]*|'') echo 'verify: BLIND - free space could not be measured before and after'; exit "$verify_rc" ;; esac
    verify_delta=$(( (verify_after - verify_before) / 1024 ))
    if [ "$verify_delta" -gt 0 ]; then verify_verdict=RECLAIMED; else verify_verdict=NOT_RECLAIMED; fi
    printf 'verify: %s  rc=%s  free %.2f -> %.2f GiB  delta %+d MiB in %ss\n' \
      "$verify_verdict" "$verify_rc" "$(bytes_gib "$verify_before")" "$(bytes_gib "$verify_after")" "$verify_delta" "$verify_dt"
    [ "$verify_verdict" = RECLAIMED ] || echo '  The command finished; the capacity did not return. Do not count it as recovered.'
    /bin/mkdir -p "$STATE/receipts" 2>/dev/null || true
    printf '%s\t%s\t%s\t%s\t%s\n' "$(/bin/date '+%Y-%m-%dT%H:%M:%S')" "$verify_before" "$verify_after" "$verify_delta" "$verify_verdict" \
      >> "$STATE/receipts/recovery.tsv" 2>/dev/null || true
    exit "$verify_rc" ;;
  probe)
    # Metadata latency, not size (founder, 2026-11-05): "the directory is slow" and "the
    # directory is large" are different findings, and a du timeout cannot tell them apart.
    # One readdir per directory, bounded, reporting entries/ms/verdict - no recursion, no I/O
    # beyond the directory itself.
    shift
    /usr/bin/python3 - "${@:-$HOME/Library/Mail|$HOME/Library/CloudStorage|$HOME/Pictures/Photos Library.photoslibrary|$HOME/Library/Application Support/FileProvider|$HOME/Library/Containers|$HOME/.estate/backups|$HOME/.cache}" <<'PROBE'
import os, signal, sys, time

class Timeout(Exception):
    pass

def _alarm(signum, frame):
    raise Timeout()

signal.signal(signal.SIGALRM, _alarm)

def probe(path, budget=5):
    if not os.path.isdir(path):
        return "ABSENT", 0, 0.0
    signal.alarm(budget)
    t0 = time.time()
    try:
        n = 0
        with os.scandir(path) as it:
            for _ in it:
                n += 1
        ms = (time.time() - t0) * 1000
        signal.alarm(0)
        if ms > 2000:
            return "SLOW", n, ms
        return "OK", n, ms
    except Timeout:
        return "BLOCKED", 0, (time.time() - t0) * 1000
    except PermissionError:
        signal.alarm(0)
        return "DENIED", 0, 0.0
    except OSError as e:
        signal.alarm(0)
        return "ERROR:%s" % e.errno, 0, 0.0

paths = [a for a in sys.argv[1:] if a]
if len(paths) == 1 and "|" in paths[0]:
    paths = [p for p in paths[0].split("|") if p]
print("%-10s %9s %10s  %s" % ("VERDICT", "ENTRIES", "READDIR_MS", "PATH"))
for p in paths:
    v, n, ms = probe(os.path.expanduser(p))
    print("%-10s %9d %10.1f  %s" % (v, n, ms, p))
PROBE
    ;;
  policy)
    policy_load
    printf 'Reserve (discretionary work refused below): %s GiB\n' "$DISK_SENTINEL_RESERVE_GIB"
    printf 'Warning line: %s GiB\n' "$DISK_SENTINEL_WARNING_GIB"
    printf 'Effective now: %s - %s\n' "$(storage_mode "$(current_avail_k)")" "$(mode_policy "$(storage_mode "$(current_avail_k)")")"
    printf 'Override file: %s (RESERVE_GIB=.., WARNING_GIB=..)\n' "$STATE/policy.conf" ;;

  # The forensic investigation is part of this tool, not a second download: one disk-management
  # surface, one install, one place where the safety policy is stated. The script is read-only,
  # time-bounded and is installed next to this one.
  forensics)
    if [ ! -x "$APP/forensics.sh" ]; then echo 'BLOCKED: forensics.sh is not installed; reinstall Disk Sentinel' >&2; exit 2; fi
    shift
    optional_args "$@"
    refuse_unless_forced forensics "$OPT_FORCE" || exit $?
    [ ${#OPT_ARGS[@]} -eq 0 ] && OPT_ARGS=(--deep)
    /bin/bash "$APP/forensics.sh" "${OPT_ARGS[@]}" ;;
  # One-pass attribution of the whole Data volume. Different question from "forensics":
  # that one probes named suspects; this one walks every entry once and buckets the blocks
  # by top-level owner, so "what is the 96 GB?" has an answer even when no suspect list hits.
  elephant)
    if [ ! -x "$APP/elephant.sh" ]; then echo 'BLOCKED: elephant.sh is not installed; reinstall Disk Sentinel' >&2; exit 2; fi
    # Single flight (2026-11-05). Two walks were started by hand and both stalled at 0% CPU
    # while writing the same report file; each truncates the other's offsets, so the report
    # froze mid-progress. A whole-volume walk is exactly the thing that must not be doubled.
    elephant_lock="$STATE/elephant.lock"
    lock_acquire "$elephant_lock" || { echo 'BLOCKED: another elephant walk is already running; no duplicate I/O started.' >&2; exit 75; }
    trap 'lock_release "$elephant_lock"' EXIT INT TERM
    shift
    optional_args "$@"
    refuse_unless_forced elephant "$OPT_FORCE" || exit $?
    [ ${#OPT_ARGS[@]} -eq 0 ] && OPT_ARGS=(--deep)
    /bin/bash "$APP/elephant.sh" "${OPT_ARGS[@]}" ;;
  *) echo 'Usage: disk-sentinel {tick|scan|review|status|open|admit|probe|verify|policy|forensics [--deep|--quick]|elephant [--deep|--quick]}' >&2; exit 2 ;;
esac
