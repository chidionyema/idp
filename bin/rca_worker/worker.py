"""Primitive D of the via-negativa engine: the async RCA worker.

Consumes failure events (a "session hit a dead end") off a Redis Stream,
asks an LLM for a *structured, schema-enforced* root-cause signature via
`instructor`, drops anything subjective or low-confidence, and persists
what survives to the Postgres ledger (schema.sql) and to the Redis SET the
proxy (Primitive A) reads for fast pre-flight rejection.

Design split, on purpose: `NegativeConstraint`, `rule_allowed` and
`build_prompt` are pure functions with zero I/O, so
tests/test_via_negativa_engine.py can import and exercise them without a
live Redis/Postgres/LLM -- only `run_forever()` below touches the network,
and it imports redis/asyncpg/instructor lazily so a schema-only import
(as the tests do) never requires infra credentials or those packages to
even be reachable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import signal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("via_negativa.rca_worker")

MIN_CONFIDENCE = 0.6


class NegativeConstraint(BaseModel):
    """The one shape an LLM is allowed to hand back for a failure.

    Enforced via `instructor` (Pydantic-schema-constrained generation), not
    parsed out of free text -- the email's whole point: no hallucinated
    root causes, no vague "it broke" rules reaching the ledger.
    """

    scope: str = Field(description="e.g. 'bash', 'python', 'kubectl'")
    signature_regex: str = Field(
        description="regex matching the failure, args normalized out"
    )
    semantic_summary: str = Field(description="one sentence: what NOT to do and why")
    is_deterministic: bool = Field(
        description="true only if this is a reproducible, mechanical failure "
        "(a missing module, a bad flag) -- never an opinion"
    )
    confidence_score: float = Field(ge=0.0, le=1.0)

    @field_validator("signature_regex")
    @classmethod
    def _must_compile(cls, v: str) -> str:
        import re

        re.compile(v)  # raises ValidationError-wrapped re.error if malformed
        return v


def rule_allowed(nc: NegativeConstraint) -> bool:
    """The admission guard: subjective or low-confidence rules never reach the ledger.

    Both thresholds are load-bearing per the founder spec -- a rule that
    isn't reproducible, or one the model isn't confident about, does more
    harm (false-positive blocks) than good.
    """
    if not nc.is_deterministic:
        return False
    if nc.confidence_score < MIN_CONFIDENCE:
        return False
    return True


# --------------------------------------------------------------------------
# Primitive B: deterministic regex pre-filter. Pure and zero-I/O like the
# three functions above it -- a known, mechanical failure class gets a
# NegativeConstraint WITHOUT ever calling the LLM: fewer tokens, and zero
# hallucination risk for exactly the classes we can already prove out by
# inspection. `_handle_one` below tries this FIRST and only falls back to
# `_extract_constraint` (the LLM path) when nothing here matches.
# --------------------------------------------------------------------------

# (scope, pattern searched against "stderr\nstdout", semantic_summary). Order
# matters only in that the first match wins; patterns are disjoint in
# practice (each names a distinct, well-known failure mode) so this is not
# load-bearing today.
KNOWN_FAILURE_SIGNATURES: list[tuple[str, str, str]] = [
    (
        "python",
        r"ModuleNotFoundError: No module named '[^']+'",
        "Do not run a command that imports a module not yet installed in this environment.",
    ),
    (
        "python",
        r"ImportError: cannot import name '[^']+'",
        "Do not import a name that does not exist in the target module without checking first.",
    ),
    (
        "git",
        r"fatal: not a git repository",
        "Do not run a git command outside a git working tree.",
    ),
    (
        "git",
        r"fatal: [Aa] branch named '.+' already exists",
        "Do not create a branch without first checking whether it already exists.",
    ),
    (
        "git",
        r"! \[rejected\].*non-fast-forward",
        "Do not push without first fetching and reconciling upstream changes.",
    ),
    (
        "shell",
        r"[Pp]ermission denied",
        "Do not run a command against a path this user cannot access without checking permissions first.",
    ),
    (
        "shell",
        r"[Nn]o such file or directory",
        "Do not reference a path before confirming it exists.",
    ),
    (
        "shell",
        r"command not found",
        "Do not invoke a binary without first confirming it is installed on this host.",
    ),
    (
        "network",
        r"[Cc]onnection refused|ECONNREFUSED",
        "Do not assume a service is reachable without a live health check first.",
    ),
]

_KNOWN_FAILURE_RE = [
    (scope, re.compile(pattern), summary)
    for scope, pattern, summary in KNOWN_FAILURE_SIGNATURES
]

REGEX_PREFILTER_CONFIDENCE = (
    0.95  # deterministic by construction; above MIN_CONFIDENCE on purpose
)


def regex_extract_constraint(payload: dict[str, Any]) -> NegativeConstraint | None:
    """Match a failure against KNOWN_FAILURE_SIGNATURES; None means "unknown class, ask the LLM".

    Every hit is `is_deterministic=True` because the class itself was picked for being
    mechanical and reproducible -- the same guarantee `rule_allowed` demands from an
    LLM-extracted constraint, here established by inspection instead of a model's say-so.
    """
    text = f"{payload.get('stderr', '') or ''}\n{payload.get('stdout', '') or ''}"
    for scope, compiled, summary in _KNOWN_FAILURE_RE:
        if compiled.search(text):
            return NegativeConstraint(
                scope=scope,
                signature_regex=compiled.pattern,
                semantic_summary=summary,
                is_deterministic=True,
                confidence_score=REGEX_PREFILTER_CONFIDENCE,
            )
    return None


def build_prompt(payload: dict[str, Any]) -> str:
    """Render a failure event into the prompt handed to the LLM extractor.

    Deliberately plain and inspectable (no template engine) -- the prompt
    is itself part of what an auditor reviews when a bad rule slips through.
    """
    command = payload.get("command", "")
    exit_code = payload.get("exit_code", "")
    stderr = payload.get("stderr", "")
    stdout = payload.get("stdout", "")
    return (
        "A command failed. Extract ONE deterministic negative constraint "
        "(what an agent should never do again) from this failure, or say "
        "it is not deterministic.\n\n"
        f"command: {command}\n"
        f"exit_code: {exit_code}\n"
        f"stderr:\n{stderr}\n"
        f"stdout:\n{stdout}\n\n"
        "Rules: normalize away dynamic values (paths, timestamps, UUIDs) "
        "from signature_regex. Set is_deterministic=false for anything "
        "that looks like flaky infra, a timeout, or a one-off. Only give "
        "confidence_score >= 0.6 when you would bet the constraint holds "
        "for every future occurrence of this exact failure class."
    )


# --------------------------------------------------------------------------
# Infra-touching pipeline below. Nothing above this line imports redis,
# asyncpg or instructor's client machinery -- see module docstring.
# --------------------------------------------------------------------------

STREAM_KEY = os.environ.get("VN_FAILURE_STREAM", "via_negativa:failures")
CONSUMER_GROUP = os.environ.get("VN_CONSUMER_GROUP", "rca-workers")
DLQ_KEY = os.environ.get("VN_DLQ_STREAM", "via_negativa:failures:dlq")
BANNED_SET_KEY = os.environ.get("VN_BANNED_SET", "via_negativa:banned_signatures")
# Primitive C's supply: the proxy's ZREVRANGE target (bin/negative-constraints-proxy/main.go's
# TOP_CONSTRAINTS_KEY), ranked by failure_count so the proxy injects the most-repeated lessons.
TOP_CONSTRAINTS_KEY = os.environ.get(
    "VN_TOP_CONSTRAINTS_KEY", "via_negativa:top_constraints"
)
MAX_ATTEMPTS = int(os.environ.get("VN_MAX_ATTEMPTS", "3"))


async def _extract_constraint(
    client: Any, payload: dict[str, Any], model: str
) -> NegativeConstraint | None:
    """Call the LLM through instructor's schema-enforced wrapper.

    Returns None (not a dropped-confidence rule, an actual extraction
    failure) on any error -- the caller routes those to the DLQ rather
    than silently losing the failure event.
    """
    try:
        return await client.chat.completions.create(
            model=model,
            response_model=NegativeConstraint,
            messages=[{"role": "user", "content": build_prompt(payload)}],
            max_retries=1,
        )
    except Exception:
        logger.exception("LLM extraction failed for payload=%r", payload)
        return None


async def _persist(pg_pool: Any, redis_client: Any, nc: NegativeConstraint) -> None:
    """Write an admitted rule to the durable ledger, then to the proxy's fast-path set.

    Order matters: Postgres (the source of truth, with the pgvector column
    for future semantic-dedup) is written first; the Redis SET is a cache
    the proxy fail-opens around, so it's fine if this second write is what
    fails and gets retried on the next cycle.
    """
    async with pg_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO rules (scope, signature, confidence, failure_count)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (signature) DO UPDATE
                SET failure_count = rules.failure_count + 1,
                    confidence = GREATEST(rules.confidence, EXCLUDED.confidence)
            """,
            nc.scope,
            nc.signature_regex,
            nc.confidence_score,
        )
    await redis_client.sadd(BANNED_SET_KEY, nc.signature_regex)
    # Primitive C: rank by repeat count so the proxy's top-N injection surfaces the lessons that
    # keep recurring, not just the most recent one.
    await redis_client.zincrby(TOP_CONSTRAINTS_KEY, 1, nc.semantic_summary)


async def _handle_one(
    entry_id: str,
    fields: dict[str, str],
    client: Any,
    pg_pool: Any,
    redis_client: Any,
    model: str,
) -> bool:
    try:
        payload = json.loads(fields.get("payload", "{}"))
    except json.JSONDecodeError:
        logger.warning("dropping malformed entry %s: not JSON", entry_id)
        return True  # ack and move on; it will never parse on retry either

    nc = regex_extract_constraint(
        payload
    )  # Primitive B: try the free, deterministic path first
    if nc is None:
        nc = await _extract_constraint(client, payload, model)
    if nc is None:
        return False  # let it retry / eventually DLQ

    if not rule_allowed(nc):
        logger.info(
            "rule dropped (deterministic=%s confidence=%.2f): %s",
            nc.is_deterministic,
            nc.confidence_score,
            nc.semantic_summary,
        )
        return True

    await _persist(pg_pool, redis_client, nc)
    logger.info(
        "rule admitted scope=%s confidence=%.2f: %s",
        nc.scope,
        nc.confidence_score,
        nc.semantic_summary,
    )
    return True


def _read_secret_file(file_env: str) -> str | None:
    """Read a mounted secret file named by an env var, or None if unset/unreadable.

    Same Kyverno secrets-not-from-env-vars rationale as _with_password_from_file, for a
    value that is not part of a URL (the router API key).
    """
    path = os.environ.get(file_env, "")
    if not path:
        return None
    try:
        return open(path).read().strip()  # noqa: PTH123 - one-shot secret read
    except OSError as exc:
        logging.warning("%s %r: %s (continuing without it)", file_env, path, exc)
        return None


def _with_password_from_file(url: str, file_env: str) -> str:
    """Splice a mounted secret file's contents into `url` as the password.

    Mirrors bin/negative-constraints-proxy/main.go's resolveRedisURL(): Kyverno
    secrets-not-from-env-vars refuses a password as pod env, so it rides a mounted file
    instead and the process folds it in itself. A missing or unreadable file leaves `url`
    unchanged -- consistent with this worker's own fail-open posture elsewhere.
    """
    path = os.environ.get(file_env, "")
    if not path:
        return url
    try:
        password = open(path).read().strip()  # noqa: PTH123 - one-shot secret read, no filesystem API needed beyond this
    except OSError as exc:
        logging.warning("%s %r: %s (continuing without auth)", file_env, path, exc)
        return url
    parts = urlsplit(url)
    user = parts.username or ""
    netloc = f"{user}:{password}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


async def run_forever(
    model: str = os.environ.get("VN_LLM_MODEL", "gpt-4o-mini"),
) -> None:
    """The consume loop: Redis Streams in, Postgres+Redis out, DLQ on repeated failure.

    Graceful SIGTERM shutdown (Kubernetes sends this on every pod restart):
    the loop checks a stop flag between messages rather than being killed
    mid-write, so a rollout never corrupts an in-flight ledger insert.
    """
    import asyncpg
    import instructor
    import redis.asyncio as redis
    from openai import AsyncOpenAI

    redis_url = _with_password_from_file(
        os.environ.get("REDIS_URL", "redis://127.0.0.1:6379"), "REDIS_PASSWORD_FILE"
    )
    pg_dsn = _with_password_from_file(
        os.environ.get("VN_LEDGER_DSN", "postgresql://localhost/via_negativa"),
        "VN_LEDGER_DSN_PASSWORD_FILE",
    )

    openai_api_key = _read_secret_file("OPENAI_API_KEY_FILE") or os.environ.get(
        "OPENAI_API_KEY"
    )
    openai_base_url = os.environ.get("OPENAI_BASE_URL")

    redis_client = redis.from_url(redis_url, decode_responses=True)
    pg_pool = await asyncpg.create_pool(pg_dsn, min_size=1, max_size=4)
    # Every statement in schema.sql is IF NOT EXISTS, so applying it on every start is a
    # no-op after the first: this is the ledger's only migration path, a brand new database
    # with nothing to copy in (platform/estate-db/cluster/databases.yaml).
    await pg_pool.execute((Path(__file__).with_name("schema.sql")).read_text())
    client = instructor.from_openai(
        AsyncOpenAI(api_key=openai_api_key, base_url=openai_base_url)
    )

    try:
        await redis_client.xgroup_create(
            STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True
        )
    except Exception as exc:  # BUSYGROUP if it already exists -- fine
        if "BUSYGROUP" not in str(exc):
            raise

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    consumer_name = f"rca-worker-{os.getpid()}"
    logger.info(
        "rca worker %s starting, stream=%s group=%s",
        consumer_name,
        STREAM_KEY,
        CONSUMER_GROUP,
    )

    # The heartbeat file's mtime is the liveness signal (platform/via-negativa/rca.yaml's
    # exec probe): this loop has no listening port to probe, so the real question a probe
    # can ask is whether the xreadgroup loop is still turning, not whether messages are
    # flowing -- block=2000 below means an idle consumer still reaches here every ~2s.
    heartbeat_path = Path(os.environ.get("VN_HEARTBEAT_PATH", "/tmp/heartbeat"))  # noqa: S108

    while not stop.is_set():
        heartbeat_path.touch()
        resp = await redis_client.xreadgroup(
            CONSUMER_GROUP,
            consumer_name,
            {STREAM_KEY: ">"},
            count=10,
            block=2000,
        )
        for _stream, entries in resp or []:
            for entry_id, fields in entries:
                attempts = int(fields.get("attempts", "0"))
                ok = await _handle_one(
                    entry_id, fields, client, pg_pool, redis_client, model
                )
                if ok:
                    await redis_client.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
                elif attempts + 1 >= MAX_ATTEMPTS:
                    logger.error(
                        "entry %s exceeded %d attempts, routing to DLQ",
                        entry_id,
                        MAX_ATTEMPTS,
                    )
                    await redis_client.xadd(
                        DLQ_KEY, {**fields, "attempts": str(attempts + 1)}
                    )
                    await redis_client.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
                else:
                    fields["attempts"] = str(attempts + 1)
                    await redis_client.xadd(STREAM_KEY, fields)
                    await redis_client.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)

    logger.info("rca worker %s shutting down cleanly", consumer_name)
    await pg_pool.close()
    await redis_client.aclose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
