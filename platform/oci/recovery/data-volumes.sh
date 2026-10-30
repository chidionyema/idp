#!/usr/bin/env bash
# Runs ON the recovery host (via OCI Run Command, .github/workflows/recovery-data.yml), as root.
#
#   data-volumes.sh identify   mount every attached data volume read-only and describe it
#   data-volumes.sh copy       the same, then tar | zstd each one into the host's own bucket,
#                              with a sha256 beside it
#
# The three csi-* volumes are the only copy of the estate's data (no backup was configured, and
# volume backups are refused at the free limit). They are attached read-only by tofu and mounted
# read-only here: nothing in this script can write to them.
set -euo pipefail
MODE="${1:-identify}"

# OCI Run Command executes this script as `ocarun` (uid 988), NOT as root -- measured on
# 2026-10-30. The instance-principal OCI calls and the mounts both need root, and the OCI CLI
# refuses instance-principal auth without it ("This command has to be run with superuser
# privileges"). The host's cloud-init writes
# /etc/sudoers.d/101-oracle-cloud-agent-run-command (`ocarun ALL=(ALL) NOPASSWD:ALL`), so the
# script elevates itself FIRST and only then exports the instance-principal auth, so the root
# re-exec performs the authentication (#7525).
if [ "$(id -u)" != "0" ]; then
  if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    printf 'state  data-volumes  not root; re-executing as root through sudo -n\n'
    exec sudo -n bash "$0" "$@"
  fi
  printf 'BLIND   data-volumes  Run Command must execute as root and no passwordless sudo is available\n' >&2
  exit 2
fi

export OCI_CLI_AUTH=instance_principal SUPPRESS_LABEL_WARNING=True
NS="$(oci os ns get --query data --raw-output)"
BUCKET="${RECOVERY_BUCKET:-estate-router-recovery}"
command -v zstd >/dev/null || dnf install -y zstd >/dev/null

root_dev="$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" | head -1)"
for dev in $(lsblk -dno NAME,TYPE | awk '$2=="disk"{print $1}'); do
  [ "$dev" = "$root_dev" ] && continue
  part="/dev/$dev"; [ -b "/dev/${dev}1" ] && part="/dev/${dev}1"
  mnt="/mnt/recovery/$dev"; mkdir -p "$mnt"
  mountpoint -q "$mnt" || mount -o ro,noload "$part" "$mnt" 2>/dev/null || mount -o ro "$part" "$mnt"
  size="$(du -sm "$mnt" 2>/dev/null | cut -f1)"
  pg="$(find "$mnt" -maxdepth 4 -name PG_VERSION 2>/dev/null | head -1)"
  echo "VOLUME $dev part=$part used_mb=$size postgres=${pg:+$(cat "$pg") at ${pg%/PG_VERSION}}"
  ls -la "$mnt" | head -12 | sed 's/^/  | /'
  if [ "$MODE" = copy ]; then
    obj="volumes/$dev-$(date -u +%Y%m%dT%H%M%SZ).tar.zst"
    # Streamed: the boot disk is 50 GB and a volume is 50 GB, so nothing is staged locally.
    tar -C "$mnt" -cf - . | zstd -T0 -10 -q |
      tee >(sha256sum | cut -d' ' -f1 > "/var/tmp/$dev.sha256") |
      oci os object put -ns "$NS" -bn "$BUCKET" --name "$obj" --file - --force >/dev/null
    sleep 1; sha="$(cat "/var/tmp/$dev.sha256")"
    printf '%s\n' "$sha" | oci os object put -ns "$NS" -bn "$BUCKET" --name "$obj.sha256" --file - --force >/dev/null
    echo "COPIED $dev -> $BUCKET/$obj sha256=$sha"
  fi
done
