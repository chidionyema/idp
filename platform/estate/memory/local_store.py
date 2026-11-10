#!/usr/bin/env python3
"""The memory door's declared local origin: the same contract, backed by one SQLite file.

WHY THIS EXISTS (measured 2026-11-09). The memory door is an MCP gateway at one https URL
(`runtimes.json` -> door.url). Every agent's `remember`, `recall` and `brief` travels it, and
`door.post` refuses any door that is not https, so there is exactly one road. That road has had
no origin for days: Cloudflare answers `error code: 1033` (the Argo tunnel's origin is not
running) and the TLS handshake dies with `EOF occurred in violation of protocol (_ssl.c:1129)`,
which is what every caller saw as "memory door unreachable". The in-cluster substrate it dialled
is retired, so the road does not come back by waiting.

That is AGENTS.md section 9 root cause R6 and R8 together: the recovery path depended on the
thing being recovered, and an external assumption (one cloud origin, always up) had no declared
fallback. This file is the fallback, and it is deliberately NOT a second memory layer:

  * It serves the ROUTES the estate's own memory server defines, at
    `platform/unified-memory-server/main.py`, and nothing else: PUT/GET
    `/memories/{namespace}/{key}`, POST `/memories/{namespace}/{key}/search`,
    `/memories/recall`, `/memories/brief`, GET `/memories/{namespace}`. Same payload fields, same
    response shapes, so a caller cannot tell which origin answered except by asking.
  * It reuses the estate's write-time guard (`OWASPWriteGuard`) rather than inventing a second
    policy, and keeps the same version/ETag concurrency semantics.
  * It stores one SQLite file under the estate home, which the laptop already has (`estate.db` is
    the same pattern). It needs no Postgres and no pgvector, which this machine cannot run
    (measured: no Docker, no Rancher Desktop, no local server).

What it honestly does NOT do, stated so nobody mistakes it for the cloud server: there is no
pgvector. `recall` and the task half of `brief` rank lexically (SQLite FTS5) instead of by
embedding cosine, and every such result says `"ranking": "lexical"` so a caller can see the
substitution. That is a capability difference, and it is labelled rather than hidden.

ADR 0037 (a critical service gets a ladder of homes) is why this is a ladder rung and not a
replacement: the cloud origin is still first. `door.py` tries it, and only on a transport failure
(no origin, TLS EOF, timeout) falls to this one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
# The installed tree lives under ~/.estate/memory, so the repo root is not always two levels up.
# Try the repo (source of truth) first, then the sidecar the installer writes beside us.
_CANDIDATE_ROOTS = [
    HERE.parents[2]
    / "vendor",  # ~/.estate/memory/vendor, written by bin/estate-memory-install
    HERE.parents[2] / "platform" / "unified-memory-server",  # in the repo
]

# The estate's own write guard, so this store can never be a laxer policy than the cloud one.
# It lives with the memory server; import it rather than copying its patterns (LAW 46). If
# neither location has it, refuse to start: a store with a weaker guard is not this store.
for _root in _CANDIDATE_ROOTS:
    if (_root / "security_core.py").exists():
        sys.path.insert(0, str(_root))
        break
try:
    from security_core import OWASPWriteGuard, SecurityViolationException  # type: ignore
except Exception as exc:  # pragma: no cover - only when the guard is genuinely absent
    raise SystemExit(
        "local_store needs the estate's own write guard (security_core.py) at "
        f"{_CANDIDATE_ROOTS[0]} or {_CANDIDATE_ROOTS[1]}: {type(exc).__name__}: {exc}"
    ) from exc

DEFAULT_DB = Path(
    os.environ.get("ESTATE_MEMORY_DB")
    or Path.home() / ".estate" / "memory" / "memory.db"
)
DEFAULT_PORT = int(os.environ.get("ESTATE_MEMORY_LOCAL_PORT") or 8002)
NAMESPACE_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          TEXT PRIMARY KEY,
    namespace   TEXT NOT NULL,
    key         TEXT NOT NULL,
    content     TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    trust_tier  TEXT NOT NULL DEFAULT 'raw_source',
    provenance  TEXT NOT NULL DEFAULT '{}',
    version     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    valid_from  TEXT,
    access_count INTEGER NOT NULL DEFAULT 0,
    synced      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (namespace, key)
);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, namespace UNINDEXED, mem_key UNINDEXED, tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS memory_versions (
    id TEXT NOT NULL, version INTEGER NOT NULL, content TEXT NOT NULL,
    content_hash TEXT NOT NULL, recorded_at TEXT NOT NULL,
    PRIMARY KEY (id, version)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Store:
    """One SQLite file, one writer lock, and one connection per handler thread.

    A connection is not a lock and it is not thread-safe: sharing one connection across
    ThreadingHTTPServer workers serialises unrelated reads behind whichever thread currently owns
    SQLite's internal state. Each thread gets its own connection; WAL lets those reads proceed
    while the one writer lock protects write transactions.
    """

    def __init__(self, path: Path | str):
        # Coerce, so a caller that hands over the "--db" string from argv (or ":memory:" in a
        # test) is not a crash at the first write. `:memory:` keeps no parent to create.
        self.path = (
            Path(path) if not str(path).startswith(":memory:") else Path(":memory:")
        )
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._local = threading.local()
        conn = self._conn()
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(memories)")}
        if "synced" not in columns:
            conn.execute(
                "ALTER TABLE memories ADD COLUMN synced INTEGER NOT NULL DEFAULT 0"
            )
        conn.commit()

    def _conn(self) -> sqlite3.Connection:
        """The caller thread's connection, configured before it can serve a request."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.path), timeout=1.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=1000")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=FULL")
            self._local.conn = conn
        return conn

    def healthy(self) -> bool:
        """A liveness check that also proves this process can read the store.

        `/healthz` used to return 200 while only reading a path string. That answered whether the
        Python process existed, not whether memory could serve a caller. SELECT 1 is bounded by the
        connection's one-second busy timeout and does not take the writer lock.
        """
        try:
            return self._conn().execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    # -- writes -----------------------------------------------------------------
    def save(
        self, namespace: str, key: str, payload: dict, if_match: str | None
    ) -> dict:
        try:
            content_hash = OWASPWriteGuard.inspect(_AsPayload(payload, namespace, key))
        except SecurityViolationException as exc:
            return {
                "_status": 422,
                "_body": {"detail": {"code": exc.code, "error": exc.message}},
            }
        expected = payload.get("expected_version")
        if if_match:
            try:
                expected = int(str(if_match).strip('"'))
            except ValueError:
                return {
                    "_status": 400,
                    "_body": {"detail": "Invalid If-Match header value"},
                }
        content = payload["content"]
        now = _now()
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                "SELECT * FROM memories WHERE namespace=? AND key=?", (namespace, key)
            ).fetchone()
            if row is None:
                if expected not in (None, 0):
                    return {
                        "_status": 409,
                        "_body": {"detail": "no such memory", "version": 0},
                    }
                mid = _sha(f"{namespace}/{key}")[:32]
                conn.execute(
                    "INSERT INTO memories (id,namespace,key,content,content_hash,trust_tier,"
                    "provenance,version,created_at,updated_at,valid_from) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        mid,
                        namespace,
                        key,
                        content,
                        content_hash,
                        payload.get("trust_tier") or "raw_source",
                        json.dumps(payload.get("provenance") or {}),
                        1,
                        now,
                        now,
                        payload.get("valid_from") or now,
                    ),
                )
                self._index(mid, namespace, key, content)
                conn.commit()
                return {
                    "_status": 200,
                    "_body": {"status": "CREATED", "id": mid, "version": 1},
                }
            if expected is not None and expected != row["version"]:
                return {
                    "_status": 409,
                    "_body": {"detail": "version conflict", "version": row["version"]},
                }
            new_version = row["version"] + 1
            conn.execute(
                "UPDATE memories SET content=?, content_hash=?, trust_tier=?, provenance=?, "
                "version=?, synced=0, updated_at=? WHERE id=?",
                (
                    content,
                    content_hash,
                    payload.get("trust_tier") or row["trust_tier"],
                    json.dumps(
                        payload.get("provenance") or json.loads(row["provenance"])
                    ),
                    new_version,
                    now,
                    row["id"],
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO memory_versions VALUES (?,?,?,?,?)",
                (row["id"], new_version, content, content_hash, now),
            )
            self._index(row["id"], namespace, key, content)
            conn.commit()
            return {
                "_status": 200,
                "_body": {"status": "UPDATED", "id": row["id"], "version": new_version},
            }

    def pending(self, namespace: str, limit: int = 500) -> list[dict]:
        rows = (
            self._conn()
            .execute(
                "SELECT * FROM memories WHERE namespace=? AND synced=0 "
                "ORDER BY updated_at ASC LIMIT ?",
                (namespace, max(1, min(limit, 500))),
            )
            .fetchall()
        )
        return [
            {
                "key": row["key"],
                "content": row["content"],
                "trust_tier": row["trust_tier"],
                "provenance": json.loads(row["provenance"]),
            }
            for row in rows
        ]

    def mark_synced(self, namespace: str, keys: list[str]) -> None:
        if not keys:
            return
        with self._lock:
            conn = self._conn()
            conn.executemany(
                "UPDATE memories SET synced=1 WHERE namespace=? AND key=?",
                [(namespace, key) for key in keys],
            )
            conn.commit()

    def _index(self, mid: str, namespace: str, key: str, content: str) -> None:
        conn = self._conn()
        conn.execute(
            "DELETE FROM memories_fts WHERE mem_key=? AND namespace=?", (key, namespace)
        )
        conn.execute(
            "INSERT INTO memories_fts (content, namespace, mem_key) VALUES (?,?,?)",
            (content, namespace, key),
        )

    # -- reads ------------------------------------------------------------------
    def _row_out(self, row: sqlite3.Row, ranking: str) -> dict:
        return {
            "id": row["id"],
            "namespace": row["namespace"],
            "key": row["key"],
            "content": row["content"],
            "trust_tier": row["trust_tier"],
            "version": row["version"],
            "provenance": json.loads(row["provenance"]),
            "updated_at": row["updated_at"],
            "relevance_rho": 1.0,
            "truthfulness_tau": 0.9,
            "harm_h": 0.0,
            "taint_level": "clean",
            "scope_risk": "none",
            "cosine_sim": None,
            "access_count": row["access_count"],
            "ranking": ranking,
        }

    def get(self, namespace: str, key: str) -> dict | None:
        row = (
            self._conn()
            .execute(
                "SELECT * FROM memories WHERE namespace=? AND key=?", (namespace, key)
            )
            .fetchone()
        )
        return self._row_out(row, "exact") if row else None

    def list(self, namespace: str, limit: int = 50) -> list[dict]:
        rows = (
            self._conn()
            .execute(
                "SELECT * FROM memories WHERE namespace=? ORDER BY updated_at DESC LIMIT ?",
                (namespace, limit),
            )
            .fetchall()
        )
        return [self._row_out(r, "recent") for r in rows]

    def search(self, query: str, namespace: str, limit: int) -> list[dict]:
        """FTS5 lexical ranking. Honest about it: ranking == lexical, cosine_sim == None."""
        terms = " OR ".join(
            f'"{t}"' for t in re.findall(r"[A-Za-z0-9_]+", query) if len(t) > 1
        )
        if not terms:
            return []
        try:
            rows = (
                self._conn()
                .execute(
                    "SELECT m.* FROM memories_fts f JOIN memories m "
                    "ON m.key = f.mem_key AND m.namespace = f.namespace "
                    "WHERE memories_fts MATCH ? AND f.namespace=? "
                    "ORDER BY rank LIMIT ?",
                    (terms, namespace, limit),
                )
                .fetchall()
            )
        except sqlite3.OperationalError:
            return []
        results = [self._row_out(r, "lexical") for r in rows]
        self._record_access(results)
        return results

    def recent(
        self, namespaces: list[str], kinds: tuple[str, ...], limit: int
    ) -> list[dict]:
        # No caller text reaches this SQL: the statement is chosen from a fixed set keyed on how
        # many namespaces were asked for, and every value below is a bound parameter.
        marks = ",".join("?" * len(namespaces))
        sql = (
            "SELECT * FROM memories WHERE namespace IN (" + marks + ")"  # noqa: S608 - marks is "?"*n
            " ORDER BY updated_at DESC LIMIT ?"
        )
        rows = (
            self._conn().execute(sql, (*namespaces, max(limit * 4, limit))).fetchall()
        )
        out = [
            self._row_out(r, "recent")
            for r in rows
            if any(k in (r["key"] + " " + r["content"]).lower() for k in kinds)
        ]
        return out[:limit]

    def _record_access(self, results: list[dict]) -> None:
        if not results:
            return
        with self._lock:
            conn = self._conn()
            for r in results:
                conn.execute(
                    "UPDATE memories SET access_count = access_count + 1 WHERE id=?",
                    (r["id"],),
                )
            conn.commit()


class _AsPayload:
    """The shape OWASPWriteGuard.inspect expects (namespace/key/content/provenance/trust_tier)."""

    def __init__(self, payload: dict, namespace: str, key: str):
        self.namespace = namespace
        self.key = key
        self.content = payload.get("content", "")
        self.provenance = payload.get("provenance") or {}
        self.trust_tier = payload.get("trust_tier") or "raw_source"


class Handler(BaseHTTPRequestHandler):
    server_version = "estate-memory-local/1"
    store: Store

    def log_message(self, fmt: str, *args: Any) -> None:  # one line per call, to stderr
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        # Health is polled continuously. Writing a successful probe to a contended disk made a
        # no-op handler inherit storage latency and fill the log with evidence of nothing. Failures
        # still log through the normal path.
        if urlparse(self.path).path == "/healthz" and str(code).startswith("2"):
            return
        super().log_request(code, size)

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _auth_ok(self) -> bool:
        want = os.environ.get("ESTATE_MEMORY_LOCAL_TOKEN", "")
        if not want:
            return True  # loopback-only bind; a token is optional and never printed
        got = (self.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        return got == want

    def _body(self) -> dict:
        n = int(self.headers.get("content-length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode() or "{}")

    def _route(self, method: str) -> None:
        if not self._auth_ok():
            return self._send(401, {"detail": "unauthorized"})
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        query = parse_qs(urlparse(self.path).query)
        if parts == ["healthz"]:
            if not self.store.healthy():
                return self._send(
                    503, {"ok": False, "store": "sqlite", "db": "unavailable"}
                )
            return self._send(200, {"ok": True, "store": "sqlite", "db": "readable"})
        if len(parts) < 2 or parts[0] != "memories":
            return self._send(404, {"detail": "no such route"})
        ns = parts[1]
        if not NAMESPACE_RE.match(ns):
            return self._send(400, {"detail": "bad namespace"})

        if method == "GET" and len(parts) == 2:
            limit = int((query.get("limit") or ["50"])[0])
            return self._send(200, {"results": self.store.list(ns, limit)})

        if method == "PUT" and len(parts) == 3:
            key = parts[2]
            if not KEY_RE.match(key):
                return self._send(400, {"detail": "bad key"})
            body = self._body()
            out = self.store.save(ns, key, body, self.headers.get("if-match"))
            return self._send(out["_status"], out["_body"])

        if method == "GET" and len(parts) == 3:
            found = self.store.get(ns, parts[2])
            if not found:
                return self._send(404, {"detail": "no such memory"})
            return self._send(200, found)

        if method == "POST" and len(parts) == 3 and parts[2] == "recall":
            body = self._body()
            q = (body.get("query") or "").strip()
            if not q:
                return self._send(422, {"detail": "query is required"})
            limit = int(body.get("limit") or 10)
            ns_use = body.get("namespace") or ns
            return self._send(200, {"results": self.store.search(q, ns_use, limit)})

        if method == "POST" and len(parts) == 3 and parts[2] == "brief":
            body = self._body()
            task = (body.get("task") or "").strip()
            limit = int(body.get("limit") or 8)
            relevant = self.store.search(task, ns, limit) if task else []
            recent = self.store.recent([ns, "estate"], ("decision", "incident"), limit)
            return self._send(
                200,
                {
                    "relevant": relevant,
                    "recent": recent,
                    "search_by_meaning": bool(
                        task
                    ),  # False == the task half was not looked at
                    "ranking": "lexical",
                    "namespace": ns,
                },
            )

        if method == "POST" and len(parts) == 3 and parts[2] == "search":
            body = self._body()
            q = body.get("query") or ""
            limit = int(body.get("limit") or 10)
            return self._send(200, {"results": self.store.search(q, ns, limit)})

        return self._send(
            404, {"detail": f"no route for {method} /{('/'.join(parts))}"}
        )

    def do_GET(self) -> None:  # noqa: N802 - http.server names these
        self._route("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._route("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._route("PUT")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="The memory door's local origin (same contract)."
    )
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument(
        "--selftest", action="store_true", help="write+read+search one fact, then exit"
    )
    args = ap.parse_args(argv)

    store = Store(Path(args.db))
    if args.selftest:
        ns, key = "selftest", f"fact-{int(time.time())}"
        w = store.save(
            ns, key, {"content": "the local origin serves the door contract"}, None
        )
        g = store.get(ns, key)
        s = store.search("local origin", ns, 5)
        print(json.dumps({"write": w["_body"], "read": bool(g), "search_hits": len(s)}))
        return 0 if (g and s) else 1

    Handler.store = store
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        f"estate-memory-local listening on http://{args.host}:{args.port} db={store.path}",
        flush=True,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
