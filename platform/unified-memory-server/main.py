import asyncio
import logging
import os
import json
import hashlib
import time
import urllib.request
import urllib.error
import urllib.parse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Header,
    Query,
    Request,
    Response,
    status,
)
from pydantic import BaseModel, Field
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

import hedge
import ranking
from security_core import (
    OWASPWriteGuard,
    MAPLEGuard,
    MemoryWritePayload,
    SecurityViolationException,
)

from harness import (
    ActiveMemoryEngine,
    ApprovalWebhookHandler,
    ExtractedFactCandidate,
    HarnessTelemetry,
    PostgresApprovalStore,
    PostgresCortexAdapter,
    PostgresScratchpadStore,
)

# Singleton telemetry instance — one per server process.
_harness_telemetry = HarnessTelemetry()
_approval_handler: ApprovalWebhookHandler | None = None


def _get_approval_handler() -> ApprovalWebhookHandler:
    global _approval_handler
    if _approval_handler is None:
        signing_secret = (
            _secret("HARNESS_APPROVAL_WEBHOOK_SECRET") or "insecure-dev-secret"
        )
        _approval_handler = ApprovalWebhookHandler(
            signing_secret=signing_secret,
            approval_store=PostgresApprovalStore(),
            telemetry=_harness_telemetry,
        )
    return _approval_handler


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
# Embeddings: the vector is written by the server, never by the client.
# ---------------------------------------------------------------------
# Until 2026-10-02 this store ranked by `embedding <=> %s::vector` while no code anywhere
# wrote that column: every row landed with embedding NULL, so recall found nothing and facts
# were write-only (47 rows, 0 vectors, measured). The vector is computed HERE, in the one
# place every caller passes through, rather than in each client (`do_remember` and
# `otto/memory` and every future caller) where the next client to forget would reintroduce
# the bug. It goes through the estate router's existing `embed` lane -- one model, one
# dimension (1536, matching schema.sql's vector(1536) and the HNSW index on it).
EMBED_URL = _secret("MEMORY_EMBED_URL")
EMBED_MODEL = os.environ.get("MEMORY_EMBED_MODEL", "embed")
# The lane a recall QUERY is embedded with: the same model and width as EMBED_MODEL, asked as a
# question rather than a passage. The model is asymmetric, and the same query typed passage vs
# query ranked the stored facts differently on the live lane (2026-10-13, see embed-query in
# platform/vendors/consoles.yaml). Facts are never embedded with this lane: a passage vector is
# what a query is compared against.
EMBED_QUERY_MODEL = os.environ.get("MEMORY_EMBED_QUERY_MODEL", "embed-query")
# 1536: the width the column is created at, and the width the router's `embed` lane is
# configured to return (platform/llm/config.yaml, nvidia llama-nemotron-embed-vl-1b-v2 with
# dimensions: 1536, measured 2026-10-09). A default nobody chose is an accident, so it is
# written here and checked on every vector below: a vector of another width is refused, not
# stored.
EMBED_DIM = int(os.environ.get("MEMORY_EMBED_DIM", "1536"))
# Bounded well inside the request path: a store that hangs on its own embedding call is worse
# than one that stores the fact unembedded, because the caller cannot even write the fact.
EMBED_TIMEOUT_S = float(os.environ.get("MEMORY_EMBED_TIMEOUT_S", "20"))
# The brief's task embed is hedged, not waited on (hedge.py has the measurement: the NIM lane
# drops about half its requests without a reply). A brief is read on the way INTO a model call
# -- the router's Active Memory callback gives it 1.5 s -- so its embed gets BRIEF_EMBED_DEADLINE_S
# across BRIEF_EMBED_ATTEMPTS staggered tries, and a miss returns the recent half in about a
# second instead of 20. Stores keep EMBED_TIMEOUT_S: a write is not on anyone's critical path.
BRIEF_EMBED_DEADLINE_S = float(os.environ.get("MEMORY_BRIEF_EMBED_DEADLINE_S", "1.0"))
BRIEF_EMBED_ATTEMPTS = int(os.environ.get("MEMORY_BRIEF_EMBED_ATTEMPTS", "3"))
BRIEF_EMBED_HEDGE_S = float(os.environ.get("MEMORY_BRIEF_EMBED_HEDGE_S", "0.3"))
# The floor under /memories/recall: the least cosine similarity a fact may have to be returned.
# MAPLE's retrieval gate cannot be that floor. Its score is sim + 0.3*rho + 0.4*tau - penalties,
# so with the defaults (rho = tau = 1, no penalties) a fact scores sim + 0.7 and the gate
# (> 0.35) refuses only sim < -0.35: every fact with a vector passes, however unrelated, and
# recall would return the nearest N facts whether or not any is near. 0.2 is a starting value
# NOT yet measured against the live lane (no related/unrelated pairs have been embedded and
# compared); calibrate it from real pairs and set MEMORY_RECALL_MIN_COSINE, don't trust it.
RECALL_MIN_COSINE = float(os.environ.get("MEMORY_RECALL_MIN_COSINE", "0.2"))


def _embed(
    text: str, model: Optional[str] = None, timeout: Optional[float] = None
) -> Optional[List[float]]:
    """The EMBED_DIM-wide vector for `text`, or None if the lane is unreachable.

    `model` is the router lane; EMBED_MODEL (a fact, as a passage) unless the caller is
    embedding a search query, which passes EMBED_QUERY_MODEL. `timeout` defaults to
    EMBED_TIMEOUT_S; a hedged caller passes what is left of its own deadline.

    None is not an error the caller raises: a fact whose vector could not be computed is
    still a fact worth keeping (the write must not fail because a model was briefly down),
    but it must be VISIBLE as unvectorised rather than silent -- `vector_status` reports it,
    the backfill re-embeds it, and /embeddings/status counts it. The old failure was not that
    vectors were missing; it was that nothing could tell.
    """
    if not EMBED_URL:
        return None
    url = EMBED_URL.rstrip("/") + "/embeddings"
    # S310: urlopen accepts file:// and other schemes, so a MEMORY_EMBED_URL that arrived
    # from a misconfigured Secret would be read as a local file rather than a request -- and
    # ``file:`` on the embedding path means a stray filesystem read dressed up as a model
    # call. The lane is the estate router and nothing else; http(s) is the whole of what this
    # may be, and the refusal is explicit rather than implied by a comment (AGENTS.md 23,
    # boundary enforced by infrastructure, not the application -- here the application is all
    # that stands between the Secret and the read).
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme not in ("http", "https"):
        # Silent like every other refusal in this function: the caller sees None, the fact is
        # still stored, and `vector_status` counts it. A refused scheme is therefore visible
        # as unvectorised rather than as a warning nobody reads.
        return None
    body = json.dumps({"model": model or EMBED_MODEL, "input": text}).encode("utf-8")
    # The scheme is validated above, so this is the one shape urlopen is allowed to see.
    req = urllib.request.Request(  # noqa: S310
        url,
        data=body,
        headers={
            "authorization": "Bearer " + (_secret("MEMORY_EMBED_API_KEY") or ""),
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout or EMBED_TIMEOUT_S) as resp:  # noqa: S310
            vec = json.loads(resp.read())["data"][0]["embedding"]
    except (urllib.error.URLError, KeyError, IndexError, ValueError, OSError):
        return None
    if len(vec) != EMBED_DIM:
        # A dimension mismatch is not a vector for this column: it would be silently
        # truncated or rejected by pgvector, and either way the row is a lie.
        return None
    return vec


def _vector_literal(vec: Optional[List[float]]) -> Optional[str]:
    """pgvector's text input form, or None to store SQL NULL when no vector was computed."""
    if vec is None:
        return None
    return "[" + ",".join(map(str, vec)) + "]"


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
        # autocommit=False means every statement opens an implicit transaction that stays open
        # until an explicit commit; authenticate_surface commits once after rate limiting, then
        # its tenant SELECT opens a fresh one, so a handler's `async with conn.transaction()`
        # is only a savepoint inside that. psycopg_pool rolls the connection back on release,
        # which silently discarded every write while the handler still returned 200 CREATED
        # (verified in production 2026-10-18: PUT -> CREATED, row count 0). Commit what the
        # request left open; if an exception aborted the transaction this is a rollback, which
        # is exactly what a failed request should do.
        await conn.commit()


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
            # Computed once, outside the row-state branch, because all three write paths (fresh
            # insert, update, late-write history) carry the same content and therefore the same
            # vector. One HTTP call per write, not zero (the old bug) and not three.
            vec = _vector_literal(_embed(payload.content))

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
                        valid_from = %s,
                        embedding = %s
                    WHERE id = %s
                    RETURNING id, version;
                    """,
                    (
                        payload.content,
                        content_hash,
                        payload.trust_tier,
                        Jsonb(payload.provenance),
                        valid_from,
                        vec,
                        existing["id"],
                    ),
                )
                updated = await cur.fetchone()
                return {
                    "status": "UPDATED",
                    "id": str(updated["id"]),
                    "version": updated["version"],
                    "search_by_meaning": vec is not None,
                }

            else:
                # Insert fresh record
                await cur.execute(
                    """
                    INSERT INTO memories (
                        tenant_id, namespace, key, content, content_hash, trust_tier, provenance,
                        valid_from, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        vec,
                    ),
                )
                inserted = await cur.fetchone()
                return {
                    "status": "CREATED",
                    "id": str(inserted["id"]),
                    "version": inserted["version"],
                    "search_by_meaning": vec is not None,
                }


async def _ranked(
    cur,
    query_vector: List[float],
    namespace: str,
    limit: int,
    min_cosine: Optional[float] = None,
) -> list:
    """The MAPLE-Guard-ranked facts nearest `query_vector` in `namespace`, best first.

    Rows with no vector are not candidates: `embedding <=> q` on NULL ranks them nowhere, and
    counting them would only spend the candidate window on facts that cannot match by meaning.
    """
    # Enforce Production HNSW Recall Configuration
    await cur.execute("SET LOCAL hnsw.ef_search = 100;")
    # pgvector < 0.8 has no iterative scan, and once its library is loaded in a backend the
    # unknown setting is refused; a savepoint keeps that refusal from aborting the search.
    try:
        async with cur.connection.transaction():
            await cur.execute("SET LOCAL hnsw.iterative_scan = 'relaxed_order';")
    except psycopg.errors.InvalidName:
        pass

    # Query candidates from pgvector
    query_vector_str = "[" + ",".join(map(str, query_vector)) + "]"
    await cur.execute(
        """
        SELECT
            id, namespace, key, content, trust_tier, version, provenance, updated_at,
            relevance_rho, truthfulness_tau, harm_h, taint_level, scope_risk,
            1 - (embedding <=> %s::vector) AS cosine_sim,
            COALESCE((SELECT a.access_count FROM memory_access a
                      WHERE a.memory_id = memories.id), 0) AS access_count
        FROM memories
        WHERE namespace = %s AND is_quarantined = FALSE AND embedding IS NOT NULL
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
        if min_cosine is not None and sim < min_cosine:
            continue
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
                    "provenance": c["provenance"],
                    "recorded_at": c["updated_at"].isoformat(),
                    "maple_score": round(final_score, 4),
                    "cosine_sim": round(sim, 4),
                    "access_count": c["access_count"],
                }
            )

    # Order what the gate admitted by MAPLE score plus recency and frequency (ranking.py). The
    # boost orders; it never admits, because the gate above ran on the unboosted score.
    return ranking.rank(scored_results)[:limit]


async def _record_access(cur, results: list) -> None:
    """Count one retrieval for each returned fact (ranking.py's frequency term).

    Best effort: a failure here must never cost the caller the answer it already has, so it runs
    in a savepoint and is swallowed. The tenant comes from the memory row (RLS has already
    filtered to the caller's), so no tenant id is threaded through the ranking call.
    """
    ids = [r["id"] for r in results if r.get("id")]
    if not ids:
        return
    try:
        async with cur.connection.transaction():
            await cur.execute(
                """
                INSERT INTO memory_access (memory_id, tenant_id, access_count, last_accessed_at)
                SELECT id, tenant_id, 1, CURRENT_TIMESTAMP FROM memories WHERE id = ANY(%s::uuid[])
                ON CONFLICT (memory_id) DO UPDATE
                SET access_count = memory_access.access_count + 1,
                    last_accessed_at = CURRENT_TIMESTAMP;
                """,
                (ids,),
            )
    except Exception:  # noqa: BLE001 -- reinforcement is never worth failing a recall
        logging.getLogger(__name__).warning(
            "recall reinforcement skipped", exc_info=True
        )


@app.post("/memories/search", status_code=status.HTTP_200_OK)
async def memory_search(
    query_vector: List[float],
    namespace: str = "default",
    limit: int = 10,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    if len(query_vector) != EMBED_DIM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dimension mismatch: vector must be {EMBED_DIM}d",
        )

    async with conn.cursor() as cur:
        return {"results": await _ranked(cur, query_vector, namespace, limit)}


class RecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    namespace: str = "default"
    limit: int = Field(default=10, ge=1, le=50)


@app.post("/memories/recall", status_code=status.HTTP_200_OK)
async def memory_recall(
    payload: RecallRequest,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    """Search by meaning from text: the server embeds the query with the same lane and width
    it embeds facts with, so no client ever holds a vector and none can embed with the wrong
    model. When the lane cannot answer this is a 503, not an empty list: 'nothing matches' and
    'could not look' are different answers and the caller falls back differently on each."""
    # urllib blocks; off the event loop so one slow embed call does not stall every request.
    vec = await asyncio.to_thread(_embed, payload.query, EMBED_QUERY_MODEL)
    if vec is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="embed lane unavailable: cannot search by meaning right now",
        )
    async with conn.cursor() as cur:
        results = await _ranked(
            cur, vec, payload.namespace, payload.limit, RECALL_MIN_COSINE
        )
        await _record_access(cur, results)
        return {"results": results}


# The kinds a session should hear about whatever its task: what was decided, and what broke.
BRIEF_RECENT_KINDS = ("decision", "incident")


class BriefRequest(BaseModel):
    task: str = Field(default="", max_length=8000)
    namespace: str = "default"
    limit: int = Field(default=8, ge=1, le=30)


@app.post("/memories/brief", status_code=status.HTTP_200_OK)
async def memory_brief(
    payload: BriefRequest,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    """What a session should know before it starts: the facts nearest its task, and the
    newest decisions and incidents. Unlike recall this never 503s on a down lane -- a session
    start waits on it, and the recent half needs no vector -- so `search_by_meaning` says
    whether the task half was answered at all."""
    relevant: list = []
    vec = None
    if payload.task.strip():
        vec = await asyncio.to_thread(
            hedge.first_answer,
            lambda left: _embed(payload.task, EMBED_QUERY_MODEL, timeout=left),
            BRIEF_EMBED_ATTEMPTS,
            BRIEF_EMBED_HEDGE_S,
            BRIEF_EMBED_DEADLINE_S,
        )
    async with conn.cursor() as cur:
        if vec is not None:
            relevant = await _ranked(
                cur, vec, payload.namespace, payload.limit, RECALL_MIN_COSINE
            )
            await _record_access(cur, relevant)
        seen = [r["key"] for r in relevant]
        await cur.execute(
            """
            SELECT key, content, trust_tier, version, provenance, updated_at
            FROM memories
            WHERE namespace = %s AND is_quarantined = FALSE
              AND provenance->>'kind' = ANY(%s) AND NOT (key = ANY(%s))
            ORDER BY valid_from DESC, updated_at DESC
            LIMIT %s;
            """,
            (payload.namespace, list(BRIEF_RECENT_KINDS), seen, payload.limit),
        )
        recent = [
            {
                "key": r["key"],
                "content": r["content"],
                "trust_tier": r["trust_tier"],
                "version": r["version"],
                "provenance": r["provenance"],
                "recorded_at": r["updated_at"].isoformat(),
            }
            for r in await cur.fetchall()
        ]
    return {
        "namespace": payload.namespace,
        "relevant": relevant,
        "recent": recent,
        "search_by_meaning": vec is not None,
    }


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


@app.get("/embeddings/status", status_code=status.HTTP_200_OK)
async def embeddings_status(
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    # The number that was missing on 2026-10-02. The store held 47 facts and 0 vectors and
    # every probe still said healthy, because nothing counted the gap between the two. This
    # endpoint makes the gap a number any caller, gate or alert can read, so 'stored but not
    # searchable' can never again be invisible. unvectorised > 0 with the lane configured is
    # the exact signature of the write-path regression this change fixes.
    async with conn.cursor() as cur:
        # `embedding` is the column a recall actually searches, so this counts that one:
        # the number that must not lie.
        await cur.execute(
            """
            SELECT count(*) AS facts,
                   count(embedding) AS vectorised,
                   count(*) - count(embedding) AS unvectorised
            FROM memories;
            """
        )
        row = await cur.fetchone()
    return {
        "facts": row["facts"],
        "vectorised": row["vectorised"],
        "unvectorised": row["unvectorised"],
        "embed_lane_configured": bool(EMBED_URL),
        "embed_model": EMBED_MODEL,
        "embed_query_model": EMBED_QUERY_MODEL,
        "embed_dim": EMBED_DIM,
    }


# One call embeds at most this many facts: each is a network round trip to the lane, and the
# request must finish inside the caller's door. Repeat the call until `remaining` is 0.
BACKFILL_MAX_BATCH = 25
BACKFILL_BUDGET_S = 40.0


@app.post("/embeddings/backfill", status_code=status.HTTP_200_OK)
async def embeddings_backfill(
    limit: int = Query(10, ge=1, le=BACKFILL_MAX_BATCH),
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008 — FastAPI DI
    conn=Depends(get_db_conn),  # noqa: B008 — FastAPI DI: Depends() in a default IS the API
):
    """Embed facts that were stored without a vector (the 47 of 2026-10-02, and any written
    while the lane was down). Only the caller's own tenant's rows are visible (row-level
    security), so this can never touch another tenant's facts. A fact whose content changed
    while its vector was being computed is left alone: the write that changed it embeds it."""
    if not EMBED_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="embed lane not configured: nothing to backfill with",
        )
    deadline = time.monotonic() + BACKFILL_BUDGET_S
    embedded = failed = 0
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, content FROM memories
            WHERE embedding IS NULL AND is_quarantined = FALSE
            ORDER BY created_at
            LIMIT %s;
            """,
            (limit,),
        )
        todo = await cur.fetchall()
        for row in todo:
            if time.monotonic() > deadline:
                break
            vec = await asyncio.to_thread(_embed, row["content"])
            if vec is None:
                failed += 1
                continue
            await cur.execute(
                """
                UPDATE memories SET embedding = %s::vector
                WHERE id = %s AND content = %s AND embedding IS NULL;
                """,
                (_vector_literal(vec), row["id"], row["content"]),
            )
            embedded += cur.rowcount
        await cur.execute(
            "SELECT count(*) AS remaining FROM memories "
            "WHERE embedding IS NULL AND is_quarantined = FALSE;"
        )
        remaining = (await cur.fetchone())["remaining"]
    return {"embedded": embedded, "failed": failed, "remaining": remaining}


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


# ---------------------------------------------------------------------
# Active Runtime Harness Endpoints
# ADR 0036: one memory plane. The harness writes facts through the existing
# memory_save path (no duplication), and this server owns the four harness
# tables. Future work integrates buildActiveContextBrief into /memories/brief
# and consolidateTurnCandidates into do_remember in estate_memory.py.
# ---------------------------------------------------------------------


@app.post(
    "/harness/approvals",
    summary="Approval webhook callback (HMAC-SHA256 verified)",
)
async def harness_approval_webhook(
    request: Request,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008
    conn=Depends(get_db_conn),  # noqa: B008
    x_fleet_timestamp: Optional[str] = Header(None, alias="x-fleet-timestamp"),
    x_fleet_signature: Optional[str] = Header(None, alias="x-fleet-signature"),
) -> Response:
    """POST handler for approval webhook callbacks from Slack or internal UI.
    Verifies HMAC-SHA256 signature and 5-minute replay window, then updates
    the ticket status atomically and resumes any suspended run."""
    raw_body = await request.body()
    raw_body_str = raw_body.decode("utf-8")
    handler = _get_approval_handler()
    resp = handler.handle_webhook(
        conn, raw_body_str, x_fleet_timestamp, x_fleet_signature
    )
    return Response(
        content=json.dumps(resp.body),
        status_code=resp.status_code,
        media_type="application/json",
    )


@app.get(
    "/harness/telemetry/{tenant_id}",
    status_code=status.HTTP_200_OK,
    summary="Harness telemetry snapshot for /fleet view",
)
async def harness_telemetry(
    tenant_id: str,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008
    conn=Depends(get_db_conn),  # noqa: B008
) -> Dict[str, Any]:
    """Read counts directly from the four harness tables for the /fleet view.
    Works when no OTel tracing stack is running — the /fleet view reads from
    the tables, not from traces."""
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT count(*) AS cnt FROM harness_idempotency WHERE tenant_id = %s;",
            (tenant_id,),
        )
        idempotency_count = (await cur.fetchone())["cnt"]

        await cur.execute(
            "SELECT status, count(*) AS cnt FROM approval_tickets WHERE tenant_id = %s GROUP BY status;",
            (tenant_id,),
        )
        ticket_rows = await cur.fetchall()
        tickets_by_status = {r["status"]: r["cnt"] for r in ticket_rows}

        await cur.execute(
            "SELECT count(DISTINCT run_id) AS cnt FROM harness_scratchpad "
            "WHERE tenant_id = %s AND expires_at > %s;",
            (tenant_id, datetime.now(timezone.utc)),
        )
        active_runs = (await cur.fetchone())["cnt"]

        snap = _harness_telemetry.get_snapshot()

    return {
        "tenant_id": tenant_id,
        "harness": {
            "idempotency_entries": idempotency_count,
            "approval_tickets": {
                "pending": tickets_by_status.get("pending", 0),
                "approved": tickets_by_status.get("approved", 0),
                "consumed": tickets_by_status.get("consumed", 0),
                "rejected": tickets_by_status.get("rejected", 0),
            },
            "active_runs": active_runs,
        },
        "otel_snapshot": {
            "prefetch_count": snap.prefetch_count,
            "last_brief_tokens": snap.last_brief_tokens,
            "facts_promoted": snap.facts_promoted,
            "facts_ignored_ephemeral": snap.facts_ignored_ephemeral,
            "facts_blocked_stale_or_untrusted": snap.facts_blocked_stale_or_untrusted,
            "facts_archived": snap.facts_archived,
            "attempts_by_outcome": snap.attempts_by_outcome,
            "strategy_pivots": snap.strategy_pivots,
            "circuit_breaker_trips": snap.circuit_breaker_trips,
            "approval_events": snap.approval_events,
            "total_cost_usd": snap.total_cost_usd,
        },
    }


# ---------------------------------------------------------------------------
# Active Runtime Harness: sync connection
#
# harness.py is deliberately synchronous and speaks the sync psycopg3 protocol
# (`with conn.cursor()`); the DI pool above yields an AsyncConnection, which
# raises TypeError under that protocol. Every route that calls an engine or
# store method takes a short-lived sync connection from here instead of the
# pooled async one, commits, and closes it before returning.
# ---------------------------------------------------------------------------


def _harness_sync_conn(tenant_id: Optional[str] = None):
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    if tenant_id:
        # The harness tables are FORCE ROW LEVEL SECURITY on app.tenant_id (schema.sql),
        # and a policy with USING alone is also the INSERT's WITH CHECK. Without the
        # GUC set, current_setting returns NULL and every write is rejected -- seen in
        # production 2026-10-19: POST /harness/memory/consolidate -> 500 with
        # psycopg.errors.InsufficientPrivilege on preference_recurrence.
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.tenant_id', %s, true);", (tenant_id,))
    return conn


@app.post(
    "/harness/memory/prefetch",
    status_code=status.HTTP_200_OK,
    summary="Build active context brief for an agent run (Active Memory pre-fetch)",
)
async def harness_memory_prefetch(
    run_id: str,
    task: str,
    project_id: Optional[str] = None,
    namespace: str = "default",
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008
) -> Dict[str, Any]:
    """Pre-fetch hook: called before an agent run starts.
    Calls ActiveMemoryEngine.buildActiveContextBrief and returns the brief text.
    Wire this into do_recall in estate_memory.py as the first step of any
    agent session start.

    Every field is a query param (no body). Until 2026-10-19 the MCP posted them as a JSON
    object: all 5 prefetches in the pod's 18h log were 422, swallowed as a silent degrade, so
    no recall ever carried a brief. tests/test_estate_memory_prefetch_shape.py pins the shape."""
    tenant_id = auth["tenant_id"]
    sync_conn = _harness_sync_conn(tenant_id)
    try:
        cortex = PostgresCortexAdapter(
            sync_conn,
            embed=lambda text: _embed(text, EMBED_QUERY_MODEL),
            namespace=namespace,
            min_cosine=RECALL_MIN_COSINE,
        )
        scratchpad = PostgresScratchpadStore()
        engine = ActiveMemoryEngine(cortex, scratchpad, _harness_telemetry)

        brief, tokens = engine.build_active_context_brief(
            sync_conn, tenant_id, project_id, run_id, task
        )
        sync_conn.commit()
    finally:
        sync_conn.close()
    return {"brief": brief, "estimated_tokens": tokens}


@app.post(
    "/harness/memory/consolidate",
    status_code=status.HTTP_200_OK,
    summary="Consolidate extracted facts after an agent run (Active Memory post-write)",
)
async def harness_memory_consolidate(
    run_id: str,
    project_id: Optional[str] = None,
    provenance: str = "user_direct",
    candidates: Optional[List[Dict[str, Any]]] = None,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008
) -> Dict[str, Any]:
    """Post-write hook: called after an agent run finishes a turn.
    Calls ActiveMemoryEngine.consolidateTurnCandidates to gate ephemeral facts,
    enforce global-preference rules, and write bi-temporal facts to memories.
    Wire this into do_remember in estate_memory.py."""
    tenant_id = auth["tenant_id"]
    sync_conn = _harness_sync_conn(tenant_id)
    try:
        cortex = PostgresCortexAdapter(sync_conn)
        scratchpad = PostgresScratchpadStore()
        engine = ActiveMemoryEngine(cortex, scratchpad, _harness_telemetry)

        parsed_candidates = []
        if candidates:
            for c in candidates:
                parsed_candidates.append(
                    ExtractedFactCandidate(
                        scope=c.get("scope", "ephemeral_turn"),
                        subject=c.get("subject", ""),
                        predicate=c.get("predicate", ""),
                        object=c.get("object", ""),
                        artifact_uri=c.get("artifactUri"),
                        artifact_version_hash=c.get("artifactVersionHash"),
                        source_event_timestamp_iso=c.get("sourceEventTimestampIso"),
                        explicit_permanence_intent=c.get(
                            "explicitPermanenceIntent", False
                        ),
                        confidence=c.get("confidence", 1.0),
                    )
                )

        stats = engine.consolidate_turn_candidates(
            sync_conn, tenant_id, project_id, run_id, provenance, parsed_candidates
        )
        sync_conn.commit()
    finally:
        sync_conn.close()
    return {"memory_stats": stats}


# ---------------------------------------------------------------------------
# Active Runtime Harness Endpoints
# Wire into existing memory endpoints for pre-fetch (brief) and
# consolidation (remember). The full run loop lives here for now;
# future work integrates it into the agent execution layer.
# Wire into existing memory endpoints for pre-fetch (brief) and
# consolidation (remember). The full run loop lives here for now;
# future work integrates it into the agent execution layer.
# ----------------------------------------------------------------------------


@app.get(
    "/harness/stats",
    status_code=status.HTTP_200_OK,
    summary="Active Runtime Harness telemetry snapshot (fleet view)",
)
async def harness_stats(
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008
    conn=Depends(get_db_conn),  # noqa: B008
) -> Dict[str, Any]:
    """Return the harness telemetry snapshot and harness table row counts.

    Wire this into the /fleet view so the founder can watch Active Memory and
    Active Focus operating in real time.
    """
    import asyncio

    tenant_id = auth["tenant_id"]

    # Read telemetry snapshot (sync; run in executor to avoid blocking the async path)
    loop = asyncio.get_event_loop()
    telemetry_snapshot = await loop.run_in_executor(
        None, _harness_telemetry.get_snapshot
    )

    # Read harness table row counts (sync psycopg, wrapped in executor)
    async with conn.cursor() as cur:
        # Pending approval tickets
        await cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM approval_tickets
            WHERE tenant_id = %s AND status = 'pending' AND expires_at > NOW()
            """,
            (tenant_id,),
        )
        pending_approvals = (await cur.fetchone())["count"] or 0

        # Active scratchpad runs (expires > now)
        await cur.execute(
            """
            SELECT COUNT(DISTINCT run_id) AS count
            FROM harness_scratchpad
            WHERE tenant_id = %s AND expires_at > NOW()
            """,
            (tenant_id,),
        )
        active_runs = (await cur.fetchone())["count"] or 0

        # Idempotency entries
        await cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM harness_idempotency
            WHERE tenant_id = %s
            """,
            (tenant_id,),
        )
        idempotency_entries = (await cur.fetchone())["count"] or 0

    return {
        "telemetry": {
            "prefetch_count": telemetry_snapshot.prefetch_count,
            "last_brief_tokens": telemetry_snapshot.last_brief_tokens,
            "facts_promoted": telemetry_snapshot.facts_promoted,
            "facts_ignored_ephemeral": telemetry_snapshot.facts_ignored_ephemeral,
            "facts_blocked_stale_or_untrusted": (
                telemetry_snapshot.facts_blocked_stale_or_untrusted
            ),
            "facts_archived": telemetry_snapshot.facts_archived,
            "total_cost_usd": round(telemetry_snapshot.total_cost_usd, 4),
            "circuit_breaker_trips": telemetry_snapshot.circuit_breaker_trips,
            "strategy_pivots": telemetry_snapshot.strategy_pivots,
            "attempts_by_outcome": telemetry_snapshot.attempts_by_outcome,
            "approval_events": telemetry_snapshot.approval_events,
        },
        "store": {
            "pending_approvals": pending_approvals,
            "active_runs": active_runs,
            "idempotency_entries": idempotency_entries,
        },
        "tenant_id": tenant_id,
    }


@app.get(
    "/harness/scratchpad/{run_id}",
    status_code=status.HTTP_200_OK,
    summary="Active Runtime scratchpad for one agent run",
)
async def harness_scratchpad(
    run_id: str,
    auth: Dict[str, Any] = Depends(authenticate_surface),  # noqa: B008
    conn=Depends(get_db_conn),  # noqa: B008
) -> Dict[str, Any]:
    """Return the current scratchpad key-value pairs for one agent run."""
    tenant_id = auth["tenant_id"]
    scratchpad_store = PostgresScratchpadStore()
    sync_conn = _harness_sync_conn(tenant_id)
    try:
        scratchpad = scratchpad_store.get_working_scratchpad(
            sync_conn, tenant_id, run_id
        )
        sync_conn.commit()
    finally:
        sync_conn.close()
    return {"run_id": run_id, "tenant_id": tenant_id, "scratchpad": scratchpad}


# ----------------------------------------------------------------------------
