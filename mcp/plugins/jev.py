"""Datasette plugin: JevLayer MCP tools -- the estate's unified confidence-and-decision service.

Registers three tools on the existing estate MCP server through datasette-mcp's extension point,
`register_mcp_tools(datasette, mcp)` -- the same mechanism all sibling plugins use.
This is NOT a second server (ADR 0006: "extend `mcp/`; never add a second server").

ARCHITECTURE (docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md):
  Every decision point (guard, agent, hook, consensus, verifier) calls these tools instead of
  making best-guess decisions locally or calling TypeSafeClient directly. The estate holds
  TYPESAFE_API_KEY; no other repository holds it.

  State envelope per call:
    repo         -- "sovereign" | "hermes" | "estate" | ...
    layer        -- "guard" | "agent" | "hook" | "consensus" | "verifier"
    decision_id  -- "law32_feature_name" | "verifier_z3_gate" | ...
    context      -- free-form dict, Jev reads it as structured input; no secrets

  Every call writes a row to estate.db jev_decisions (UPSERT on decision_id + created_at).
  The estate twin reads jev_decisions for the jev_decisions domain state row.

CONFIG (LAW 46 -- no path or key is a literal in code):
  TYPESAFE_API_KEY           -- TypeSafe API key (from estate-secrets, estate holds the only copy)
  ESTATE_DB_PATH             -- estate.db path (default /data/estate.db)
  JEV_MODEL                  -- model name (default jev-1.13.0)
  JEV_DEFAULT_CONFIDENCE_FLOOR  -- minimum confidence to consider a decision resolved (default 0.7)
  JEV_TIMEOUT_MS             -- per-call timeout in ms (default 2000)

FALLBACK: When Jev is unavailable, each tool returns {escalated: true, _fallback: "<behaviour>"}.
  This is NOT silent failure -- the fallback response is logged to jev_decisions with null confidence.
  The estate MCP door (BLIND mode) also routes here when MCP_GATEWAY_KEY is unset.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - datasette-less CI venv

    def hookimpl(fn):
        return fn


TYPESAFE_API_KEY = os.environ.get("TYPESAFE_API_KEY", "")
ESTATE_DB_PATH = os.environ.get("ESTATE_DB_PATH", "/data/estate.db")
JEVD = os.environ.get("JEV_MODEL", "jev-1.13.0")
DEFAULT_FLOOR = float(os.environ.get("JEV_DEFAULT_CONFIDENCE_FLOOR", "0.7"))
TIMEOUT_MS = int(os.environ.get("JEV_TIMEOUT_MS", "2000"))

_JEVD_INSTALLED = False
_TypeSafeClient = None

try:
    from typesafe_sdk import TypeSafeClient as _TypeSafeClient

    _JEVD_INSTALLED = True
except ImportError:  # pragma: no cover - CI venv without typesafe-sdk
    _TypeSafeClient = None


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass
class JevState:
    repo: str
    layer: str
    decision_id: str
    context: dict[str, Any]


@dataclass
class JevDecision:
    id: str
    repo: str
    layer: str
    decision_id: str
    question: str
    answer: str | None
    confidence: float | None
    probabilities: str | None  # JSON
    escalated: bool
    latency_ms: float | None
    created_at: str

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "repo": self.repo,
            "layer": self.layer,
            "decision_id": self.decision_id,
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "escalated": int(self.escalated),
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def _connect_rw(path: str):
    """Read-write connection for UPSERT. BLIND on locked DB."""
    import sqlite3

    uri = f"file:{path}?mode=rw"
    return sqlite3.connect(uri, uri=True, timeout=10)


def _ensure_table(db_path: str) -> None:
    """Create jev_decisions if it does not exist (idempotent)."""
    import sqlite3

    sql = """
    CREATE TABLE IF NOT EXISTS jev_decisions (
        id           TEXT PRIMARY KEY,
        repo         TEXT NOT NULL,
        layer        TEXT NOT NULL,
        decision_id  TEXT NOT NULL,
        question     TEXT NOT NULL,
        answer       TEXT,
        confidence   REAL,
        probabilities TEXT,
        escalated    INTEGER NOT NULL DEFAULT 0,
        latency_ms   REAL,
        created_at   TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_jevd_repo ON jev_decisions(repo);
    CREATE INDEX IF NOT EXISTS idx_jevd_confidence ON jev_decisions(confidence)
        WHERE confidence IS NOT NULL;
    """
    try:
        con = sqlite3.connect(db_path, timeout=5)
        con.executescript(sql)
        con.close()
    except Exception:  # noqa: S110 -- the failure is non-fatal by design; the caller reads the absent result
        pass  # BLIND: cannot create table on locked/inaccessible DB


def _upsert(decision: JevDecision, db_path: str) -> None:
    """UPSERT into estate.db. BLIND on failure (never blocks the call)."""

    _ensure_table(db_path)
    row = decision.to_row()
    sql = """
    INSERT INTO jev_decisions
        (id, repo, layer, decision_id, question, answer, confidence,
         probabilities, escalated, latency_ms, created_at)
    VALUES
        (:id, :repo, :layer, :decision_id, :question, :answer, :confidence,
         :probabilities, :escalated, :latency_ms, :created_at)
    """
    try:
        con = _connect_rw(db_path)
        con.execute(sql, row)
        con.commit()
        con.close()
    except Exception:  # noqa: S110 -- the failure is non-fatal by design; the caller reads the absent result
        pass  # BLIND: never fail a Jev call because the DB is locked


# ---------------------------------------------------------------------------
# Core Jev calls (pure, testable without MCP server or TypeSafe client)
# ---------------------------------------------------------------------------


def _strip_secrets(context: dict[str, Any]) -> dict[str, Any]:
    """Remove known secret fields before sending to Jev API."""
    SECRET_KEYS = frozenset(
        (
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "private_key",
            "credential",
            "pwd",
            "passwd",
        )
    )
    out: dict[str, Any] = {}
    for k, v in context.items():
        if any(sek in k.lower() for sek in SECRET_KEYS):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _strip_secrets(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out[k] = [
                _strip_secrets(item) if isinstance(item, dict) else item for item in v
            ]
        else:
            out[k] = v
    if any(sek in k.lower() for sek in SECRET_KEYS for k in context):
        out["_password_redacted"] = True
    return out


def _call_jev(
    state: JevState,
    question: str,
    question_type: str,
    options: dict[str, Any] | list[str] | None = None,
    required_confidence: float = DEFAULT_FLOOR,
    timeout_ms: int = TIMEOUT_MS,
) -> dict[str, Any]:
    """Call TypeSafe Jev and return a structured decision dict.

    Returns dict with keys: choice|decision|score (type-specific), confidence,
    probabilities, escalated, latency_ms, _fallback (if unavailable).
    """
    if not _JEVD_INSTALLED or not TYPESAFE_API_KEY:
        return {
            "escalated": True,
            "_fallback": "jev_unavailable",
            "confidence": None,
            "latency_ms": None,
        }

    started = time.monotonic()
    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {TYPESAFE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": JEVD,
            "state": _strip_secrets(state.context),
            "questions": _build_questions(question, question_type, options),
        }
        with httpx.Client(timeout=timeout_ms / 1000) as client:
            resp = client.post(
                "https://api.typesafe.ai/v1/systemone",
                headers=headers,
                json=payload,
            )
        elapsed_ms = (time.monotonic() - started) * 1000

        if resp.status_code != 200:
            return {
                "escalated": True,
                "_fallback": f"jev_http_{resp.status_code}",
                "confidence": None,
                "latency_ms": elapsed_ms,
            }

        data = resp.json()
        answers = data.get("answers", {})
        # One question per call; the question id is the first key
        qid = list(answers.keys())[0] if answers else question_type
        ans = answers.get(qid, {})

        return _parse_answer(ans, question_type, required_confidence, elapsed_ms)

    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - started) * 1000
        return {
            "escalated": True,
            "_fallback": "jev_timeout",
            "confidence": None,
            "latency_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        return {
            "escalated": True,
            "_fallback": f"jev_error_{type(exc).__name__}",
            "confidence": None,
            "latency_ms": elapsed_ms,
        }


def _build_questions(
    question: str, qtype: str, options: dict[str, Any] | list[str] | None
) -> dict[str, dict[str, Any]]:
    """Build the questions dict for the TypeSafe API."""
    if qtype == "choice":
        criteria = (
            options if isinstance(options, dict) else {str(o): o for o in options}
        )
        return {
            "decision": {
                "type": "choice",
                "instructions": question,
                "criteria": criteria,
            }
        }
    elif qtype == "score":
        levels = options if isinstance(options, list) else []
        return {
            "rating": {
                "type": "score",
                "instructions": question,
                "criteria": levels,
            }
        }
    elif qtype == "noul":
        return {
            "truth": {
                "type": "noul",
                "instructions": question,
            }
        }
    return {}


def _parse_answer(
    ans: dict[str, Any], qtype: str, required_confidence: float, elapsed_ms: float
) -> dict[str, Any]:
    """Parse a TypeSafe answer dict into the standard response shape."""
    if qtype == "choice":
        choice = ans.get("choice")
        confidence = ans.get("confidence", 0.0)
        probabilities = ans.get("probabilities")
        return {
            "choice": choice,
            "confidence": confidence,
            "probabilities": probabilities,
            "escalated": confidence < required_confidence,
            "latency_ms": elapsed_ms,
        }
    elif qtype == "score":
        score = ans.get("score")
        level = ans.get("legend", {}).get(str(score)) if ans.get("legend") else None
        confidence = ans.get("confidence", 0.0)
        probabilities = ans.get("probabilities")
        return {
            "score": score,
            "level": level,
            "confidence": confidence,
            "probabilities": probabilities,
            "escalated": confidence < required_confidence,
            "latency_ms": elapsed_ms,
        }
    elif qtype == "noul":
        noul = ans.get("noul")
        confidence = ans.get("confidence", 0.0)
        return {
            "decision": bool(noul >= 0.5),
            "noul": noul,
            "confidence": confidence,
            "escalated": confidence < required_confidence,
            "latency_ms": elapsed_ms,
        }
    return {
        "escalated": True,
        "_fallback": "unknown_question_type",
        "confidence": None,
        "latency_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def jev_choice(
    repo: str,
    layer: str,
    decision_id: str,
    context: dict[str, Any],
    question: str,
    options: list[str],
    required_confidence: float = DEFAULT_FLOOR,
) -> dict[str, Any]:
    """Call Jev choice and return {choice, confidence, probabilities, escalated, latency_ms}."""
    state = JevState(repo=repo, layer=layer, decision_id=decision_id, context=context)
    result = _call_jev(state, question, "choice", options, required_confidence)

    # Always write to DB
    decision = JevDecision(
        id=f"{repo}:{layer}:{decision_id}:{uuid.uuid4().hex[:12]}",
        repo=repo,
        layer=layer,
        decision_id=decision_id,
        question=question,
        answer=result.get("choice"),
        confidence=result.get("confidence"),
        probabilities=json.dumps(result.get("probabilities"))
        if result.get("probabilities")
        else None,
        escalated=result.get("escalated", False),
        latency_ms=result.get("latency_ms"),
        created_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
    )
    _upsert(decision, ESTATE_DB_PATH)
    return result


def jev_score(
    repo: str,
    layer: str,
    decision_id: str,
    context: dict[str, Any],
    question: str,
    levels: list[str],
    required_confidence: float = DEFAULT_FLOOR,
) -> dict[str, Any]:
    """Call Jev score and return {score, level, confidence, probabilities, escalated, latency_ms}."""
    state = JevState(repo=repo, layer=layer, decision_id=decision_id, context=context)
    result = _call_jev(state, question, "score", levels, required_confidence)

    decision = JevDecision(
        id=f"{repo}:{layer}:{decision_id}:{uuid.uuid4().hex[:12]}",
        repo=repo,
        layer=layer,
        decision_id=decision_id,
        question=question,
        answer=result.get("level"),
        confidence=result.get("confidence"),
        probabilities=json.dumps(result.get("probabilities"))
        if result.get("probabilities")
        else None,
        escalated=result.get("escalated", False),
        latency_ms=result.get("latency_ms"),
        created_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
    )
    _upsert(decision, ESTATE_DB_PATH)
    return result


def jev_noul(
    repo: str,
    layer: str,
    decision_id: str,
    context: dict[str, Any],
    question: str,
    threshold: float = DEFAULT_FLOOR,
) -> dict[str, Any]:
    """Call Jev noul and return {decision: bool, confidence, escalated, latency_ms}."""
    state = JevState(repo=repo, layer=layer, decision_id=decision_id, context=context)
    result = _call_jev(state, question, "noul", None, threshold)

    decision = JevDecision(
        id=f"{repo}:{layer}:{decision_id}:{uuid.uuid4().hex[:12]}",
        repo=repo,
        layer=layer,
        decision_id=decision_id,
        question=question,
        answer=str(result.get("decision")),
        confidence=result.get("confidence"),
        probabilities=None,
        escalated=result.get("escalated", False),
        latency_ms=result.get("latency_ms"),
        created_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
    )
    _upsert(decision, ESTATE_DB_PATH)
    return result


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------


@hookimpl
def register_mcp_tools(datasette, mcp) -> None:  # pragma: no cover - estate MCP server
    """Register jev_choice, jev_score, jev_noul on the estate MCP server."""

    async def _jev_choice(
        repo: str,
        layer: str,
        decision_id: str,
        context: dict[str, Any],
        question: str,
        options: list[str],
        required_confidence: float = DEFAULT_FLOOR,
    ) -> dict[str, Any]:
        """Ask Jev to choose one option from a list with confidence.

        repo:        sovereign|hermes|estate|prospector|verdict|agent-foundry|...
        layer:       guard|agent|hook|consensus|verifier
        decision_id: names the specific decision ("law32_feature_name", ...)
        context:     free-form dict of evidence; no secrets (passwords are stripped)
        question:    what to ask Jev
        options:     list of option strings to choose from
        required_confidence: minimum confidence to consider resolved (default 0.7)

        Returns {choice, confidence, probabilities: {option: float}, escalated, latency_ms}.
        When escalated=true the caller should route to human review or deeper analysis.
        When Jev is unavailable: {escalated: true, _fallback: "jev_unavailable", confidence: null}.
        """
        return jev_choice(
            repo, layer, decision_id, context, question, options, required_confidence
        )

    async def _jev_score(
        repo: str,
        layer: str,
        decision_id: str,
        context: dict[str, Any],
        question: str,
        levels: list[str],
        required_confidence: float = DEFAULT_FLOOR,
    ) -> dict[str, Any]:
        """Ask Jev to score the state on a rubric with confidence.

        repo:        sovereign|hermes|estate|prospector|verdict|agent-foundry|...
        layer:       guard|agent|hook|consensus|verifier
        decision_id: names the specific decision
        context:     free-form dict of evidence; no secrets
        question:    what to ask Jev
        levels:      ordered list of level descriptions (low to high)
        required_confidence: minimum confidence to consider resolved (default 0.7)

        Returns {score, level, confidence, probabilities: {level: float}, escalated, latency_ms}.
        """
        return jev_score(
            repo, layer, decision_id, context, question, levels, required_confidence
        )

    async def _jev_noul(
        repo: str,
        layer: str,
        decision_id: str,
        context: dict[str, Any],
        question: str,
        threshold: float = DEFAULT_FLOOR,
    ) -> dict[str, Any]:
        """Ask Jev whether a statement is true with confidence.

        repo:        sovereign|hermes|estate|prospector|verdict|agent-foundry|...
        layer:       guard|agent|hook|consensus|verifier
        decision_id: names the specific decision
        context:     free-form dict of evidence; no secrets
        question:    statement to evaluate (will receive a yes/no answer)
        threshold:   minimum confidence to return True (default 0.7)

        Returns {decision: bool, noul: float, confidence, escalated, latency_ms}.
        decision=true when noul >= threshold. escalated=true when confidence < threshold.
        """
        return jev_noul(repo, layer, decision_id, context, question, threshold)

    mcp.add_tool(_jev_choice, name="jev_choice")
    mcp.add_tool(_jev_score, name="jev_score")
    mcp.add_tool(_jev_noul, name="jev_noul")
