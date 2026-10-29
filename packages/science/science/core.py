"""Scientific programme registry, admission gates, and append-only experiment evidence.

No model is trusted to approve its own results. Hardened over the 2026-10-28 reference kernel:
transitions are one atomic transaction with compare-and-set on the state, evidence rows are
immutable at the schema level, and the experimenter is read from the log (the actor who moved the
programme to `running`), never taken from the caller.
"""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATES = (
    "proposed",
    "preregistered",
    "running",
    "analysed",
    "independently_verified",
    "rejected",
    "archived",
)
TRANSITIONS = {
    "proposed": {"preregistered", "rejected"},
    "preregistered": {"running", "rejected"},
    "running": {"analysed", "rejected"},
    "analysed": {"independently_verified", "rejected"},
    "independently_verified": {"archived"},
    "rejected": {"archived"},
    "archived": set(),
}
REQUIRED = (
    "question",
    "hypothesis",
    "null_hypothesis",
    "falsifier",
    "primary_metric",
    "analysis_plan",
    "fixture_digest",
    "verifier",
    "budget_usd",
    "max_seconds",
    "risk_tier",
)
KINDS = (
    "state_transition",
    "run",
    "measurement",
    "artifact",
    "finding",
    "replication",
    "audit",
)
HEX = frozenset("0123456789abcdef")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def _is_sha(s):
    return isinstance(s, str) and len(s) == 64 and set(s) <= HEX


def validate_protocol(p):
    if not isinstance(p, dict):
        raise ValueError("protocol must be object")
    missing = [k for k in REQUIRED if k not in p or p[k] is None or p[k] == ""]
    if missing:
        raise ValueError("missing protocol fields: " + ", ".join(missing))
    if type(p["budget_usd"]) not in (int, float) or not 0 <= p["budget_usd"] <= 100:
        raise ValueError("invalid bounded budget")
    if type(p["max_seconds"]) is not int or not 1 <= p["max_seconds"] <= 86400:
        raise ValueError("invalid time budget")
    if p["risk_tier"] not in ("read_only", "sandboxed"):
        raise ValueError("production experiments prohibited")
    if not _is_sha(p["fixture_digest"]):
        raise ValueError("fixture_digest must be sha256")
    return p


SCHEMA = """
CREATE TABLE IF NOT EXISTS programmes(id TEXT PRIMARY KEY, protocol TEXT NOT NULL, protocol_sha TEXT NOT NULL,
  state TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
  programme_id TEXT NOT NULL REFERENCES programmes(id), kind TEXT NOT NULL, payload TEXT NOT NULL,
  sha TEXT NOT NULL, created TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence
  BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence
  BEGIN SELECT RAISE(ABORT, 'evidence is append-only'); END;
CREATE TRIGGER IF NOT EXISTS programme_protocol_frozen BEFORE UPDATE OF protocol, protocol_sha ON programmes
  BEGIN SELECT RAISE(ABORT, 'protocol is frozen at registration'); END;
"""


class Registry:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: transactions are explicit (BEGIN IMMEDIATE) so a writer takes the lock first.
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)

    def register(self, protocol):
        validate_protocol(protocol)
        pid = str(uuid.uuid4())
        body, sha = canonical(protocol), digest(protocol)
        self.db.execute(
            "INSERT INTO programmes VALUES(?,?,?,?,?)",
            (pid, body, sha, "proposed", utc()),
        )
        return {"programme_id": pid, "protocol_sha256": sha, "state": "proposed"}

    def get(self, pid):
        row = self.db.execute(
            "SELECT protocol,protocol_sha,state FROM programmes WHERE id=?", (pid,)
        ).fetchone()
        if not row:
            raise KeyError(pid)
        return {
            "programme_id": pid,
            "protocol": json.loads(row[0]),
            "protocol_sha256": row[1],
            "state": row[2],
        }

    def list(self, state=None):
        q, a = "SELECT id,state FROM programmes", ()
        if state:
            q, a = q + " WHERE state=?", (state,)
        return [
            {"programme_id": r[0], "state": r[1]}
            for r in self.db.execute(q + " ORDER BY created", a)
        ]

    def _insert_evidence(self, pid, kind, payload, event_id):
        """Caller holds the write lock. Idempotent on (id, sha); conflicting reuse of an id is refused."""
        if kind not in KINDS:
            raise ValueError("unknown evidence kind")
        eid = event_id or str(uuid.uuid4())
        body, sha = canonical(payload), digest(payload)
        existing = self.db.execute(
            "SELECT sha,programme_id FROM evidence WHERE id=?", (eid,)
        ).fetchone()
        if existing:
            if existing[0] != sha or existing[1] != pid:
                raise ValueError("conflicting evidence id")
            return {"id": eid, "duplicate": True, "sha256": sha}
        self.db.execute(
            "INSERT INTO evidence(id,programme_id,kind,payload,sha,created) VALUES(?,?,?,?,?,?)",
            (eid, pid, kind, body, sha, utc()),
        )
        return {"id": eid, "duplicate": False, "sha256": sha}

    def append(self, pid, kind, payload, event_id=None):
        self.get(pid)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            out = self._insert_evidence(pid, kind, payload, event_id)
            self.db.execute("COMMIT")
            return out
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _experimenter(self, pid):
        """The actor who started the run, read from the log -- the caller cannot name them."""
        for payload in (
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT payload FROM evidence WHERE programme_id=? AND kind='state_transition' ORDER BY seq",
                (pid,),
            )
        ):
            if payload.get("to") == "running":
                return payload["receipt"]["actor"]
        return None

    def transition(self, pid, target, receipt):
        """Move state and record the transition in one transaction; a lost race is refused, not applied."""
        if (
            not isinstance(receipt, dict)
            or not receipt.get("actor")
            or not receipt.get("evidence_id")
        ):
            raise ValueError("transition requires actor and evidence_id")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT state FROM programmes WHERE id=?", (pid,)
            ).fetchone()
            if not row:
                raise KeyError(pid)
            current = row[0]
            if target not in TRANSITIONS[current]:
                raise ValueError(f"illegal transition {current}->{target}")
            if target == "independently_verified":
                experimenter = self._experimenter(pid)
                if experimenter is None or receipt["actor"] == experimenter:
                    raise ValueError("self-verification forbidden")
                if not _is_sha(receipt.get("verifier_receipt_sha256")):
                    raise ValueError("independent verifier receipt required")
                cited = self.db.execute(
                    "SELECT 1 FROM evidence WHERE programme_id=? AND id=? AND kind IN ('audit','replication')",
                    (pid, receipt["evidence_id"]),
                ).fetchone()
                if not cited:
                    raise ValueError(
                        "verification must cite an audit or replication evidence row"
                    )
            self._insert_evidence(
                pid,
                "state_transition",
                {"from": current, "to": target, "receipt": receipt},
                None,
            )
            n = self.db.execute(
                "UPDATE programmes SET state=? WHERE id=? AND state=?",
                (target, pid, current),
            ).rowcount
            if n != 1:
                raise ValueError("state changed concurrently")
            self.db.execute("COMMIT")
            return target
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def events(self, pid):
        return [
            {"id": r[0], "kind": r[1], "payload": json.loads(r[2]), "sha256": r[3]}
            for r in self.db.execute(
                "SELECT id,kind,payload,sha FROM evidence WHERE programme_id=? ORDER BY seq",
                (pid,),
            )
        ]
