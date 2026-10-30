#!/usr/bin/env bash
# The estate database's daily copy, running where the database does not.
#
# idp#7391: the estate's PostgreSQL cluster is gone -- OKE's free trial ended on 2026-10-28 and
# the cluster with it -- but its data survived as logical dumps in Object Storage
# (estate-db-backups/db/2026-09-08/*.sql.gz: 16 databases, PostgreSQL 18.1). A copy service that
# only works while the database is alive is not a copy service, so this one restores the newest
# surviving dump into a PostgreSQL 18 instance, re-dumps it, and publishes it.
#
# The contract is the CronJob's (platform/estate-db/backup/cronjob.yaml), unchanged:
#   * the dump must end with pg_dumpall's own completion marker, or it is not published;
#   * a copy that collapsed against the previous receipt is refused;
#   * estate-db/latest.json is written LAST, so its presence means the copy above it landed.
# bin/idp-estate-db-backup grades that receipt from the backend and prints
#   ok      estate-db-backup  <stamp> (<age> h old), <bytes> bytes
#
# What the CronJob never had to say, and this receipt says out loud: a copy is only as fresh as
# the data it came from. `data_as_of` is the creation time of the dump that was restored, `source`
# is its object name, and `mode` says whether this run re-dumped a running cluster or restored a
# surviving one. A fresh stamp over 2026-09-08 data is a fresh copy of old data, and the receipt
# is where that difference is visible rather than implied.
#
# Subcommands -- each one stands alone, so each one can be tested alone:
#   select-source            print "<name>\t<created>\t<bytes>" for the best surviving dump
#   fetch-source FILE        download the best surviving dump that really carries the estate
#                            database, and write its .source file

#   start-container NAME [CIDFILE]
#                            start PostgreSQL in the copy image and wait until it answers
#   check-extensions       refuse before the restore if the image lacks vector/btree_gin/pg_trgm
#   check-extensions-container CID
#                            the same check, against the PostgreSQL in the container
#   restore FILE             restore FILE into the PostgreSQL named by PG* in the environment
#   restore-container CID FILE   restore FILE inside the running container
#   dump FILE                write a fresh pg_dumpall of that PostgreSQL to FILE
#   dump-container CID FILE     dump inside the running container, then copy it out
#   publish FILE             upload FILE as estate-db/estate-<stamp>.sql.gz, then the receipt
#   run                      fetch-source -> restore -> dump -> publish
#
# Environment:
#   BUCKET               object storage bucket                       (default estate-db-backups)
#   PG_IMAGE             the PostgreSQL image to run                   (default the estate's 18.1 image)
#   PG_DATA_DIR          where initdb writes inside the container      (default /tmp/estate-pgdata)
#   PG_READY_TIMEOUT     seconds to wait for PostgreSQL to answer      (default 180)
#   OCI_OS_NAMESPACE     tenancy namespace                           (default: oci os ns get)
#   RECEIPT_PREFIX       receipt and copy prefix                     (default estate-db)
#   SOURCE_PREFIXES      where a dump to restore may live            (default "estate-db db")
#   ESTATE_DB_NAME       the database the copy has to carry         (default estate)
#   ESTATE_DB_LABEL      the estate's own dump prefix                (default estate-db)
#   MIN_SIZE_RATIO       refuse a copy below this share of the last one (default 0.5)
#   PGHOST PGPORT PGUSER PGPASSWORD   the PostgreSQL to restore into and dump from
#   OCI_CLI_AUTH         passed to the oci CLI when set
set -euo pipefail

BUCKET="${ESTATE_DB_BACKUP_BUCKET:-estate-db-backups}"
PG_IMAGE="${PG_IMAGE:-ghcr.io/chidionyema/postgres-partman:18.1-postgres-partman}"
PG_DATA_DIR="${PG_DATA_DIR:-/tmp/estate-pgdata}"
PG_READY_TIMEOUT="${PG_READY_TIMEOUT:-180}"
RECEIPT_PREFIX="${ESTATE_DB_RECEIPT_PREFIX:-estate-db}"
RECEIPT_NAME="${RECEIPT_PREFIX}/latest.json"
SOURCE_PREFIXES="${ESTATE_DB_SOURCE_PREFIXES:-estate-db db}"
ESTATE_DB_NAME="${ESTATE_DB_NAME:-estate}"
ESTATE_DB_LABEL="${ESTATE_DB_LABEL:-estate-db}"
# How much of a candidate dump is read to recognise its header. The header is at the very top.
VERIFY_HEADER_BYTES="${ESTATE_DB_VERIFY_HEADER_BYTES:-65536}"
REQUIRED_EXTENSIONS="${ESTATE_DB_REQUIRED_EXTENSIONS:-vector btree_gin pg_trgm}"
MIN_SIZE_RATIO="${ESTATE_DB_MIN_SIZE_RATIO:-0.5}"
DUMP_MARKER="PostgreSQL database cluster dump complete"
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

say() { printf '%s\n' "$*"; }
fail() {
	printf 'FAIL    estate-db-backup  %s\n' "$*" >&2
	exit 1
}

oci_cli() {
	if [ -n "${OCI_CLI_AUTH:-}" ]; then
		oci --auth "$OCI_CLI_AUTH" "$@"
	else
		oci "$@"
	fi
}

namespace() {
	if [ -n "${OCI_OS_NAMESPACE:-}" ]; then
		printf '%s' "$OCI_OS_NAMESPACE"
		return 0
	fi
	oci_cli os ns get --query data --raw-output
}

sha256_of() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1" | cut -d' ' -f1
	else
		shasum -a 256 "$1" | cut -d' ' -f1
	fi
}

# Every surviving dump, ranked: the estate database's own dumps first, newest first within each
# tier. The legacy dumps sit under db/ and this script's own copies under estate-db/.
#
# MEASURED 2026-10-30: the bucket holds another database's dump too --
# db/2026-09-08/temporal-temporal-db-0.sql.gz -- and it is 1.5 seconds NEWER than the estate
# cluster dump. "Newest wins" therefore restored a per-database dump that has no estate database
# in it, and the run died on `FATAL: database "estate" does not exist`. A dump of another
# database is not a copy of this one, so the estate's own dumps are ranked first.
list_sources() {
	local listing
	listing=$(oci_cli os object list --namespace-name "$(namespace)" --bucket-name "$BUCKET" --all --output json)
	printf '%s' "$listing" | python3 -c '
import json, sys

prefixes = (sys.argv[1] or "").split()
bucket = sys.argv[2]
estate = sys.argv[3]
label = sys.argv[4]
try:
    data = json.load(sys.stdin).get("data") or []
except ValueError as exc:
    sys.exit("the bucket listing is not JSON: %s" % exc)
rows = []
for obj in data:
    name = obj.get("name") or ""
    if not name.endswith(".sql.gz"):
        continue
    if prefixes and not any(name.startswith(p) for p in prefixes):
        continue
    base = name.rsplit("/", 1)[-1]
    tier = 0 if (estate in base or name.startswith(label)) else 1
    rows.append((tier, obj.get("time-created") or "", name, int(obj.get("size") or 0)))
if not rows:
    sys.exit("no surviving dump under %s in bucket %s" % ("/".join(prefixes), bucket))
rows.sort(key=lambda row: (row[1], row[2]), reverse=True)
rows.sort(key=lambda row: row[0])
for tier, created, name, size in rows:
    print("\t".join([name, created, str(size)]))
' "$SOURCE_PREFIXES" "$BUCKET" "$ESTATE_DB_NAME" "$ESTATE_DB_LABEL"
}

# The best surviving dump, on the list's own ranking.
select_source() {
	local listing
	listing=$(list_sources)
	printf '%s\n' "$listing" | head -1
}

# Does this dump really carry the estate database? A cluster dump says so in its first line, and
# lists the estate database itself; a dump of one other database does neither. The reason the
# check failed is printed, so the refusal says what is wrong with the object, not just that it
# was refused.
verify_source() {
	local file="$1" head_bytes count
	[ -f "$file" ] || { printf 'it was not downloaded\n'; return 1; }
	gzip -t "$file" 2>/dev/null || { printf 'it does not decompress\n'; return 1; }
	head_bytes=$(mktemp)
	{ gzip -dc "$file" 2>/dev/null | head -c "$VERIFY_HEADER_BYTES" >"$head_bytes"; } || true
	if ! grep -aq "PostgreSQL database cluster dump" "$head_bytes"; then
		rm -f "$head_bytes"
		printf 'it is not a cluster dump, so it holds no %s database\n' "$ESTATE_DB_NAME"
		return 1
	fi
	rm -f "$head_bytes"
	# MEASURED 2026-10-30: in the surviving estate cluster dump, CREATE DATABASE estate sits at
	# byte 92964364 of 626202513 -- 89 MiB in, not in the first 64 MiB. A window would have
	# refused the very dump it was written to accept, so the marker is looked for across the
	# whole decompressed dump. grep -c reads the stream to its end and never exits early, so the
	# decompressor is never killed by SIGPIPE and the count is never a partial answer.
	count=$(gzip -dc "$file" 2>/dev/null | grep -a -c "CREATE DATABASE ${ESTATE_DB_NAME} " || true)
	if [ "${count:-0}" -eq 0 ]; then
		printf 'it is a cluster dump without the %s database\n' "$ESTATE_DB_NAME"
		return 1
	fi
	return 0
}

# Restore a dump into the running PostgreSQL. A restore that hit a real error is not a restore:
# "already exists" is the only tolerated failure, because the roles and extensions the dump
# carries are usually already there, and everything else is read out and refused.
restore() {
	local file="$1" err out benign bad rc
	[ -f "$file" ] || fail "the restore source $file does not exist"
	err=$(mktemp)
	out=$(mktemp)
	set +e
	gzip -dc "$file" | psql -v ON_ERROR_STOP=0 -q -f - >"$out" 2>"$err"
	rc=${PIPESTATUS[1]}
	set -e
	[ "$rc" -eq 0 ] || fail "psql exited $rc during the restore; the copy is not published"
	benign=$(grep -c "already exists" "$err" || true)
	bad=$(grep "ERROR:" "$err" | grep -v "already exists" || true)
	if [ -n "$bad" ]; then
		printf '%s\n' "$bad" | head -10 >&2
		fail "the restore hit $(printf '%s\n' "$bad" | wc -l | tr -d ' ') error(s); the copy is not published"
	fi
	local tables
	tables=$(psql -d estate -Atc "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname not in ('pg_catalog', 'information_schema', 'pg_toast') and c.relkind in ('r', 'p')" || true)
	case "${tables:-}" in
	'' | *[!0-9]*) fail "the estate database did not answer after the restore; the copy is not published" ;;
	esac
	[ "$tables" -gt 0 ] || fail "the estate database restored with no tables; the copy is not published"
	rm -f "$err" "$out"
	say "restored $file ($benign tolerated error(s), $tables table(s) in estate)"
}

# A fresh copy of the running PostgreSQL. pg_dumpall writes its own completion marker last, and
# a dump without it was cut short, so the marker is checked before anything is published.
dump() {
	local file="$1" tmp tail_text rc
	[ -n "$file" ] || fail "dump needs a file to write"
	tmp="${file}.partial"
	set +e
	pg_dumpall | gzip -9 >"$tmp"
	rc=${PIPESTATUS[0]}
	set -e
	[ "$rc" -eq 0 ] || fail "pg_dumpall exited $rc; no copy is published"
	gzip -t "$tmp" || fail "the fresh dump does not decompress"
	mv "$tmp" "$file"
	tail_text=$(gzip -dc "$file" | tail -c 512 || true)
	case "$tail_text" in
	*"$DUMP_MARKER"*) : ;;
	*) fail "REFUSED: the dump lacks pg_dumpall's completion marker (truncated)" ;;
	esac
	say "dumped $(wc -c <"$file" | tr -d ' ') bytes to $file"
}

write_receipt() {
	python3 - "$@" <<'PY'
import json
import sys

out, stamp, obj, size, sha, mode, source, data_as_of = sys.argv[1:9]
receipt = {
    "stamp": stamp,
    "object": obj,
    "bytes": int(size),
    "sha256": sha,
    "complete": True,
    "mode": mode,
    "source": source or None,
    "data_as_of": data_as_of or None,
}
with open(out, "w") as fh:
    json.dump(receipt, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(json.dumps(receipt, sort_keys=True))
PY
}

# Publish the copy, then the receipt. The order is the contract: the receipt is written last, so
# its presence means the copy above it landed.
publish() {
	local file="$1" bytes sha stamp object ns tail_text previous floor tmp mode source data_as_of
	[ -f "$file" ] || fail "the copy to publish $file does not exist"
	bytes=$(wc -c <"$file" | tr -d ' ')
	sha=$(sha256_of "$file")
	tail_text=$(gzip -dc "$file" | tail -c 512 || true)
	case "$tail_text" in
	*"$DUMP_MARKER"*) : ;;
	*) fail "REFUSED: the dump lacks pg_dumpall's completion marker (truncated)" ;;
	esac
	ns=$(namespace)
	stamp="${ESTATE_DB_BACKUP_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
	object="${RECEIPT_PREFIX}/estate-${stamp}.sql.gz"

	previous=$(oci_cli os object get --namespace-name "$ns" --bucket-name "$BUCKET" \
		--name "$RECEIPT_NAME" --file - 2>/dev/null | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
if not raw:
    raise SystemExit(0)
try:
    print(int(json.loads(raw).get("bytes") or 0))
except Exception:
    raise SystemExit(0)
' || true)
	if [ -n "$previous" ] && [ "$previous" -gt 0 ]; then
		floor=$(python3 -c "print(int($previous * $MIN_SIZE_RATIO))")
		if [ "$bytes" -lt "$floor" ]; then
			fail "REFUSED: $bytes bytes under $floor ($MIN_SIZE_RATIO of $previous at the previous receipt)"
		fi
	fi

	oci_cli os object put --namespace-name "$ns" --bucket-name "$BUCKET" --name "$object" \
		--file "$file" --content-type application/gzip --force

	source="${ESTATE_DB_SOURCE_NAME:-}"
	data_as_of="${ESTATE_DB_SOURCE_CREATED:-}"
	if [ -z "$source" ] && [ -n "${ESTATE_DB_SOURCE_FILE:-}" ] && [ -r "${ESTATE_DB_SOURCE_FILE:-}" ]; then
		source=$(head -1 "$ESTATE_DB_SOURCE_FILE")
		data_as_of=$(sed -n '2p' "$ESTATE_DB_SOURCE_FILE")
	fi
	mode="${ESTATE_DB_MODE:-}"
	if [ -z "$mode" ]; then
		if [ -n "$source" ]; then mode="restored-from-surviving-dump"; else mode="dump-from-running-cluster"; fi
	fi

	tmp=$(mktemp)
	write_receipt "$tmp" "$stamp" "$object" "$bytes" "$sha" "$mode" "$source" "$data_as_of"
	oci_cli os object put --namespace-name "$ns" --bucket-name "$BUCKET" --name "$RECEIPT_NAME" \
		--file "$tmp" --content-type application/json --force
	rm -f "$tmp"
	say "estate-db copied to $BUCKET/$object"
}

# The newest surviving dump, downloaded. The source it came from is written next to it, because
# the receipt has to say where the data was as old as the data is.
# Download the best surviving dump that really carries the estate database. The candidates are
# tried in rank order and each one is checked before it is trusted, so a dump of another
# database -- or a truncated object -- is skipped with its reason, not restored.
fetch_source() {
	local dest="$1" ns name created size reason candidate rejected=""
	[ -n "$dest" ] || fail "fetch-source needs a destination"
	ns=$(namespace)
	candidate="${dest}.candidate"
	while IFS=$'\t' read -r name created size; do
		[ -n "$name" ] || continue
		rm -f "$candidate"
		if ! oci_cli os object get --namespace-name "$ns" --bucket-name "$BUCKET" --name "$name" \
			--file "$candidate" >/dev/null 2>&1; then
			rejected="${rejected}"$'\n'"  $name: it could not be downloaded"
			continue
		fi
		reason=$(verify_source "$candidate") || {
			rejected="${rejected}"$'\n'"  $name: $reason"
			continue
		}
		mv "$candidate" "$dest"
		printf '%s\n%s\n' "$name" "$created" >"${dest}.source"
		say "fetched $name ($size bytes, created $created) to $dest"
		return 0
	done < <(list_sources)
	rm -f "$candidate"
	fail "no surviving dump carries the ${ESTATE_DB_NAME} database; rejected:${rejected}"
}

# Start PostgreSQL in the copy image, and wait until it answers.
#
# MEASURED 2026-10-30: the estate's own image (ghcr.io/chidionyema/postgres-partman:18.1-postgres-partman)
# carries no entrypoint of its own -- its config is Entrypoint null, Cmd ["bash"], User postgres --
# because it is built to be run by the CloudNativePG operator, which supplies the command. A
# GitHub Actions service container is given no such command, so the container started, ran bash,
# read EOF and exited: "Failed to initialize container ... One or more containers failed to start."
#
# So PostgreSQL is started here, explicitly, inside the same image: initdb, then postgres, in the
# container's own data directory. The image's extensions (vector, btree_gin, pg_trgm) and its
# 18.1 client are the ones the dump needs; only the startup is ours.
start_container() {
	local name="${1:-}" cidfile="${2:-}" cid ready=0 waited=0
	[ -n "$name" ] || fail "start-container needs a container name"
	docker rm -f "$name" >/dev/null 2>&1 || true
	docker run -d --name "$name" -e PGDATA="$PG_DATA_DIR" "$PG_IMAGE" bash -c '
		set -e
		initdb -D "$PGDATA" -U postgres --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C
		exec postgres -D "$PGDATA" -c listen_addresses=127.0.0.1 -c fsync=off -c full_page_writes=off -c max_wal_size=8GB -c shared_buffers=512MB
	' >/dev/null
	while [ "$waited" -lt "$PG_READY_TIMEOUT" ]; do
		if docker exec "$name" pg_isready -U postgres -q >/dev/null 2>&1; then
			ready=1
			break
		fi
		if ! docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null | grep -q true; then
			break
		fi
		waited=$((waited + 2))
		sleep 2
	done
	if [ "$ready" -ne 1 ]; then
		printf 'FAIL    estate-db-backup  the PostgreSQL container %s did not become ready in %ss\n' \
			"$name" "$PG_READY_TIMEOUT" >&2
		{ docker logs "$name" || true; } >&2
		{ docker exec "$name" bash -c 'ls /usr/lib/postgresql/18/bin 2>&1 | head -20; ls -ld /tmp 2>&1' || true; } >&2
		exit 1
	fi
	cid=$(docker ps -q --filter "name=^/${name}$" | head -1)
	[ -n "$cid" ] || fail "the PostgreSQL container $name has no id"
	if [ -n "$cidfile" ]; then
		printf '%s\n' "$cid" >"$cidfile"
	fi
	printf 'cid=%s\n' "$cid"
	say "PostgreSQL is ready in $name ($cid)"
}

# The extensions the surviving dump asks for. MEASURED 2026-10-30: the dump carries
# `CREATE EXTENSION vector`, `btree_gin` and `pg_trgm`; without them the restore dies on
# "extension ... is not available" a long way into a 626 MB restore, and the failure looks like
# the restore's fault rather than the image's. So they are checked first, and a refusal prints
# what the image does have.
check_extensions() {
	local cid="${1:-}" missing="" name found
	for name in $REQUIRED_EXTENSIONS; do
		found=$(ext_query "$cid" "select 1 from pg_available_extensions where name = '$name'")
		case "$found" in
		1) : ;;
		*) missing="${missing} ${name}" ;;
		esac
	done
	if [ -n "$missing" ]; then
		printf 'FAIL    estate-db-backup  the image has no%s extension; the surviving dump needs them\n' \
			"$missing" >&2
		ext_query "$cid" "select name from pg_available_extensions order by name" >&2 || true
		return 1
	fi
	say "the image has every extension the dump needs ($REQUIRED_EXTENSIONS)"
}

# The query runs where PostgreSQL runs: in the container when a container id is given, on the
# host otherwise.
ext_query() {
	local cid="${1:-}" query="${2:-}"
	if [ -n "$cid" ]; then
		docker exec -e PGHOST="${PGHOST:-127.0.0.1}" -e PGPORT="${PGPORT:-5432}" \
			-e PGUSER="${PGUSER:-postgres}" -e PGPASSWORD="${PGPASSWORD:-}" \
			"$cid" psql -Atc "$query" 2>/dev/null || true
	else
		psql -Atc "$query" 2>/dev/null || true
	fi
}

check_extensions_container() {
	local cid="$1"
	[ -n "$cid" ] || fail "check-extensions-container needs the container id"
	check_extensions "$cid"
}

# Restore and dump run where psql and pg_dumpall live: inside the PostgreSQL container. The
# plumbing lives here, not in the workflow, so it can be tested here.
restore_container() {
	local cid="$1" file="$2"
	[ -n "$cid" ] || fail "restore-container needs the container id"
	[ -n "$file" ] || fail "restore-container needs the dump to restore"
	docker cp "$file" "$cid:/tmp/estate-db-source.sql.gz" >/dev/null
	docker cp "$SCRIPT_PATH" "$cid:/tmp/estate-db-backup.sh" >/dev/null
	docker exec -e PGHOST="${PGHOST:-127.0.0.1}" -e PGPORT="${PGPORT:-5432}" \
		-e PGUSER="${PGUSER:-postgres}" -e PGPASSWORD="${PGPASSWORD:-}" \
		"$cid" bash /tmp/estate-db-backup.sh restore /tmp/estate-db-source.sql.gz
}

dump_container() {
	local cid="$1" file="$2"
	[ -n "$cid" ] || fail "dump-container needs the container id"
	[ -n "$file" ] || fail "dump-container needs a file to write"
	docker cp "$SCRIPT_PATH" "$cid:/tmp/estate-db-backup.sh" >/dev/null
	docker exec -e PGHOST="${PGHOST:-127.0.0.1}" -e PGPORT="${PGPORT:-5432}" \
		-e PGUSER="${PGUSER:-postgres}" -e PGPASSWORD="${PGPASSWORD:-}" \
		"$cid" bash /tmp/estate-db-backup.sh dump /tmp/estate-dump.sql.gz
	docker cp "$cid:/tmp/estate-dump.sql.gz" "$file" >/dev/null
	say "copied the fresh dump to $file"
}

run_service() {
	local tmpdir
	tmpdir=$(mktemp -d)
	fetch_source "$tmpdir/source.sql.gz"
	restore "$tmpdir/source.sql.gz"
	dump "$tmpdir/estate.sql.gz"
	ESTATE_DB_SOURCE_FILE="$tmpdir/source.sql.gz.source" publish "$tmpdir/estate.sql.gz"
	rm -rf "$tmpdir"
}

case "${1:-}" in
select-source) select_source ;;
fetch-source) fetch_source "${2:-}" ;;
start-container) start_container "${2:-}" "${3:-}" ;;
restore) restore "${2:-}" ;;
check-extensions) check_extensions ;;
check-extensions-container) check_extensions_container "${2:-}" ;;
dump) dump "${2:-}" ;;
restore-container) restore_container "${2:-}" "${3:-}" ;;
dump-container) dump_container "${2:-}" "${3:-}" ;;
publish) publish "${2:-}" ;;
run) run_service ;;
*)
	fail "unknown subcommand '${1:-}'; use select-source, fetch-source, start-container, restore, dump, restore-container, dump-container, check-extensions, check-extensions-container, publish or run"
	;;
esac
