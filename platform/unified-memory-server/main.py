import os
import hashlib
import time
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, status
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from security_core import (
    OWASPWriteGuard,
    MAPLEGuard,
    MemoryWritePayload,
    SecurityViolationException,
)

# LAW 4: secrets by name only, from the vault. No literal password in source.
DATABASE_URL = os.environ["DATABASE_URL"]

# ---------------------------------------------------------------------
# Lifespan: Bounded AsyncConnectionPool with Connection Checks & Locks
# ---------------------------------------------------------------------
pool: Optional[AsyncConnectionPool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    # Bounded pool with active connection validation and TCP keepalive
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=4,
        max_size=32,
        timeout=10.0,
        check=AsyncConnectionPool.check_connection,
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

    # Coordination: Execute DB schema migration under a Transaction-Scoped Advisory Lock
    # Lock identifier: 0x2100A4 (2162852)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_try_advisory_xact_lock(2162852);")
            acquired = (await cur.fetchone())["pg_try_advisory_xact_lock"]
            if acquired:
                # Primary boot node runs prepare check
                with open("schema.sql", "r") as f:
                    await cur.execute(f.read())
                await conn.commit()
            else:
                # Non-leader pods yield to allow the leader to finish migration
                await conn.rollback()

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
        # Rate Limiter Execution: 120 requests per 60-second window
        window = int(time.time() // 60)
        await cur.execute(
            "SELECT fn_hit_rate_limit(%s, %s, %s);", (token_hash, window, 120)
        )
        allowed = (await cur.fetchone())["fn_hit_rate_limit"]
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

    async with conn.transaction():
        async with conn.cursor() as cur:
            # Check existing record state
            await cur.execute(
                """
                SELECT id, version, trust_tier
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

                # Update row: monotonic trigger automatically increments the version counter
                await cur.execute(
                    """
                    UPDATE memories SET
                        content = %s,
                        content_hash = %s,
                        trust_tier = %s,
                        provenance = %s
                    WHERE id = %s
                    RETURNING id, version;
                    """,
                    (
                        payload.content,
                        content_hash,
                        payload.trust_tier,
                        payload.provenance,
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
                        tenant_id, namespace, key, content, content_hash, trust_tier, provenance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, version;
                    """,
                    (
                        auth["tenant_id"],
                        namespace,
                        key,
                        payload.content,
                        content_hash,
                        payload.trust_tier,
                        payload.provenance,
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
