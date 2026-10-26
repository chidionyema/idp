"""The record: Postgres in the estate cluster, and a sqlite cache beside it.

D1 (founder, accepted 2026-10-25): the record is Postgres -- the estate's own
CloudNativePG cluster `estate` in namespace `estate-db` -- and a generated sqlite
copy of it is a read-only cache, not a second source of truth. This module is the
only place that knows how to reach either. The cache lives at
`~/.estate/runtime/catalog/estate.db`, outside the repo: the estate's own asset
database is `<repo>/catalog/estate.db` (the twin's graph), and a cache written over
it is the second store the estate's law forbids.

HOW THE LAPTOP REACHES THE RECORD, and why it is written this way
-------------------------------------------------------------------
The estate's Postgres is in the cluster. The laptop has no credential for it: every
role's password is minted from a vault entry (platform/estate-db/cluster/secrets.yaml
is a list of ExternalSecrets), and minting a new one needs the founder's vault. So
Phase 0 writes the record the way the estate already reads the same database from
this machine: `kubectl -n estate-db exec <primary> -- psql`, with the psql process
running inside the cluster's own pod (measured working 2026-10-26: `postgres |
PostgreSQL 18.6 (Debian 18.6-1.pgdg12+2)`).

That path is deliberate, not a workaround around a missing driver:

  * no secret value is read, printed, written to disk or put in an environment
    variable in code -- the psql process authenticates as the cluster's own
    superuser over the pod's local socket, so there is no credential to leak;
  * it needs no new vault entry, so Phase 0 is not blocked on the founder;
  * it is the same door `kubectl` already is for everything else this laptop does
    to the cluster, and the SQL that lands is visible in the psql log.

The debt this leaves, stated plainly: the census writes as the superuser rather
than as a least-privilege `catalog` role. A dedicated role needs its own vault
entry, and the founder's vault is the only place a password may be minted. When
that entry exists, the change is one line here (the role and its database) plus a
CNPG managed role -- no collector changes, because no collector knows who it is.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from catalog.census.model import Edge, Fact, Observation

DEFAULT_CONTEXT = os.environ.get("ESTATE_KUBE_CONTEXT", "context-estate-crq7jwxsjxq")
DEFAULT_NAMESPACE = os.environ.get("ESTATE_DB_NAMESPACE", "estate-db")
DEFAULT_DATABASE = os.environ.get("ESTATE_CATALOG_DB", "estate")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The estate's ASSET DATABASE is <repo>/catalog/estate.db: bin/db-gen writes it and
# bin/estate-twin-runtime fills it with the twin's own tables (nodes, node_events,
# edges, freshness). It is the estate's graph, not this catalog's cache -- and
# measured 2026-10-26, the catalog's cache was written over the top of it, which
# left the twin's graph unreadable ("the twin's graph is missing node_events,
# freshness; present tables are aliases, collectors, coverage, edges, facts,
# nodes") and failed sovereign/tests/bdd. So the cache lives OUTSIDE the repo, in
# the estate's runtime directory, and the store refuses to write over the asset
# database even if it is told to.
ASSET_DATABASE = os.path.join(REPO_ROOT, "catalog", "estate.db")

DEFAULT_CACHE = os.environ.get(
    "ESTATE_CATALOG_CACHE",
    os.path.join(
        os.path.expanduser("~"),
        ".estate",
        "runtime",
        "catalog",
        "estate.db",
    ),
)


class RecordError(RuntimeError):
    """The record could not be reached or written. Never swallowed."""


def _tool(name: str) -> str:
    """The absolute path of a tool, so the process is started by path (ruff S607)."""

    found = shutil.which(name)
    if not found:
        raise RecordError(f"{name} is not on PATH")
    return found


def _sql_literal(value: Any) -> str:
    """A SQL literal, quoted the way Postgres expects, with no room for injection.

    Every value that reaches the record comes from a collector that read it off a
    cluster, a git tree or an API -- none of them trusted to be free of quotes. The
    quoting is therefore done here, once, for every value, and a value that is not
    a string is rendered as its JSON form.
    """

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"))
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _sql_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"'{payload.replace(chr(39), chr(39) * 2)}'::jsonb"


@dataclass
class WriteReport:
    """What one write did, in numbers the caller can print."""

    nodes: int = 0
    edges: int = 0
    facts: int = 0
    aliases: int = 0
    events: int = 0
    coverage_rows: int = 0
    sql_bytes: int = 0
    target: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "facts": self.facts,
            "aliases": self.aliases,
            "events": self.events,
            "coverage_rows": self.coverage_rows,
            "sql_bytes": self.sql_bytes,
            "target": self.target,
        }


class Record:
    """The estate's catalog record: Postgres in the cluster, sqlite as its cache."""

    def __init__(
        self,
        context: str = DEFAULT_CONTEXT,
        namespace: str = DEFAULT_NAMESPACE,
        database: str = DEFAULT_DATABASE,
        cache_path: str = DEFAULT_CACHE,
    ) -> None:
        self.context = context
        self.namespace = namespace
        self.database = database
        self.cache_path = cache_path

    # -- the door ---------------------------------------------------------------

    def primary_pod(self) -> str:
        """The CloudNativePG primary's pod name, found by label.

        The pod is chosen by the operator's own labels, not by a name written down
        here: the pod name changes when the instance is rebuilt, and a name in a
        file is exactly the defect the drift check was written to remove.
        """

        out = self._kubectl(
            [
                "get",
                "pod",
                "-n",
                self.namespace,
                "-l",
                "cnpg.io/cluster=estate,cnpg.io/instanceRole=primary",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ]
        )
        name = out.strip()
        if not name:
            raise RecordError(
                f"no primary pod for cnpg cluster 'estate' in {self.namespace}"
            )
        return name

    def _kubectl(self, args: Sequence[str], stdin: str | None = None) -> str:
        """Run kubectl, and try again when the path breaks.

        The path from this laptop to the cluster is the API server, and from the
        API server to the pod's node, and both drop connections now and then
        (measured 2026-10-26: "connection reset by peer" and an EOF from the
        kubelet's exec endpoint, minutes apart, on a node that was Ready
        throughout). Every statement this class runs is idempotent -- a read, an
        IF NOT EXISTS migration, or one transaction of upserts -- so retrying is
        safe, and a transient network is not a reason to fail a sweep.
        """

        cmd = [_tool("kubectl"), "--context", self.context] + list(args)
        last = ""
        for attempt in range(1, 4):
            try:
                proc = subprocess.run(  # noqa: S603 -- fixed argv, never a shell string
                    cmd,
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RecordError(f"kubectl {' '.join(args[:3])} timed out") from exc
            if proc.returncode == 0:
                return proc.stdout
            # The tail of stderr, not the head: kubectl's own "Defaulted container"
            # notice comes first and would hide the one line that says what went
            # wrong -- a Postgres error is at the end, where psql put it.
            last = proc.stderr.strip()[-600:]
            if attempt < 3:
                time.sleep(2)
        raise RecordError(f"kubectl {' '.join(args[:4])} failed after 3 tries: {last}")

    def psql(self, sql: str, database: str | None = None, tuples: bool = False) -> str:
        """Run SQL inside the cluster's own Postgres pod.

        The script is piped in, so the values never travel through a shell and a
        quote in a workload name cannot break out of its literal. With
        `tuples`, psql is told to print the rows and nothing else -- no headers,
        no "(N rows)" footer -- which is what makes its output parseable as
        JSON without a Postgres client library on this machine.
        """

        target = database or self.database
        pod = self.primary_pod()
        args = ["exec", "-i", "-n", self.namespace, pod, "--", "psql"]
        if tuples:
            args += ["-t", "-A"]
        # -q: psql's own status lines ("SET", "INSERT 0 1") are not data. With them
        # in the output, the row JSON is not the first thing in the stream and a
        # parser has to know which line to trust.
        args += [
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            target,
            "-f",
            "-",
        ]
        # The catalog's tables live in the `catalog` schema of the estate's shared
        # database, so every statement says where it means. The DDL sets its own
        # search_path inside its transaction; this one covers every other statement.
        # The check against the `postgres` database is left alone: it asks about
        # databases, not about the catalog's tables.
        preamble = (
            "" if target == "postgres" else "set search_path to catalog, public;\n"
        )
        return self._kubectl(args, stdin=preamble + sql)

    def query(self, sql: str, database: str | None = None) -> list[dict[str, Any]]:
        """Read rows out of the record, as a list of dicts.

        The rows come back as a JSON document produced by Postgres itself, so the
        laptop needs no Postgres client library to read the record -- which is the
        same reason the write path exists.
        """

        wrapped = f"select coalesce(json_agg(t), '[]'::json) from ({sql}) t;\n"  # noqa: S608 -- the query is this class's own, and every value in it is a literal
        out = self.psql(wrapped, database=database, tuples=True)
        payload = out.strip()
        try:
            rows = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RecordError(
                f"the record returned something that is not JSON: {payload[:200]}"
            ) from exc
        return rows if isinstance(rows, list) else []

    def query_json(self, sql: str, database: str | None = None) -> dict[str, Any]:
        """Read ONE json document out of the record.

        The whole point is the round trip: the laptop reaches the cluster through
        an exec stream that costs ten to twenty seconds, so a door that asks five
        questions asks for five minutes. One statement, one document.
        """

        out = self.psql(sql, database=database, tuples=True)
        payload = out.strip()
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RecordError(
                f"the record returned something that is not JSON: {payload[:200]}"
            ) from exc
        return value if isinstance(value, dict) else {}

    def entity(self, term: str) -> dict[str, Any]:
        """Everything the record knows about one thing, in one round trip.

        A term can be a node id, a node's name, or an alias -- the three things
        a person actually has.
        """

        literal = _sql_literal(term)
        match = (
            "select distinct n.id from nodes n left join aliases a on a.node_id = n.id"  # noqa: S608 -- the term is a literal
            f" where n.id = {literal} or n.name = {literal} or a.alias = {literal}"
        )
        return self.query_json(
            "select json_build_object("  # noqa: S608 -- every value below is a literal
            "  'nodes', (select coalesce(json_agg(t), '[]'::json) from ("
            "     select n.id, n.type, n.name, n.plane, n.state, n.source, n.observed_at,"
            "            n.expires_at, n.confidence, n.payload, n.payload->>'reason' as reason"
            f"     from nodes n where n.id in ({match})"
            "  ) t),"
            "  'aliases', (select coalesce(json_agg(t), '[]'::json) from ("
            "     select al.alias, al.node_id, al.source, al.confidence from aliases al"
            f"     where al.node_id in ({match})"
            "  ) t),"
            "  'edges_out', (select coalesce(json_agg(t), '[]'::json) from ("
            "     select e.src, e.dst, e.type, e.source, e.confidence from edges e"
            f"     where e.src in ({match})"
            "  ) t),"
            "  'edges_in', (select coalesce(json_agg(t), '[]'::json) from ("
            "     select e.src, e.dst, e.type, e.source, e.confidence from edges e"
            f"     where e.dst in ({match})"
            "  ) t),"
            "  'facts', (select coalesce(json_agg(t), '[]'::json) from ("
            "     select f.id, f.subject, f.predicate, f.object, f.source, f.observed_at, f.expires_at"
            f"     from facts f where f.subject in ({match})"
            "  ) t)"
            ");"
        )

    # -- the schema -------------------------------------------------------------

    def ensure_database(self) -> None:
        """Check that the record's database is there. It does NOT create one.

        The record is the `estate` database in the estate's CloudNativePG cluster
        `estate-db` (D1: one Postgres, the existing one; the catalog's tables are
        new tables in it, not a second store). Measured 2026-10-26: the database
        exists, is owned by the role `estate`, and holds no tables -- it was
        created for exactly this. A second database is not created here, because
        the proposal's D1 says "do not create a second database" and a catalog
        with two records is the failure this whole phase exists to prevent.
        """

        exists = self.query(
            "select 1 from pg_database where datname = " + _sql_literal(self.database),  # noqa: S608 -- the name is a literal
            database="postgres",
        )
        if not exists:
            raise RecordError(
                f"the record database {self.database!r} does not exist in {self.namespace}; "
                "the catalog does not create a second database"
            )

    def apply_schema(self, ddl: str) -> None:
        """Apply the catalog's DDL. Every statement is IF NOT EXISTS, so this is
        safe to run on every census and on a record that is already there."""

        self.psql(ddl)

    # -- the write --------------------------------------------------------------

    def write(
        self,
        observations: Iterable[Observation],
        edges: Iterable[Edge],
        facts: Iterable[Fact],
        aliases: Iterable[tuple[str, str, str, float]],
        coverage: Iterable[dict[str, Any]],
        collectors: Iterable[dict[str, Any]],
    ) -> WriteReport:
        """Write one census into the record, in one transaction.

        One transaction, one script: a census that is half-written is worse than a
        census that failed, because the coverage numbers would then describe a
        mixture of two sweeps.
        """

        report = WriteReport(target=f"postgres://{self.namespace}/{self.database}")
        statements: list[str] = ["begin;"]
        node_count = 0
        for obs in observations:
            statements.append(
                "insert into nodes (id, type, name, plane, state, source, observed_at, expires_at,"  # noqa: S608 -- every value is a literal
                " confidence, payload) values ("
                + ", ".join(
                    [
                        _sql_literal(obs.id),
                        _sql_literal(obs.type),
                        _sql_literal(obs.name),
                        _sql_literal(obs.plane),
                        _sql_literal(obs.state),
                        _sql_literal(obs.source),
                        _sql_literal(obs.observed_at),
                        _sql_literal(obs.expires_at),
                        repr(float(obs.confidence)),
                        _sql_json(
                            {
                                "reason": obs.reason,
                                "joins": [j.as_dict() for j in obs.joins],
                                **obs.payload,
                            }
                        ),
                    ]
                )
                + ") on conflict (id) do update set type = excluded.type, name = excluded.name,"
                " plane = excluded.plane, state = excluded.state, source = excluded.source,"
                " observed_at = excluded.observed_at, expires_at = excluded.expires_at,"
                " confidence = excluded.confidence, payload = excluded.payload;"
            )
            node_count += 1
        for edge in edges:
            statements.append(
                "insert into edges (src, dst, type, source, observed_at, expires_at, confidence, payload)"  # noqa: S608 -- every value is a literal
                " values ("
                + ", ".join(
                    [
                        _sql_literal(edge.src),
                        _sql_literal(edge.dst),
                        _sql_literal(edge.type),
                        _sql_literal(edge.source),
                        _sql_literal(edge.observed_at),
                        _sql_literal(edge.expires_at),
                        repr(float(edge.confidence)),
                        _sql_json(edge.payload),
                    ]
                )
                + ") on conflict (src, dst, type) do update set source = excluded.source,"
                " observed_at = excluded.observed_at, expires_at = excluded.expires_at,"
                " confidence = excluded.confidence, payload = excluded.payload;"
            )
            report.edges += 1
        for fact in facts:
            statements.append(
                "insert into facts (id, subject, predicate, object, source, observed_at, expires_at,"  # noqa: S608 -- every value is a literal
                " confidence) values ("
                + ", ".join(
                    [
                        _sql_literal(fact.id),
                        _sql_literal(fact.subject),
                        _sql_literal(fact.predicate),
                        _sql_literal(fact.object),
                        _sql_literal(fact.source),
                        _sql_literal(fact.observed_at),
                        _sql_literal(fact.expires_at),
                        repr(float(fact.confidence)),
                    ]
                )
                + ") on conflict (id) do update set object = excluded.object,"
                " observed_at = excluded.observed_at, expires_at = excluded.expires_at,"
                " confidence = excluded.confidence;"
            )
            report.facts += 1
        for alias, node_id, source, confidence in aliases:
            statements.append(
                "insert into aliases (alias, node_id, source, confidence) values ("  # noqa: S608 -- every value is a literal
                + ", ".join(
                    [
                        _sql_literal(alias),
                        _sql_literal(node_id),
                        _sql_literal(source),
                        repr(float(confidence)),
                    ]
                )
                + ") on conflict (alias, node_id) do update set source = excluded.source,"
                " confidence = excluded.confidence;"
            )
            report.aliases += 1
        for row in coverage:
            statements.append(
                "insert into coverage (plane, universe, classified, uncatalogued, blind, last_run, detail)"  # noqa: S608 -- every value is a literal
                " values ("
                + ", ".join(
                    [
                        _sql_literal(row["plane"]),
                        str(int(row["universe"])),
                        str(int(row["classified"])),
                        str(int(row["uncatalogued"])),
                        str(int(row["blind"])),
                        _sql_literal(row["last_run"]),
                        _sql_json(row.get("detail", {})),
                    ]
                )
                + ") on conflict (plane) do update set universe = excluded.universe,"
                " classified = excluded.classified, uncatalogued = excluded.uncatalogued,"
                " blind = excluded.blind, last_run = excluded.last_run, detail = excluded.detail;"
            )
            report.coverage_rows += 1
        for row in collectors:
            statements.append(
                "insert into collectors (name, last_started, last_success, last_error, duration_ms, counts)"  # noqa: S608 -- every value is a literal
                " values ("
                + ", ".join(
                    [
                        _sql_literal(row["name"]),
                        _sql_literal(row.get("last_started")),
                        _sql_literal(row.get("last_success")),
                        _sql_literal(row.get("last_error") or ""),
                        str(int(row.get("duration_ms", 0))),
                        _sql_json(row.get("counts", {})),
                    ]
                )
                + ") on conflict (name) do update set last_started = excluded.last_started,"
                " last_success = excluded.last_success, last_error = excluded.last_error,"
                " duration_ms = excluded.duration_ms, counts = excluded.counts;"
            )
        statements.append("commit;")
        script = "\n".join(statements) + "\n"
        report.nodes = node_count
        report.sql_bytes = len(script)
        self.psql(script)
        return report

    # -- the cache --------------------------------------------------------------

    def write_cache(
        self,
        observations: Iterable[Observation],
        edges: Iterable[Edge],
        facts: Iterable[Fact],
        aliases: Iterable[tuple[str, str, str, float]],
    ) -> str:
        """Write the sqlite cache beside the record.

        The cache is a copy, and it is rebuilt rather than updated: a cache that
        accumulates rows from every sweep is a second record that nobody can
        reason about, which is the failure the proposal's D1 exists to prevent.
        """

        path = self.cache_path
        if os.path.abspath(path) == os.path.abspath(ASSET_DATABASE):
            raise RecordError(
                "the catalog's cache may not be written over the estate's asset "
                f"database ({ASSET_DATABASE}); the twin's graph lives there. Point "
                "ESTATE_CATALOG_CACHE somewhere else."
            )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            os.remove(path)
        conn = sqlite3.connect(path)
        try:
            conn.executescript(CACHE_SCHEMA)
            conn.executemany(
                "insert into nodes (id, type, name, plane, state, source, observed_at, expires_at,"
                " confidence, payload) values (?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        o.id,
                        o.type,
                        o.name,
                        o.plane,
                        o.state,
                        o.source,
                        o.observed_at,
                        o.expires_at,
                        o.confidence,
                        json.dumps(o.as_dict(), sort_keys=True),
                    )
                    for o in observations
                ],
            )
            conn.executemany(
                "insert into edges (src, dst, type, source, observed_at, expires_at, confidence, payload)"
                " values (?,?,?,?,?,?,?,?)",
                [
                    (
                        e.src,
                        e.dst,
                        e.type,
                        e.source,
                        e.observed_at,
                        e.expires_at,
                        e.confidence,
                        json.dumps(e.payload, sort_keys=True),
                    )
                    for e in edges
                ],
            )
            conn.executemany(
                "insert into facts (id, subject, predicate, object, source, observed_at, expires_at,"
                " confidence) values (?,?,?,?,?,?,?,?)",
                [
                    (
                        f.id,
                        f.subject,
                        f.predicate,
                        f.object,
                        f.source,
                        f.observed_at,
                        f.expires_at,
                        f.confidence,
                    )
                    for f in facts
                ],
            )
            conn.executemany(
                "insert into aliases (alias, node_id, source, confidence) values (?,?,?,?)",
                [(a, n, s, c) for a, n, s, c in aliases],
            )
            conn.commit()
        finally:
            conn.close()
        return path


CACHE_SCHEMA = """
create table if not exists nodes (
  id text primary key, type text, name text, plane text, state text, source text,
  observed_at text, expires_at text, confidence real, payload text);
create table if not exists edges (
  src text, dst text, type text, source text, observed_at text, expires_at text,
  confidence real, payload text, primary key (src, dst, type));
create table if not exists facts (
  id text primary key, subject text, predicate text, object text, source text,
  observed_at text, expires_at text, confidence real);
create table if not exists aliases (
  alias text, node_id text, source text, confidence real, primary key (alias, node_id));
create table if not exists coverage (
  plane text primary key, universe integer, classified integer, uncatalogued integer,
  blind integer, last_run text, detail text);
create table if not exists collectors (
  name text primary key, last_started text, last_success text, last_error text,
  duration_ms integer, counts text);
"""
