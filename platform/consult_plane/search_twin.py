"""Signed research receipts in front of an external search backend.

This is a FIREWALL, not a search engine and not a memory plane. The estate's
search backend already exists and is deployed: `platform/searxng/` is a
self-hosted SearXNG instance in the `searxng` namespace, reachable only
inside the cluster. This module sits in front of whatever fetcher the caller
supplies and does four things the backend does not:

  1. classifies the source into a trust tier (Tier 1 official, Tier 2
     corroborated, Tier 3 quarantined);
  2. sanitizes the payload and quarantines prompt-injection directives;
  3. signs the sanitized result, so a receipt cannot be forged after the fact;
  4. caches the receipt, so a repeated query costs nothing.

ADR 0036 (`docs/decisions/0036-one-memory-plane-and-it-is-cortex.md`) is
binding on the estate: there is ONE memory plane, reached through the one MCP
door, on the one Postgres. The `memory_facts` table below is therefore NOT a
rival memory plane. It is a TTL-scoped RESEARCH RECEIPT cache: every row
carries the `search_receipt_id` of the signed envelope it came from, every
row expires, and nothing is promoted here that has not been verified against
its signature. Durable estate facts go through `remember`/`recall` on the MCP
door; this table holds only the short-lived provenance of external evidence
and is safe to delete at any time.

Standard library only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import IntEnum
from typing import Callable, Optional
from urllib.parse import urlparse


class TrustTier(IntEnum):
    TIER_1_OFFICIAL = 1
    TIER_2_CORROBORATED = 2
    TIER_3_QUARANTINED = 3


TIER_1_HOSTS = frozenset(
    {
        "docs.python.org",
        "doc.rust-lang.org",
        "datatracker.ietf.org",
        "rfc-editor.org",
        "developers.cloudflare.com",
        "docs.github.com",
        "ai.google.dev",
        "docs.anthropic.com",
        "platform.openai.com",
        "nvd.nist.gov",
        "kubernetes.io",
    }
)

TIER_2_HOSTS = frozenset(
    {
        "arxiv.org",
        "blog.cloudflare.com",
        "github.com",
        "aws.amazon.com",
        "sqlite.org",
    }
)

# Directives that try to talk to the reader rather than inform it. A page
# that says "ignore previous instructions" or "bypass the pre-push hook" is
# not evidence; it is an attempt at instruction, and it is quarantined.
INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"override\s+laws\.yaml", re.IGNORECASE),
    re.compile(r"disable\s+(the\s+)?(gate|pre-push|verifier)", re.IGNORECASE),
    re.compile(r"x-idp-auth", re.IGNORECASE),
    re.compile(r"role_allocations", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"bypass\s+.*(hook|guard|seal)", re.IGNORECASE),
)

SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class RawSearchHit:
    """One unfenced search result, before any trust decision is made."""

    source_url: str
    raw_content: str
    ttl_seconds: int = 86400


@dataclass(frozen=True)
class SignedResearchEnvelope:
    """A sanitized, tiered, signed receipt. Verification is mandatory before use."""

    search_receipt_id: str
    query: str
    source_url: str
    retrieved_at_utc: str
    retrieved_at_epoch: int
    content_sha256: str
    trust_tier: int
    ttl_seconds: int
    sanitized_excerpt: str
    injection_detected: bool
    matched_injection_rules: tuple
    sig_hmac_sha256: str


class ResearchFirewallError(RuntimeError):
    """Raised when an untrusted, tampered, or injected envelope is promoted."""


def classify_source_tier(source_url: str) -> TrustTier:
    """Tier 1 official, Tier 2 corroborated, Tier 3 quarantined (everything else)."""
    host = (urlparse(source_url).hostname or "").lower()
    if host in TIER_1_HOSTS:
        return TrustTier.TIER_1_OFFICIAL
    if host in TIER_2_HOSTS:
        return TrustTier.TIER_2_CORROBORATED
    return TrustTier.TIER_3_QUARANTINED


def sanitize_class_c(raw_text: str, max_chars: int = 1200):
    """Strip markup, quarantine injection directives, bound the length.

    Returns (sanitized_text, injection_detected, matched_rule_patterns).
    """
    stripped = SCRIPT_STYLE_RE.sub(" ", raw_text)
    stripped = HTML_TAG_RE.sub(" ", stripped)
    normalized = " ".join(stripped.split())

    matched = []
    redacted = normalized
    for pat in INJECTION_PATTERNS:
        if pat.search(redacted):
            matched.append(pat.pattern)
            redacted = pat.sub("[QUARANTINED_CLASS_C_DIRECTIVE]", redacted)

    if len(redacted) > max_chars:
        redacted = redacted[:max_chars] + "..."
    return redacted, bool(matched), tuple(matched)


class TwinSearchMemory:
    """A signed twin in front of an external search: trust, quarantine, caching.

    `Twin` here means a deterministic, verifiable stand-in for a search result:
    the same query over the same source yields the same receipt id and the same
    signature, so two agents can agree on what the evidence says without
    trusting the transport.
    """

    def __init__(self, signing_secret: bytes, db_path: str = ":memory:") -> None:
        if len(signing_secret) < 16:
            raise ValueError("signing_secret must be at least 16 bytes")
        self._secret = signing_secret
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                envelopes_json TEXT NOT NULL,
                created_at_epoch INTEGER NOT NULL,
                ttl_seconds INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_key TEXT NOT NULL,
                fact_text TEXT NOT NULL,
                search_receipt_id TEXT NOT NULL,
                trust_tier INTEGER NOT NULL,
                promoted_at_epoch INTEGER NOT NULL,
                expires_at_epoch INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_topic ON memory_facts(topic_key);
            """
        )

    def _sign_fields(self, body: dict) -> str:
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hmac.new(self._secret, canonical, hashlib.sha256).hexdigest()

    def build_envelope(
        self,
        query: str,
        hit: RawSearchHit,
        now_epoch: Optional[int] = None,
    ) -> SignedResearchEnvelope:
        ts = now_epoch if now_epoch is not None else int(time.time())
        retrieved_utc = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        excerpt, inj_detected, matched = sanitize_class_c(hit.raw_content)
        content_sha = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        tier = int(classify_source_tier(hit.source_url))
        receipt_seed = f"{query}|{hit.source_url}|{content_sha}|{ts}".encode("utf-8")
        receipt_id = "srch_" + hashlib.sha256(receipt_seed).hexdigest()[:16]

        signable = {
            "search_receipt_id": receipt_id,
            "query": query,
            "source_url": hit.source_url,
            "retrieved_at_utc": retrieved_utc,
            "retrieved_at_epoch": ts,
            "content_sha256": content_sha,
            "trust_tier": tier,
            "ttl_seconds": hit.ttl_seconds,
            "sanitized_excerpt": excerpt,
            "injection_detected": inj_detected,
            "matched_injection_rules": list(matched),
        }
        sig = self._sign_fields(signable)
        return SignedResearchEnvelope(
            **{**signable, "matched_injection_rules": matched, "sig_hmac_sha256": sig}
        )

    def verify_envelope(
        self, envelope: SignedResearchEnvelope, now_epoch: Optional[int] = None
    ) -> bool:
        """True only if the envelope is unexpired, untampered and signed by us."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        if ts >= envelope.retrieved_at_epoch + envelope.ttl_seconds:
            return False
        expected_sha = hashlib.sha256(
            envelope.sanitized_excerpt.encode("utf-8")
        ).hexdigest()
        if not hmac.compare_digest(expected_sha, envelope.content_sha256):
            return False
        signable = {
            "search_receipt_id": envelope.search_receipt_id,
            "query": envelope.query,
            "source_url": envelope.source_url,
            "retrieved_at_utc": envelope.retrieved_at_utc,
            "retrieved_at_epoch": envelope.retrieved_at_epoch,
            "content_sha256": envelope.content_sha256,
            "trust_tier": envelope.trust_tier,
            "ttl_seconds": envelope.ttl_seconds,
            "sanitized_excerpt": envelope.sanitized_excerpt,
            "injection_detected": envelope.injection_detected,
            "matched_injection_rules": list(envelope.matched_injection_rules),
        }
        expected_sig = self._sign_fields(signable)
        return hmac.compare_digest(expected_sig, envelope.sig_hmac_sha256)

    def search(
        self,
        query: str,
        fetcher: Callable,
        cache_ttl_seconds: int = 3600,
        now_epoch: Optional[int] = None,
    ):
        """Return (envelopes, cache_hit). The cache is consulted before upstream."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        q_norm = " ".join(query.strip().lower().split())
        q_hash = hashlib.sha256(q_norm.encode("utf-8")).hexdigest()

        row = self._conn.execute(
            "SELECT envelopes_json, created_at_epoch, ttl_seconds FROM search_cache "
            "WHERE query_hash = ?",
            (q_hash,),
        ).fetchone()
        if row and ts < row[1] + row[2]:
            raw_list = json.loads(row[0])
            envelopes = [
                SignedResearchEnvelope(
                    **{
                        **item,
                        "matched_injection_rules": tuple(
                            item["matched_injection_rules"]
                        ),
                    }
                )
                for item in raw_list
            ]
            if all(self.verify_envelope(e, now_epoch=ts) for e in envelopes):
                return envelopes, True

        hits = fetcher(query)
        envelopes = [self.build_envelope(query, h, now_epoch=ts) for h in hits]
        serialized = [
            {**asdict(e), "matched_injection_rules": list(e.matched_injection_rules)}
            for e in envelopes
        ]
        self._conn.execute(
            """
            INSERT INTO search_cache (query_hash, envelopes_json, created_at_epoch, ttl_seconds)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(query_hash) DO UPDATE SET
                envelopes_json = excluded.envelopes_json,
                created_at_epoch = excluded.created_at_epoch,
                ttl_seconds = excluded.ttl_seconds
            """,
            (q_hash, json.dumps(serialized, sort_keys=True), ts, cache_ttl_seconds),
        )
        return envelopes, False

    def promote_to_memory(
        self,
        topic_key: str,
        fact_text: str,
        envelope: SignedResearchEnvelope,
        ttl_seconds: Optional[int] = None,
        now_epoch: Optional[int] = None,
    ) -> int:
        """Record a verified external fact in the TTL research-receipt cache.

        Refuses an invalid, expired, injection-flagged or Tier-3 receipt. This
        is not the estate memory plane (ADR 0036); durable facts go through the
        MCP door. Every row here expires and carries its receipt id.
        """
        ts = now_epoch if now_epoch is not None else int(time.time())
        if not self.verify_envelope(envelope, now_epoch=ts):
            raise ResearchFirewallError(
                "DENY: cannot promote invalid or expired search receipt"
            )
        if envelope.injection_detected:
            raise ResearchFirewallError(
                "DENY: cannot promote injection-flagged Class C envelope"
            )
        if envelope.trust_tier >= int(TrustTier.TIER_3_QUARANTINED):
            raise ResearchFirewallError(
                "DENY: Tier 3 source cannot be promoted to estate memory"
            )

        effective_ttl = ttl_seconds if ttl_seconds is not None else envelope.ttl_seconds
        expires = ts + effective_ttl
        cur = self._conn.execute(
            """
            INSERT INTO memory_facts (
                topic_key, fact_text, search_receipt_id, trust_tier,
                promoted_at_epoch, expires_at_epoch
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                topic_key,
                fact_text,
                envelope.search_receipt_id,
                envelope.trust_tier,
                ts,
                expires,
            ),
        )
        return int(cur.lastrowid)

    def recall_memory(self, topic_key: str, now_epoch: Optional[int] = None) -> list:
        """Unexpired receipts for a topic. Expired rows are never returned."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        rows = self._conn.execute(
            """
            SELECT topic_key, fact_text, search_receipt_id, trust_tier,
                   promoted_at_epoch, expires_at_epoch
            FROM memory_facts
            WHERE topic_key = ? AND expires_at_epoch > ?
            ORDER BY promoted_at_epoch DESC
            """,
            (topic_key, ts),
        ).fetchall()
        return [
            {
                "topic_key": r[0],
                "fact_text": r[1],
                "search_receipt_id": r[2],
                "trust_tier": r[3],
                "promoted_at_epoch": r[4],
                "expires_at_epoch": r[5],
            }
            for r in rows
        ]
