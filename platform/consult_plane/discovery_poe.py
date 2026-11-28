"""Tier-0 discovery providers, the Proof-of-Effort gate, and the anti-abuse ratchet.

The estate's retrieval triad -- Gortex (code graph), Cortex (memory plane) and
the Search Twin (external receipts) -- is adopted in DESIGN but its live cluster
state is UNVERIFIED (no 3/3 converging live probe receipts). This module
therefore ships with DETERMINISTIC FALLBACKS that work today, so the gate
protects the budget now and the live backends can be switched on later without
changing a single call site:

  * Gortex  -> read-only Git/AST symbol index over the local checkout.
  * Cortex -> the SQLite WAL receipt store already in `search_twin`.

The Proof-of-Effort gate is the anti-abuse surface. An agent may not spend
Tier-2 frontier tokens until it has proven it exhausted deterministic
discovery. A request missing a discovery receipt is rejected AT ZERO FRONTIER
SPEND, and each rejection is a strike. Three strikes and the session is reaped
by the System Reconciler: it is killed, the failure pattern is recorded, and a
clean stateless worker takes over.

Standard library only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from .search_twin import TwinSearchMemory


class DiscoveryError(RuntimeError):
    """Base error for Tier-0 discovery and Proof-of-Effort enforcement."""


class ProofOfEffortIncompleteError(DiscoveryError):
    """HTTP 412 equivalent: missing discovery, or a raw dump at the door."""

    def __init__(
        self, missing_reasons: list, strike_count: int, session_status: str
    ) -> None:
        self.missing_reasons = missing_reasons
        self.strike_count = strike_count
        self.session_status = session_status
        super().__init__(
            f"POE_INCOMPLETE (strikes={strike_count}, status={session_status}): "
            + "; ".join(missing_reasons)
        )


class AntiAbuseReapedError(DiscoveryError):
    """Raised when a session hits 3 abuse strikes and is reaped by System IoC."""


class TierDemotedError(DiscoveryError):
    """Raised when quota/cooldown abuse demotes a session to Tier-1 cheap fleet."""


@dataclass(frozen=True)
class CodeDiscoveryReceipt:
    """Proof that the codebase was searched before a proposal was made."""

    receipt_id: str
    backend: str  # "gortex_cluster" | "git_ast_fallback"
    query: str
    matched_symbols: tuple
    created_at_epoch: int


@dataclass(frozen=True)
class MemoryDiscoveryReceipt:
    """Proof that internal memory and the closed-defect classes were checked."""

    receipt_id: str
    backend: str  # "cortex_cluster" | "sqlite_wal_fallback"
    topic_key: str
    hit_count: int
    checked_issue_classes: bool
    created_at_epoch: int


@dataclass(frozen=True)
class ProofOfEffortBundle:
    """Everything an agent must present before frontier tokens may be spent."""

    instruction_id: str
    session_id: str
    base_sha: str
    error_digest: str
    failure_excerpt: str
    touches_external_dependency: bool
    code_receipt: Optional[CodeDiscoveryReceipt] = None
    memory_receipt: Optional[MemoryDiscoveryReceipt] = None
    search_envelopes: tuple = ()


class CodeDiscoveryProvider(Protocol):
    def discover(
        self, query: str, now_epoch: Optional[int] = None
    ) -> CodeDiscoveryReceipt: ...


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _open_checked(url: str, timeout: float, data: Optional[bytes] = None):
    """Open a URL whose scheme was just checked (ruff S310).

    `urlopen` will read a `file:` URL, and this endpoint comes from
    configuration, so the scheme is asserted here rather than assumed: https is
    admitted everywhere, loopback http is admitted because that is the local
    test lane, and nothing else reaches the open. The two suppressed call sites
    are the pair this guard protects.
    """
    parts = urllib.parse.urlsplit(url)
    loopback = parts.scheme == "http" and parts.hostname in _LOOPBACK_HOSTS
    if parts.scheme != "https" and not loopback:
        raise urllib.error.URLError(
            f"refusing a gortex endpoint with scheme {parts.scheme!r}"
        )
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(  # noqa: S310 -- scheme asserted above
        url, data=data, headers=headers, method="POST" if data else "GET"
    )
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 -- guarded


class GortexHttpProvider:
    """Live cluster sidecar client for Gortex code-graph retrieval.

    Unverified in the cluster today. When the endpoint is absent or unhealthy
    this raises and the composite falls back to the deterministic AST index, so
    the caller never depends on an unproven cluster state.
    """

    def __init__(self, endpoint_url: str, timeout_seconds: float = 2.0) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def is_healthy(self) -> bool:
        try:
            with _open_checked(
                f"{self.endpoint_url}/healthz", self.timeout_seconds
            ) as resp:
                return 200 <= resp.status < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def discover(
        self, query: str, now_epoch: Optional[int] = None
    ) -> CodeDiscoveryReceipt:
        ts = now_epoch if now_epoch is not None else int(time.time())
        body = json.dumps({"query": query}).encode("utf-8")
        with _open_checked(
            f"{self.endpoint_url}/v1/symbols/search", self.timeout_seconds, data=body
        ) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        symbols = tuple(str(s) for s in data.get("symbols", [])[:20])
        digest = hashlib.sha256(
            f"gortex|{query}|{symbols}|{ts}".encode("utf-8")
        ).hexdigest()[:16]
        return CodeDiscoveryReceipt(
            receipt_id=f"code_gtx_{digest}",
            backend="gortex_cluster",
            query=query,
            matched_symbols=symbols,
            created_at_epoch=ts,
        )


class DeterministicGitAstFallback:
    """Zero-dependency local AST symbol discovery, used while Gortex is unverified."""

    def __init__(self, repo_root) -> None:
        self.repo_root = Path(repo_root)

    def discover(
        self, query: str, now_epoch: Optional[int] = None
    ) -> CodeDiscoveryReceipt:
        ts = now_epoch if now_epoch is not None else int(time.time())
        terms = [t.lower() for t in query.split() if len(t) >= 2]
        matches: list = []

        if self.repo_root.exists():
            for py_file in sorted(self.repo_root.rglob("*.py")):
                if ".git" in py_file.parts or "__pycache__" in py_file.parts:
                    continue
                try:
                    tree = ast.parse(py_file.read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeDecodeError, OSError):
                    continue
                rel = str(py_file.relative_to(self.repo_root))
                for node in ast.walk(tree):
                    if isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    ):
                        name_l = node.name.lower()
                        if not terms or any(
                            t in name_l or t in rel.lower() for t in terms
                        ):
                            kind = "class" if isinstance(node, ast.ClassDef) else "def"
                            matches.append(f"{rel}:{node.lineno}:{kind}:{node.name}")
                            if len(matches) >= 25:
                                break
                if len(matches) >= 25:
                    break

        sym_tuple = tuple(matches)
        digest = hashlib.sha256(
            f"ast|{query}|{sym_tuple}|{ts}".encode("utf-8")
        ).hexdigest()[:16]
        return CodeDiscoveryReceipt(
            receipt_id=f"code_ast_{digest}",
            backend="git_ast_fallback",
            query=query,
            matched_symbols=sym_tuple,
            created_at_epoch=ts,
        )


class CompositeCodeDiscovery:
    """Uses Gortex when live-healthy, falling back deterministically to the AST index."""

    def __init__(
        self,
        gortex: Optional[GortexHttpProvider],
        fallback: DeterministicGitAstFallback,
    ) -> None:
        self.gortex = gortex
        self.fallback = fallback

    def discover(
        self, query: str, now_epoch: Optional[int] = None
    ) -> CodeDiscoveryReceipt:
        if self.gortex is not None:
            try:
                return self.gortex.discover(query, now_epoch=now_epoch)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                pass
        return self.fallback.discover(query, now_epoch=now_epoch)


class SqliteMemoryDiscoveryAdapter:
    """Tier-0 internal memory and issue-class discovery, used while Cortex is live-unverified."""

    def __init__(
        self,
        search_twin: TwinSearchMemory,
        issue_classes: Optional[dict] = None,
    ) -> None:
        self.search_twin = search_twin
        self.issue_classes = issue_classes or {}

    def discover(
        self, topic_key: str, now_epoch: Optional[int] = None
    ) -> MemoryDiscoveryReceipt:
        ts = now_epoch if now_epoch is not None else int(time.time())
        hits = self.search_twin.recall_memory(topic_key, now_epoch=ts)
        issue_hit = 1 if topic_key in self.issue_classes else 0
        total_hits = len(hits) + issue_hit
        digest = hashlib.sha256(
            f"mem|{topic_key}|{total_hits}|{ts}".encode("utf-8")
        ).hexdigest()[:16]
        return MemoryDiscoveryReceipt(
            receipt_id=f"mem_wal_{digest}",
            backend="sqlite_wal_fallback",
            topic_key=topic_key,
            hit_count=total_hits,
            checked_issue_classes=True,
            created_at_epoch=ts,
        )


def _token_shingles(text: str) -> set:
    cleaned = [
        w
        for w in "".join(c.lower() if c.isalnum() else " " for c in text).split()
        if len(w) > 2
    ]
    return set(cleaned)


def _jaccard_similarity(a: str, b: str) -> float:
    """Similarity of two intents. Used to catch paraphrased spam."""
    sa, sb = _token_shingles(a), _token_shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class AntiAbuseRatchet:
    """Enforces 3-strike reaping, spam detection, per-instruction caps, and cooldowns."""

    def __init__(
        self,
        db_path: str = ":memory:",
        max_strikes: int = 3,
        max_consults_per_instruction: int = 2,
        cooldown_seconds: int = 30,
        spam_ttl_seconds: int = 3600,
        paraphrase_threshold: float = 0.80,
    ) -> None:
        self.max_strikes = max_strikes
        self.max_consults_per_instruction = max_consults_per_instruction
        self.cooldown_seconds = cooldown_seconds
        self.spam_ttl_seconds = spam_ttl_seconds
        self.paraphrase_threshold = paraphrase_threshold
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS session_abuse_state (
                session_id TEXT PRIMARY KEY,
                strikes INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'DEMOTED_TIER1', 'REAPED_IOC')),
                last_consult_epoch INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS consult_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                instruction_id TEXT NOT NULL,
                error_digest TEXT NOT NULL,
                intent_text TEXT NOT NULL,
                invariant_version TEXT NOT NULL,
                consult_digest TEXT NOT NULL DEFAULT '',
                created_at_epoch INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS abuse_defect_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                instruction_id TEXT NOT NULL,
                abuse_signal TEXT NOT NULL,
                detail TEXT NOT NULL,
                recorded_at_epoch INTEGER NOT NULL
            );
            """
        )

    def _ensure_session(self, session_id: str):
        row = self._conn.execute(
            "SELECT strikes, status, last_consult_epoch FROM session_abuse_state "
            "WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO session_abuse_state "
                "(session_id, strikes, status, last_consult_epoch) VALUES (?, 0, 'ACTIVE', 0)",
                (session_id,),
            )
            return 0, "ACTIVE", 0
        return int(row[0]), str(row[1]), int(row[2])

    def get_session_state(self, session_id: str) -> dict:
        strikes, status, last_ts = self._ensure_session(session_id)
        return {
            "session_id": session_id,
            "strikes": strikes,
            "status": status,
            "last_consult_epoch": last_ts,
        }

    def add_strike(
        self,
        session_id: str,
        instruction_id: str,
        signal: str,
        detail: str,
        now_epoch: Optional[int] = None,
    ):
        ts = now_epoch if now_epoch is not None else int(time.time())
        strikes, status, _ = self._ensure_session(session_id)
        strikes += 1
        new_status = "REAPED_IOC" if strikes >= self.max_strikes else status
        self._conn.execute(
            "UPDATE session_abuse_state SET strikes = ?, status = ? WHERE session_id = ?",
            (strikes, new_status, session_id),
        )
        self._conn.execute(
            """
            INSERT INTO abuse_defect_log
                (session_id, instruction_id, abuse_signal, detail, recorded_at_epoch)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, instruction_id, signal, detail, ts),
        )
        return strikes, new_status

    def demote_to_tier1(
        self,
        session_id: str,
        instruction_id: str,
        detail: str,
        now_epoch: Optional[int] = None,
    ) -> None:
        ts = now_epoch if now_epoch is not None else int(time.time())
        strikes, status, _ = self._ensure_session(session_id)
        if status != "REAPED_IOC":
            self._conn.execute(
                "UPDATE session_abuse_state SET status = 'DEMOTED_TIER1' WHERE session_id = ?",
                (session_id,),
            )
        self._conn.execute(
            """
            INSERT INTO abuse_defect_log
                (session_id, instruction_id, abuse_signal, detail, recorded_at_epoch)
            VALUES (?, ?, 'QUOTA_OR_COOLDOWN_DEMOTION', ?, ?)
            """,
            (session_id, instruction_id, detail, ts),
        )

    def check_pre_consult(
        self,
        session_id: str,
        instruction_id: str,
        error_digest: str,
        intent_text: str,
        invariant_version: str,
        now_epoch: Optional[int] = None,
    ) -> dict:
        """Reap status, spam duplicates, instruction quota, and burst cooldown."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        strikes, status, last_ts = self._ensure_session(session_id)
        if status == "REAPED_IOC":
            raise AntiAbuseReapedError(
                f"SESSION_REAPED_IOC: session {session_id} terminated after {strikes} abuse strikes"
            )
        if status == "DEMOTED_TIER1":
            raise TierDemotedError(
                f"TIER_1_ONLY: session {session_id} demoted for quota/cooldown thrashing"
            )

        cutoff = ts - self.spam_ttl_seconds
        recent = self._conn.execute(
            """
            SELECT error_digest, intent_text FROM consult_history
            WHERE session_id = ? AND invariant_version = ? AND created_at_epoch >= ?
            """,
            (session_id, invariant_version, cutoff),
        ).fetchall()
        is_spam = False
        for prev_err, prev_intent in recent:
            if prev_err == error_digest:
                is_spam = True
                break
            if (
                _jaccard_similarity(prev_intent, intent_text)
                >= self.paraphrase_threshold
            ):
                is_spam = True
                break

        if is_spam:
            new_strikes, new_status = self.add_strike(
                session_id,
                instruction_id,
                "DUPLICATE_OR_PARAPHRASED_SPAM",
                f"Repeated error_digest={error_digest} or high-similarity intent inside TTL",
                now_epoch=ts,
            )
            if new_status == "REAPED_IOC":
                raise AntiAbuseReapedError(
                    f"SESSION_REAPED_IOC: session {session_id} reaped on spam strike {new_strikes}"
                )
            # The previous answer is returned so the caller can serve it at $0
            # instead of paying for the same question twice.
            prior_digest = ""
            for row in self._conn.execute(
                """
                SELECT consult_digest FROM consult_history
                WHERE session_id = ? AND invariant_version = ? AND created_at_epoch >= ?
                ORDER BY id DESC LIMIT 1
                """,
                (session_id, invariant_version, cutoff),
            ).fetchall():
                prior_digest = str(row[0] or "")
            return {
                "spam_detected": True,
                "strikes": new_strikes,
                "status": new_status,
                "prior_consult_digest": prior_digest,
            }

        inst_count = self._conn.execute(
            "SELECT COUNT(*) FROM consult_history WHERE instruction_id = ?",
            (instruction_id,),
        ).fetchone()[0]
        if inst_count >= self.max_consults_per_instruction:
            self.demote_to_tier1(
                session_id,
                instruction_id,
                f"Exceeded {self.max_consults_per_instruction} consult calls on {instruction_id}",
                now_epoch=ts,
            )
            raise TierDemotedError(
                f"TIER_1_ONLY: instruction {instruction_id} exceeded "
                f"{self.max_consults_per_instruction} frontier consults"
            )

        if last_ts > 0 and (ts - last_ts) < self.cooldown_seconds:
            self.demote_to_tier1(
                session_id,
                instruction_id,
                f"Burst cooldown violated ({ts - last_ts}s < {self.cooldown_seconds}s)",
                now_epoch=ts,
            )
            raise TierDemotedError(
                f"TIER_1_ONLY: cooldown violation on session {session_id}"
            )

        return {"spam_detected": False, "strikes": strikes, "status": status}

    def record_consult(
        self,
        session_id: str,
        instruction_id: str,
        error_digest: str,
        intent_text: str,
        invariant_version: str,
        now_epoch: Optional[int] = None,
        consult_digest: str = "",
    ) -> None:
        ts = now_epoch if now_epoch is not None else int(time.time())
        self._ensure_session(session_id)
        self._conn.execute(
            """
            INSERT INTO consult_history (
                session_id, instruction_id, error_digest, intent_text,
                invariant_version, consult_digest, created_at_epoch
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                instruction_id,
                error_digest,
                intent_text,
                invariant_version,
                consult_digest,
                ts,
            ),
        )
        self._conn.execute(
            "UPDATE session_abuse_state SET last_consult_epoch = ? WHERE session_id = ?",
            (ts, session_id),
        )

    def defect_log(self) -> list:
        rows = self._conn.execute(
            """
            SELECT session_id, instruction_id, abuse_signal, detail, recorded_at_epoch
            FROM abuse_defect_log ORDER BY id ASC
            """
        ).fetchall()
        return [
            {
                "session_id": r[0],
                "instruction_id": r[1],
                "abuse_signal": r[2],
                "detail": r[3],
                "recorded_at_epoch": r[4],
            }
            for r in rows
        ]


class ProofOfEffortGate:
    """Forces Tier-0 discovery before any Tier-2 frontier token may be spent."""

    def __init__(
        self,
        search_twin: TwinSearchMemory,
        ratchet: AntiAbuseRatchet,
        max_failure_excerpt_chars: int = 8000,
    ) -> None:
        self.search_twin = search_twin
        self.ratchet = ratchet
        self.max_failure_excerpt_chars = max_failure_excerpt_chars
        self._verified_receipts: dict = {}

    def verify(
        self,
        bundle: ProofOfEffortBundle,
        now_epoch: Optional[int] = None,
    ) -> str:
        """Verify the bundle, or raise with the missing reasons and the strike count."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        state = self.ratchet.get_session_state(bundle.session_id)
        if state["status"] == "REAPED_IOC":
            raise AntiAbuseReapedError(
                f"SESSION_REAPED_IOC: session {bundle.session_id} already reaped"
            )

        missing: list = []
        if not bundle.instruction_id.strip():
            missing.append("missing live instruction_id")
        if not bundle.base_sha.strip() or len(bundle.base_sha.strip()) < 7:
            missing.append("missing valid base_sha")
        if not bundle.error_digest.strip():
            missing.append("missing normalized error_digest")
        if not bundle.failure_excerpt.strip():
            missing.append("missing minimal reproducible failure excerpt")
        elif len(bundle.failure_excerpt) > self.max_failure_excerpt_chars:
            missing.append(
                f"failure_excerpt exceeds 2K-token cap "
                f"({len(bundle.failure_excerpt)} > {self.max_failure_excerpt_chars} chars)"
            )

        if bundle.code_receipt is None or not bundle.code_receipt.receipt_id:
            missing.append(
                "missing Tier-0 Code Discovery receipt (Gortex or Git-AST fallback)"
            )
        if (
            bundle.memory_receipt is None
            or not bundle.memory_receipt.checked_issue_classes
        ):
            missing.append(
                "missing Tier-0 Internal Memory + issue-classes receipt (Cortex/SQLite)"
            )

        if bundle.touches_external_dependency:
            valid_envs = [
                e
                for e in bundle.search_envelopes
                if self.search_twin.verify_envelope(e, now_epoch=ts)
                and not e.injection_detected
            ]
            if not valid_envs:
                missing.append(
                    "missing verified non-injected Search Twin receipt for external dependency"
                )

        if missing:
            strikes, new_status = self.ratchet.add_strike(
                bundle.session_id,
                bundle.instruction_id or "UNKNOWN",
                "POE_INCOMPLETE",
                "; ".join(missing),
                now_epoch=ts,
            )
            if new_status == "REAPED_IOC":
                raise AntiAbuseReapedError(
                    f"SESSION_REAPED_IOC: session {bundle.session_id} reaped on PoE strike {strikes}"
                )
            raise ProofOfEffortIncompleteError(missing, strikes, new_status)

        seed = json.dumps(
            {
                "instruction_id": bundle.instruction_id,
                "base_sha": bundle.base_sha,
                "error_digest": bundle.error_digest,
                "code_receipt": bundle.code_receipt.receipt_id,
                "memory_receipt": bundle.memory_receipt.receipt_id,
                "search_receipts": [
                    e.search_receipt_id for e in bundle.search_envelopes
                ],
                "verified_at": ts,
            },
            sort_keys=True,
        ).encode("utf-8")
        poe_receipt_id = "poe_" + hashlib.sha256(seed).hexdigest()[:16]
        self._verified_receipts[poe_receipt_id] = {
            "instruction_id": bundle.instruction_id,
            "base_sha": bundle.base_sha,
            "verified_at_epoch": ts,
        }
        return poe_receipt_id

    def is_verified_receipt(self, poe_receipt_id: str, instruction_id: str) -> bool:
        rec = self._verified_receipts.get(poe_receipt_id)
        return rec is not None and rec["instruction_id"] == instruction_id
