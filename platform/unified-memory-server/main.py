import os
import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, status
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from security_core import (
    OWASPWriteGuard,
    MAPLEGuard,
    MemoryWritePayload,
    SecurityViolationException,
)


def _secret(name: str) -> Optional[str]:
    """NAME_FILE (a mounted Secret) wins over NAME: on the cluster a secret is a file, never an
    env var (Kyverno secrets-not-from-env-vars); NAME stays for local runs and tests."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        with open(path) as f:
            return f.read().strip()
    return os.environ.get(name)


# LAW 4: secrets by name only, from the vault. No literal password in source.
DATABASE_URL = _secret("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL (or DATABASE_URL_FILE) is required")
# The estate's own surface token (vault entry unified-memory, key surface-token). Registered at
# boot as tenant `estate`, surface `estate-agents`: without it no tenant and no token exist, and
# the only way to make one would be a person typing an INSERT into the production database.
SURFACE_TOKEN = _secret("MEMORY_SURFACE_TOKEN")
# Requests per token per minute. An agent that reads its memory at the start of a task and
# writes a handful of facts stays far under it; a loop does not.
RATE_LIMIT_PER_MINUTE = 30
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# A write may say when its fact became true, but not later than this past the server's own
# clock: one surface with a fast clock would otherwise pin a key's current value until its
# clock is reached, and every honest write in between would be filed as history.
MAX_VALID_FROM_SKEW = timedelta(seconds=60)

# ---------------------------------------------------------------------
# Lifespan: Bounded AsyncConnectionPool with Connection Checks & Locks
# ---------------------------------------------------------------------
pool: Optional[AsyncConnectionPool] = None


async def _drop_to_app_role(conn) -> None:
    # Every request runs as memory_app: the connecting role owns the tables (or, in a local
    # run, is a superuser, which bypasses row-level security), so it never serves a request.
    await conn.execute("SET ROLE memory_app;")
    await conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    # Schema migration, before any request connection exists. Every pod runs it, one at a
    # time under a blocking transaction-scoped advisory lock (0x2100A4); schema.sql is
    # re-runnable, so the second pod's pass is a no-op instead of a pod that serves before
    # the schema exists (the old try-lock let non-leaders skip straight to serving).
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_advisory_xact_lock(2162852);")
            with open(SCHEMA_PATH, "r") as f:
                await cur.execute(f.read())
            if SURFACE_TOKEN:
                await cur.execute(
                    "INSERT INTO tenants(name) VALUES ('estate') ON CONFLICT (name) DO NOTHING;"
                )
                await cur.execute(
                    """
                    INSERT INTO surface_tokens(tenant_id, surface_name, token_hash)
                    SELECT tenant_id, 'estate-agents', %s FROM tenants WHERE name = 'estate'
                    ON CONFLICT (token_hash) DO NOTHING;
                    """,
                    (hashlib.sha256(SURFACE_TOKEN.encode("utf-8")).hexdigest(),),
                )
        await conn.commit()

    # Bounded pool with active connection validation and TCP keepalive
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=4,
        max_size=32,
        timeout=10.0,
        check=AsyncConnectionPool.check_connection,
        configure=_drop_to_app_role,
        kwargs={
            "autocommit": False,
            "row_factory": dict_row,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )
    await pool.open()

    yield

    if pool:
        await pool.close()


app = FastAPI(title="Unified Model-Agnostic Agentic Memory Server", lifespan=lifespan)


# ---------------------------------------------------------------------
# Dependencies: Surface-Isolated Authentication & Connection Injection
# ---------------------------------------------------------------------
async def get_db_conn():
    async with pool.connection() as conn:
        yield conn


async def authenticate_surface(
    request: Request,
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    token_query: Optional[str] = Query(None, alias="token"),
) -> Dict[str, Any]:
    raw_token = None
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ", 1)[1].strip()
    elif token_query:
        raw_token = token_query.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: No surface bearer token or query parameter provided",
        )

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    async with conn.cursor() as cur:
        window = int(time.time() // 60)
        await cur.execute(
            "SELECT fn_hit_rate_limit(%s, %s, %s);",
            (token_hash, window, RATE_LIMIT_PER_MINUTE),
        )
        allowed = (await cur.fetchone())["fn_hit_rate_limit"]
        # Committed before anything can refuse the request: a 429 or a 403 raised below rolls
        # the connection back, and the hit it rolled back was never counted.
        await conn.commit()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # Verify token and resolve tenant mapping
        await cur.execute(
            """
            SELECT tenant_id, surface_name
            FROM surface_tokens
            WHERE token_hash = %s AND revoked_at IS NULL;
            """,
            (token_hash,),
        )
        record = await cur.fetchone()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access token invalid or revoked",
            )

        # Set transaction-local RLS parameter
        tenant_id = str(record["tenant_id"])
        await cur.execute("SELECT set_config('app.tenant_id', %s, true);", (tenant_id,))
        return {"tenant_id": tenant_id, "surface": record["surface_name"]}


# ---------------------------------------------------------------------
# Endpoints: Stateless HTTP Transport Layer (SEP-2575)
# ---------------------------------------------------------------------


@app.put("/memories/{namespace}/{key}", status_code=status.HTTP_200_OK)
async def memory_save(
    namespace: str,
    key: str,
    payload: MemoryWritePayload,
    request: Request,
    if_match: Optional[str] = Header(None, alias="If-Match"),
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    payload.namespace = namespace
    payload.key = key

    # 1. OWASP Write-Time Pipeline Check
    try:
        content_hash = OWASPWriteGuard.inspect(payload)
    except SecurityViolationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": e.code, "error": e.message},
        ) from e

    # 2. Parse Expected Version for Concurrency
    expected_version = None
    if if_match:
        try:
            expected_version = int(if_match.strip('"'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid If-Match header value",
            ) from e
    elif payload.expected_version is not None:
        expected_version = payload.expected_version

    # 3. Valid time: when the fact became true. Defaults to now; never meaningfully ahead.
    now = datetime.now(timezone.utc)
    valid_from = payload.valid_from or now
    if valid_from.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="valid_from must carry a timezone offset",
        )
    if valid_from > now + MAX_VALID_FROM_SKEW:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "VALID_FROM_IN_FUTURE",
                "valid_from": valid_from.isoformat(),
                "server_time": now.isoformat(),
            },
        )

    async with conn.transaction():
        async with conn.cursor() as cur:
            # Check existing record state
            await cur.execute(
                """
                SELECT id, version, trust_tier, valid_from
                FROM memories
                WHERE namespace = %s AND key = %s
                FOR UPDATE;
                """,
                (namespace, key),
            )
            existing = await cur.fetchone()

            if existing:
                current_version = existing["version"]
                # 3. Optimistic Concurrency Arbitration
                if expected_version is not None and current_version != expected_version:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "VERSION_DRIFT_DETECTED",
                            "current_version": current_version,
                            "provided_version": expected_version,
                        },
                    )

                # Write-time gate: Protect immutable human assertions
                if (
                    existing["trust_tier"] == "human_confirmed"
                    and payload.trust_tier != "human_confirmed"
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="ANTI_OUROBOROS: An automated agent cannot overwrite human_confirmed memory",
                    )

                # Late write: the fact became true before the current one did. It belongs
                # in history, and the current value stays what it is.
                if valid_from < existing["valid_from"]:
                    await cur.execute(
                        """
                        INSERT INTO memory_versions (
                            memory_id, tenant_id, namespace, key, content, content_hash,
                            trust_tier, provenance, valid_from
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            existing["id"],
                            auth["tenant_id"],
                            namespace,
                            key,
                            payload.content,
                            content_hash,
                            payload.trust_tier,
                            Jsonb(payload.provenance),
                            valid_from,
                        ),
                    )
                    return {
                        "status": "RECORDED_AS_PAST",
                        "id": str(existing["id"]),
                        "version": current_version,
                    }

                # Update row: monotonic trigger automatically increments the version counter;
                # the history trigger files the new version in memory_versions.
                await cur.execute(
                    """
                    UPDATE memories SET
                        content = %s,
                        content_hash = %s,
                        trust_tier = %s,
                        provenance = %s,
                        valid_from = %s
                    WHERE id = %s
                    RETURNING id, version;
                    """,
                    (
                        payload.content,
                        content_hash,
                        payload.trust_tier,
                        Jsonb(payload.provenance),
                        valid_from,
                        existing["id"],
                    ),
                )
                updated = await cur.fetchone()
                return {
                    "status": "UPDATED",
                    "id": str(updated["id"]),
                    "version": updated["version"],
                }

            else:
                # Insert fresh record
                await cur.execute(
                    """
                    INSERT INTO memories (
                        tenant_id, namespace, key, content, content_hash, trust_tier, provenance,
                        valid_from
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, version;
                    """,
                    (
                        auth["tenant_id"],
                        namespace,
                        key,
                        payload.content,
                        content_hash,
                        payload.trust_tier,
                        Jsonb(payload.provenance),
                        valid_from,
                    ),
                )
                inserted = await cur.fetchone()
                return {
                    "status": "CREATED",
                    "id": str(inserted["id"]),
                    "version": inserted["version"],
                }


@app.post("/memories/search", status_code=status.HTTP_200_OK)
async def memory_search(
    query_vector: List[float],
    namespace: str = "default",
    limit: int = 10,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    if len(query_vector) != 1536:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dimension mismatch: vector must be 1536d",
        )

    async with conn.cursor() as cur:
        # Enforce Production HNSW Recall Configuration
        await cur.execute("SET LOCAL hnsw.ef_search = 100;")
        await cur.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order';")

        # Query candidates from pgvector
        query_vector_str = "[" + ",".join(map(str, query_vector)) + "]"
        await cur.execute(
            """
            SELECT
                id, namespace, key, content, trust_tier, version,
                relevance_rho, truthfulness_tau, harm_h, taint_level, scope_risk,
                1 - (embedding <=> %s::vector) AS cosine_sim
            FROM memories
            WHERE namespace = %s AND is_quarantined = FALSE
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (query_vector_str, namespace, query_vector_str, limit * 2),
        )
        candidates = await cur.fetchall()

        # Execute MAPLE-Guard Lifecycle Retrieval Ranking
        scored_results = []
        for c in candidates:
            sim = c["cosine_sim"] or 0.0
            conditional_risk = 0.0  # Evaluated by agent query context
            final_score = MAPLEGuard.calculate_retrieval_score(
                cosine_sim=sim,
                rho=c["relevance_rho"],
                tau=c["truthfulness_tau"],
                h=c["harm_h"],
                taint=c["taint_level"],
                scope=c["scope_risk"],
                conditional_risk=conditional_risk,
            )

            # Check for retrieval-gate failure
            if final_score > 0.35:  # Gate acceptance cutoff
                scored_results.append(
                    {
                        "id": str(c["id"]),
                        "key": c["key"],
                        "content": c["content"],
                        "trust_tier": c["trust_tier"],
                        "version": c["version"],
                        "maple_score": round(final_score, 4),
                        "cosine_sim": round(sim, 4),
                    }
                )

        # Re-sort based on the multi-factor MAPLE equation and truncate to requested limit
        scored_results.sort(key=lambda x: x["maple_score"], reverse=True)
        return {"results": scored_results[:limit]}


# ---------------------------------------------------------------------
# Bi-temporal reads: what was true when, and what we knew when
# ---------------------------------------------------------------------


@app.get("/memories/{namespace}", status_code=status.HTTP_200_OK)
async def memory_list_current(
    namespace: str,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    # Every current fact in a namespace: a namespace is a subject, its keys its predicates.
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT key, content, trust_tier, version, valid_from, updated_at, provenance
            FROM memories
            WHERE namespace = %s AND is_quarantined = FALSE
            ORDER BY key;
            """,
            (namespace,),
        )
        rows = await cur.fetchall()
    return {
        "namespace": namespace,
        "facts": [
            {
                "key": r["key"],
                "content": r["content"],
                "trust_tier": r["trust_tier"],
                "version": r["version"],
                "valid_from": r["valid_from"].isoformat(),
                "recorded_at": r["updated_at"].isoformat(),
                # What the writer said about the fact (subject, kind, tags, source): the fields a
                # reader filters on, returned so it never has to guess them from the key.
                "provenance": r["provenance"],
            }
            for r in rows
        ],
    }


@app.get("/memories/{namespace}/{key}", status_code=status.HTTP_200_OK)
async def memory_read(
    namespace: str,
    key: str,
    as_of: Optional[datetime] = None,
    known_at: Optional[datetime] = None,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    # as_of: what was true at that moment. known_at: as this server knew it at that moment.
    # Both default to now. The version that answers is the one with the latest valid_from at
    # or before as_of, among versions recorded at or before known_at; a tie on valid_from goes
    # to the later recording, the same rule memory_save uses to pick the current value.
    now = datetime.now(timezone.utc)
    for name, value in (("as_of", as_of), ("known_at", known_at)):
        if value is not None and value.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{name} must carry a timezone offset",
            )
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT v.content, v.content_hash, v.trust_tier, v.valid_from, v.recorded_at
            FROM memory_versions v
            JOIN memories m ON m.id = v.memory_id
            WHERE v.namespace = %s AND v.key = %s AND m.is_quarantined = FALSE
              AND v.valid_from <= %s AND v.recorded_at <= %s
            ORDER BY v.valid_from DESC, v.recorded_at DESC, v.version_id DESC
            LIMIT 1;
            """,
            (namespace, key, as_of or now, known_at or now),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No version of this memory was true at as_of, as known at known_at",
        )
    return {
        "namespace": namespace,
        "key": key,
        "content": row["content"],
        "content_hash": row["content_hash"],
        "trust_tier": row["trust_tier"],
        "valid_from": row["valid_from"].isoformat(),
        "recorded_at": row["recorded_at"].isoformat(),
    }


@app.get("/memories/{namespace}/{key}/history", status_code=status.HTTP_200_OK)
async def memory_history(
    namespace: str,
    key: str,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT content, content_hash, trust_tier, provenance, valid_from, recorded_at
            FROM memory_versions
            WHERE namespace = %s AND key = %s
            ORDER BY valid_from, recorded_at, version_id;
            """,
            (namespace, key),
        )
        rows = await cur.fetchall()
    return {
        "namespace": namespace,
        "key": key,
        "versions": [
            {
                "content": r["content"],
                "content_hash": r["content_hash"],
                "trust_tier": r["trust_tier"],
                "provenance": r["provenance"],
                "valid_from": r["valid_from"].isoformat(),
                "recorded_at": r["recorded_at"].isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/digest/{namespace}", status_code=status.HTTP_200_OK)
async def memory_digest(
    namespace: str,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    # One hash of a namespace's current state. It depends on the set of (key, content_hash)
    # pairs and not on the order they were written, so two copies holding the same facts
    # (a replica, a restore) agree, and any difference in any fact changes it. Each key is
    # length-prefixed so no key can be spelled to collide with a neighbour.
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT count(*) AS facts,
                   encode(sha256(convert_to(coalesce(string_agg(
                       length(key)::text || ':' || key || content_hash, E'\\n' ORDER BY key COLLATE "C"
                   ), ''), 'UTF8')), 'hex') AS digest
            FROM memories
            WHERE namespace = %s;
            """,
            (namespace,),
        )
        row = await cur.fetchone()
    return {"namespace": namespace, "facts": row["facts"], "digest": row["digest"]}
