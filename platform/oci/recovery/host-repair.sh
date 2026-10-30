#!/usr/bin/env bash
# Diagnose and repair the recovery host's router and Cloudflare Tunnel (#7387, 2026-10-29).
#
# WHY. llm-recovery.mumchimp.com answered HTTP 530 "error code: 1033" for hours. Cloudflare's own
# documentation says 1033 means "your tunnel is not connected to Cloudflare's network because
# Cloudflare's network cannot find a healthy cloudflared instance to receive the traffic". The
# tunnel, the DNS record, the vault entry and the config bundle were all proven good from the
# outside; the missing thing was a cloudflared connector on the host. The host has no SSH door,
# so this runs through OCI Run Command, which executes as `ocarun` (uid 988) -- so the script
# elevates itself with the passwordless sudo rule cloud-init writes for exactly this reason.
#
# WHAT IT DOES. It prints what the host is actually doing, repairs the three ways the tunnel can
# fail to start, and proves the connector is up. It is idempotent: running it twice changes
# nothing the second time.
#
# SECRETS. It never prints a secret. The env file is described by existence, size and key NAMES
# only; journal lines are passed through a redactor that replaces anything that looks like a key
# with REDACTED. The tunnel token never appears in output.
#
# EXIT. 0 when the connector is established and the router answers on loopback. 1 when the host is
# repaired as far as it can be and the connector still is not up -- a measured failure, not a
# narration. 2 when the host cannot be read at all (BLIND).

set -uo pipefail

say() { printf '%s\n' "$*"; }
ok() { printf 'ok      host-repair  %s\n' "$*"; }
bad() { printf 'FAIL    host-repair  %s\n' "$*" >&2; }
blind() { printf 'BLIND   host-repair  %s\n' "$*" >&2; exit 2; }

# ---------------------------------------------------------------- elevate

# OCI Run Command executes this script as `ocarun` (uid 988), NOT as root -- measured on
# 2026-10-30. Everything below needs root: podman, systemctl, mounting a volume, and the
# instance-principal OCI calls. The host's cloud-init writes
# /etc/sudoers.d/101-oracle-cloud-agent-run-command (`ocarun ALL=(ALL) NOPASSWD:ALL`) for
# exactly this case, so the script elevates itself and carries on as root. Before this, the
# script refused to run and the door was dead (#7525).
if [ "$(id -u)" != "0" ]; then
  if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    printf 'state  host-repair  not root; re-executing as root through sudo -n\n'
    exec sudo -n bash "$0" "$@"
  fi
  blind "not root: Run Command must execute as root and no passwordless sudo is available"
fi

# ---------------------------------------------------------------- diagnose

say "== host-repair: diagnose =="

# cloud-init: did the boot steps finish? A host still installing podman has no tunnel.
if [ -f /var/lib/cloud/instance/boot-finished ]; then
  ok "cloud-init boot-finished"
elif [ -f /var/log/cloud-init-output.log ]; then
  say "state  cloud-init  boot-finished: absent (boot steps may still be running)"
else
  say "state  cloud-init  boot-finished: absent and no cloud-init log"
fi

for unit in estate-router.service estate-tunnel.service estate-router-refresh.timer; do
  if systemctl list-unit-files "$unit" >/dev/null 2>&1 && systemctl cat "$unit" >/dev/null 2>&1; then
    state=$(systemctl is-active "$unit" 2>/dev/null || echo unknown)
    enabled=$(systemctl is-enabled "$unit" 2>/dev/null || echo unknown)
    say "state  $unit  active=$state enabled=$enabled"
  else
    say "state  $unit  unit: absent"
  fi
done

# /etc/estate: existence and size only. Never contents.
for f in /etc/estate/router.env /etc/estate/bundle.tgz /etc/estate/router-fetch; do
  if [ -e "$f" ]; then
    say "state  $f  present bytes=$(stat -c %s "$f" 2>/dev/null || echo 0)"
  else
    say "state  $f  ABSENT"
  fi
done

# The env file's KEY NAMES only -- the values are secrets and are never printed.
if [ -f /etc/estate/router.env ]; then
  keys=$(sed -n 's/^\([A-Za-z0-9_]*\)=.*/\1/p' /etc/estate/router.env | sort | tr '\n' ' ')
  say "state  /etc/estate/router.env  keys: ${keys:-<none>}"
  if grep -q '^TUNNEL_TOKEN=..' /etc/estate/router.env 2>/dev/null; then
    ok "TUNNEL_TOKEN is present and non-empty"
  else
    bad "TUNNEL_TOKEN is missing or empty in /etc/estate/router.env"
  fi
fi

# Podman: are the containers running, and do the images exist locally?
if command -v podman >/dev/null 2>&1; then
  ok "podman is installed"
  for c in estate-router estate-tunnel; do
    if podman ps --format '{{.Names}}' 2>/dev/null | grep -qx "$c"; then
      ok "container $c is running"
    else
      say "state  container $c  NOT running"
    fi
  done
  for img in ghcr.io/berriai/litellm:v1.98.0 docker.io/cloudflare/cloudflared:2024.12.2; do
    if podman images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -qx "$img"; then
      ok "image $img is present locally"
    else
      say "state  image $img  absent locally"
    fi
  done
else
  bad "podman is not installed: the boot step 'dnf install -y podman' has not finished"
fi

# Redact anything that looks like a credential before printing a journal line.
redact() {
  sed -E \
    -e 's/(TUNNEL_TOKEN|API_KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIALS?)([=:][^[:space:]]*)/\1=REDACTED/gI' \
    -e 's/(ey[A-Za-z0-9_-]{8})[A-Za-z0-9_.-]+/\1REDACTED/g'
}

for unit in estate-tunnel.service estate-router.service; do
  if systemctl cat "$unit" >/dev/null 2>&1; then
    say "--- journal $unit (last 15, redacted) ---"
    journalctl -u "$unit" --no-pager -n 15 2>/dev/null | redact | sed 's/^/  /'
  fi
done

# ---------------------------------------------------------------- repair

say ""
say "== host-repair: repair =="

# Repair 1: the env file the tunnel needs. estate-tunnel.service has no ExecStartPre=router-fetch,
# so if the vault entry had not arrived by the time the unit started, podman --env-file failed and
# the unit crash-looped forever. Fetch it now.
if [ ! -f /etc/estate/router.env ] || ! grep -q '^TUNNEL_TOKEN=..' /etc/estate/router.env 2>/dev/null; then
  if [ -x /etc/estate/router-fetch ]; then
    say "state  /etc/estate/router.env  fetching from the vault (router-fetch)"
    if /etc/estate/router-fetch >/tmp/router-fetch.out 2>&1; then
      ok "router-fetch succeeded"
    else
      bad "router-fetch failed: $(redact </tmp/router-fetch.out | tail -3 | tr '\n' ' ')"
    fi
  else
    bad "/etc/estate/router-fetch is absent: cannot fetch the vault entry"
  fi
else
  ok "/etc/estate/router.env already carries a tunnel token"
fi

# Repair 2: the ordering and the missing credential fetch. The RUNNING host still carries the
# unit that was installed at first boot -- the cloud-init change only reaches a new boot -- so
# this drop-in carries both fixes to the live unit:
#   * After=estate-router.service  -- a router in a restart loop keeps the tunnel from starting
#     at all. The tunnel only needs the router to be reachable, not to be started first.
#   * ExecStartPre=/etc/estate/router-fetch -- the unit had none, so if the vault entry had not
#     arrived by the time the unit started, `podman --env-file` failed and the unit crash-looped
#     silently, forever.
#
# A DROP-IN, not `systemctl edit --full`: --full REPLACES the unit file, and a heredoc carrying
# only [Unit] would delete the [Service] section -- ExecStart and all -- leaving a unit that
# starts and does nothing. A drop-in adds to the unit; an empty `After=` assignment resets the
# list, and the new After= replaces the inherited one.
if systemctl cat estate-tunnel.service >/dev/null 2>&1; then
  need_dropin=0
  if systemctl show estate-tunnel.service -p After 2>/dev/null | grep -q 'estate-router.service'; then
    say "state  estate-tunnel.service  After= includes estate-router.service"
    need_dropin=1
  else
    ok "estate-tunnel.service does not wait for estate-router.service"
  fi
  if ! systemctl show estate-tunnel.service -p ExecStartPre 2>/dev/null | grep -q 'router-fetch'; then
    say "state  estate-tunnel.service  has no ExecStartPre=router-fetch"
    need_dropin=1
  else
    ok "estate-tunnel.service fetches its credentials before starting"
  fi
  if [ "$need_dropin" = "1" ]; then
    mkdir -p /etc/systemd/system/estate-tunnel.service.d
    cat >/etc/systemd/system/estate-tunnel.service.d/10-no-router-wait.conf <<'EOF'
[Unit]
After=
After=network-online.target
Wants=network-online.target

[Service]
ExecStartPre=
ExecStartPre=/etc/estate/router-fetch
EOF
    systemctl daemon-reload
    if systemctl show estate-tunnel.service -p After 2>/dev/null | grep -q 'estate-router.service'; then
      bad "the drop-in did not take: After= still names estate-router.service"
    else
      ok "estate-tunnel.service no longer waits for estate-router.service"
    fi
    # The unit must still have its ExecStart: a repair that removes it would be a second outage.
    if systemctl show estate-tunnel.service -p ExecStart 2>/dev/null | grep -q 'podman run'; then
      ok "estate-tunnel.service still carries its ExecStart"
    else
      bad "estate-tunnel.service has no ExecStart: the unit would start and do nothing"
    fi
  fi
fi

# Repair 3: the connector itself. Restart both units so the tunnel reads the env file that is
# there NOW. The refresh unit restarts only the router, so the tunnel is restarted here too.
systemctl restart estate-router.service 2>/dev/null || true
systemctl restart estate-tunnel.service 2>/dev/null || true

# Repair 4: the refresh timer must be ENABLED, not merely present. Measured on 2026-10-30: the
# live host carried estate-router-refresh.timer as `active=inactive enabled=static` -- the unit
# file existed, but nothing scheduled it, so the router would never refresh itself from the
# vault again. cloud-init's combined `systemctl enable --now` for three units aborted on the
# first failure and never reached the timer; the cloud-init source is fixed for future boots,
# and this line repairs the live host now.
if systemctl cat estate-router-refresh.timer >/dev/null 2>&1; then
  if systemctl enable --now estate-router-refresh.timer >/dev/null 2>&1; then
    ok "estate-router-refresh.timer is enabled"
  else
    bad "estate-router-refresh.timer could not be enabled"
  fi
  say "state  estate-router-refresh.timer  active=$(systemctl is-active estate-router-refresh.timer 2>/dev/null || echo unknown) enabled=$(systemctl is-enabled estate-router-refresh.timer 2>/dev/null || echo unknown)"
else
  say "state  estate-router-refresh.timer  unit: absent"
fi

# Give the connector a bounded moment to register with Cloudflare.
for _ in $(seq 1 12); do
  if podman ps --format '{{.Names}}' 2>/dev/null | grep -qx estate-tunnel; then
    ok "container estate-tunnel is running"
    break
  fi
  sleep 5
done

# ---------------------------------------------------------------- prove

say ""
say "== host-repair: prove =="

if podman ps --format '{{.Names}}' 2>/dev/null | grep -qx estate-tunnel; then
  ok "estate-tunnel container is up"
else
  bad "estate-tunnel container is still not running"
  journalctl -u estate-tunnel.service --no-pager -n 25 2>/dev/null | redact | sed 's/^/  /'
  exit 1
fi

# cloudflared logs the tunnel's registration; its connector id is not a secret, its token is.
if podman logs estate-tunnel 2>&1 | tail -40 | redact | grep -qi 'Registered tunnel connection'; then
  ok "cloudflared reports a registered tunnel connection"
else
  say "state  cloudflared  no 'Registered tunnel connection' in the last 40 log lines"
  podman logs estate-tunnel 2>&1 | tail -40 | redact | sed 's/^/  /'
fi

# The router answers on loopback: the tunnel's origin is 127.0.0.1:4000.
code=$(curl -sS -m 8 -o /tmp/liveliness.out -w '%{http_code}' \
  http://127.0.0.1:4000/health/liveliness 2>/dev/null || echo 000)
say "state  router  http://127.0.0.1:4000/health/liveliness -> $code"
if [ "$code" = "200" ]; then
  ok "the router answers 200 on loopback"
else
  say "state  router  body: $(head -c 200 /tmp/liveliness.out 2>/dev/null | redact)"
  journalctl -u estate-router.service --no-pager -n 25 2>/dev/null | redact | sed 's/^/  /'
fi

say "host-repair: done"
exit 0
