"""Evidence-first, bounded estate stewardship. Standard library only."""

from __future__ import annotations
import hashlib, json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path

KINDS = {
    "observed",
    "triaged",
    "researched",
    "specified",
    "authorized",
    "started",
    "experimented",
    "verified",
    "rejected",
    "closed",
}
CLASSIFICATIONS = {"public", "internal", "restricted"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def utc():
    return datetime.now(timezone.utc).isoformat()


class Refused(ValueError):
    pass


class Ledger:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
            case_id TEXT NOT NULL, kind TEXT NOT NULL, occurred_at TEXT NOT NULL,
            actor TEXT NOT NULL, classification TEXT NOT NULL,
            payload TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS case_idx ON events(case_id,seq)")
        self.db.commit()

    def append(self, case_id, kind, actor, payload, classification="internal"):
        if kind not in KINDS or classification not in CLASSIFICATIONS:
            raise Refused("unknown event kind or classification")
        if not all(isinstance(v, str) and v.strip() for v in (case_id, actor)):
            raise Refused("case_id and actor required")
        if not isinstance(payload, dict):
            raise Refused("payload must be an object")
        # Do not persist raw secrets, transcripts, credentials or environment dumps.
        forbidden = {
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
            "raw_prompt",
            "raw_response",
        }

        def scan(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if str(k).lower() in forbidden:
                        raise Refused("sensitive field: " + str(k))
                    scan(v)
            elif isinstance(obj, list):
                for v in obj:
                    scan(v)

        scan(payload)
        eid, stamp = str(uuid.uuid4()), utc()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            prev = self.db.execute(
                "SELECT hash FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev[0] if prev else "GENESIS"
            record = dict(
                id=eid,
                case_id=case_id,
                kind=kind,
                occurred_at=stamp,
                actor=actor,
                classification=classification,
                payload=payload,
                prev_hash=prev_hash,
            )
            digest = hashlib.sha256(canonical(record).encode()).hexdigest()
            self.db.execute(
                """INSERT INTO events(id,case_id,kind,occurred_at,actor,classification,payload,prev_hash,hash)
                               VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    eid,
                    case_id,
                    kind,
                    stamp,
                    actor,
                    classification,
                    canonical(payload),
                    prev_hash,
                    digest,
                ),
            )
            self.db.commit()
            return {**record, "hash": digest}
        except Exception:
            self.db.rollback()
            raise

    def events(self, case_id=None, max_classification="restricted"):
        rank = {"public": 0, "internal": 1, "restricted": 2}
        if max_classification not in rank:
            raise Refused("invalid clearance")
        q = "SELECT id,case_id,kind,occurred_at,actor,classification,payload,prev_hash,hash FROM events"
        args = ()
        if case_id:
            q += " WHERE case_id=?"
            args = (case_id,)
        q += " ORDER BY seq"
        rows = []
        for row in self.db.execute(q, args):
            rec = {
                name: row[i]
                for i, name in enumerate(
                    (
                        "id",
                        "case_id",
                        "kind",
                        "occurred_at",
                        "actor",
                        "classification",
                        "payload",
                        "prev_hash",
                        "hash",
                    )
                )
                if i < len(row)
            }
            if rank[rec["classification"]] <= rank[max_classification]:
                rec["payload"] = json.loads(rec["payload"])
                rows.append(rec)
        return rows

    def verify(self):
        prev = "GENESIS"
        for row in self.db.execute(
            "SELECT id,case_id,kind,occurred_at,actor,classification,payload,prev_hash,hash FROM events ORDER BY seq"
        ):
            rec = {
                name: row[i]
                for i, name in enumerate(
                    (
                        "id",
                        "case_id",
                        "kind",
                        "occurred_at",
                        "actor",
                        "classification",
                        "payload",
                        "prev_hash",
                        "hash",
                    )
                )
                if i < len(row)
            }
            digest = rec.pop("hash")
            rec["payload"] = json.loads(rec["payload"])
            if (
                rec["prev_hash"] != prev
                or hashlib.sha256(canonical(rec).encode()).hexdigest() != digest
            ):
                return False
            prev = digest
        return True

    def cases(self):
        out = {}
        for event in self.events():
            case = out.setdefault(
                event["case_id"],
                {
                    "case_id": event["case_id"],
                    "events": 0,
                    "last_kind": None,
                    "latest_at": None,
                },
            )
            case.update(
                events=case["events"] + 1,
                last_kind=event["kind"],
                latest_at=event["occurred_at"],
            )
        return list(out.values())
