#!/usr/bin/env python3
"""failure_class.py -- the estate's ONE failure-class authority.

THE MANDATE (founder, 2026-10-29): "implement estate-wide loop engineering: one Failure Class
Record (FCR), an atomic claim gate with fencing tokens/expiry/reassignment/crash recovery,
fleet-wide correction broadcast with acknowledgements, recurrence detection, coverage/single-
ownership/no-unverified-promotion/eventual-propagation properties" and "inject a previously
resolved failure into a second independent agent session; the agent must inherit the correction,
intercept the failure deterministically, and produce evidence without another diagnostic
investigation".

WHAT WAS WRONG BEFORE. Every agent that hit the same failure re-derived the same diagnosis, and
every agent that fixed it fixed it in its own checkout. The estate had a claim gate for FILES
(bin/claim-gate: who may write where) and nothing at all for CLASSES (what is known about this
kind of failure, who owns the fix, and whether anyone else has already learned it). A correction
that lives only in one agent's transcript is not a correction; it is an anecdote.

WHAT THIS IS. One local store, three tables of meaning, and no new ticketing system:

  * classes -- the identity of a failure CLASS. Deterministic: fcr-<sha20> over the canonical
    [kind, signature]. Two agents that hit the same class land on the same record, so they
    cannot each believe they are the first to see it.
  * leases -- ONE owner per class, with a monotonic fencing token, an expiry and reassignment.
    The token is what makes a crashed owner's late write harmless: its token is stale, so the
    write is refused. The estate issue stays the tracker of record (carried on the class row);
    this lease never grants permission to write files.
  * resolutions -- a versioned correction plus the assurance receipt that justifies it. A
    consequential class cannot be resolved without a receipt that verifies.
  * enforcement -- per-surface OBSERVED / ADOPTED / RECURRED. Adoption requires that the surface
    SAW the class and then stopped producing it: a surface that has never seen the class has
    adopted nothing. RECURRED re-opens the class and records the prevention gap.

THE BROADCAST IS PULL-BASED. One store, one writer per plane; every other agent asks `check`
and inherits the published correction. There is no broadcast channel to be down, and no message
to be lost: the correction is durable, and the acknowledgements are the adoption rows.

THE STORE. SQLite in WAL mode at ~/.estate/failure-classes/fcr.db (override with ESTATE_FCR_DB).
SQLite is here for one reason: an exclusive claim needs an atomic compare-and-set, and a
fencing token needs a monotonic counter, and GitHub comments cannot provide either for the cost
of a 5-8 second round trip. Cross-host deployment points ESTATE_FCR_DB at shared storage.

EXIT CODES. 0 the operation succeeded; 1 the operation was REFUSED (a live lease, a stale token,
an adoption without an observation, a resolution without a receipt); 2 BLIND, the store could not
be read, which is never a success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

STATE = Path(os.environ.get("ESTATE_STATE_DIR", str(Path.home() / ".estate")))
DB_PATH = Path(
    os.environ.get("ESTATE_FCR_DB", str(STATE / "failure-classes" / "fcr.db"))
)

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_BLIND = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS classes(
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  signature TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  invariant TEXT NOT NULL DEFAULT '',
  issue INTEGER,
  decision_class TEXT,
  state TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0,
  recurrence INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL,
  updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS leases(
  class_id TEXT PRIMARY KEY REFERENCES classes(id),
  owner TEXT NOT NULL,
  token INTEGER NOT NULL,
  expires REAL NOT NULL,
  issue INTEGER
);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  class_id TEXT NOT NULL,
  event TEXT NOT NULL,
  payload TEXT NOT NULL,
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS resolutions(
  class_id TEXT PRIMARY KEY REFERENCES classes(id),
  version INTEGER NOT NULL,
  correction TEXT NOT NULL,
  receipt TEXT NOT NULL,
  created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS enforcement(
  class_id TEXT NOT NULL,
  surface TEXT NOT NULL,
  state TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 0,
  receipt TEXT NOT NULL DEFAULT '',
  evidence TEXT NOT NULL DEFAULT '',
  observed REAL,
  adopted REAL,
  PRIMARY KEY(class_id, surface)
);
CREATE TABLE IF NOT EXISTS surfaces(
  name TEXT PRIMARY KEY,
  description TEXT NOT NULL DEFAULT ''
);
"""


class Refused(Exception):
    """The operation was refused, with a reason. Never a silent no-op."""


class Blind(Exception):
    """The store could not be read or written."""


# --------------------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------------------


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def class_id(kind: str, signature: str) -> Tuple[str, str]:
    """Deterministic class identity: fcr-<sha20> over the canonical [kind, signature]."""
    fingerprint = hashlib.sha256(
        canonical([kind, signature]).encode("utf-8")
    ).hexdigest()
    return "fcr-" + fingerprint[:20], fingerprint


# --------------------------------------------------------------------------------------
# store
# --------------------------------------------------------------------------------------


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    target = Path(path).expanduser() if path else DB_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target), timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        # NORMAL, not FULL: in WAL mode this is safe against an application crash and costs one
        # fsync per checkpoint instead of one per transaction. The store holds leases and
        # acknowledgements, not money; a lease that is a second stale after a power cut is
        # recoverable, and a store that fsyncs every write is a store nobody uses.
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(SCHEMA)
        return conn
    except (sqlite3.Error, OSError) as exc:
        raise Blind(
            "the failure-class store at %s could not be opened: %s" % (target, exc)
        ) from exc


def _event(
    conn: sqlite3.Connection, class_id_: str, event: str, payload: Dict[str, Any]
) -> None:
    conn.execute(
        "INSERT INTO events(class_id, event, payload, created) VALUES(?,?,?,?)",
        (class_id_, event, canonical(payload), time.time()),
    )


def _row(conn: sqlite3.Connection, class_id_: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM classes WHERE id=?", (class_id_,)).fetchone()


def _resolution(conn: sqlite3.Connection, class_id_: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM resolutions WHERE class_id=?", (class_id_,)
    ).fetchone()


def _lease(conn: sqlite3.Connection, class_id_: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM leases WHERE class_id=?", (class_id_,)
    ).fetchone()


# --------------------------------------------------------------------------------------
# operations
# --------------------------------------------------------------------------------------


def op_identify(args: argparse.Namespace) -> int:
    cid, fingerprint = class_id(args.kind, args.signature)
    _print(
        {
            "class_id": cid,
            "kind": args.kind,
            "signature": args.signature,
            "fingerprint": fingerprint,
        }
    )
    return EXIT_OK


def op_open(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    cid, fingerprint = class_id(args.kind, args.signature)
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _row(conn, cid)
        if row is None:
            conn.execute(
                "INSERT INTO classes(id, kind, signature, fingerprint, invariant, issue, "
                "decision_class, state, version, recurrence, created, updated) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    cid,
                    args.kind,
                    args.signature,
                    fingerprint,
                    args.invariant or "",
                    args.issue,
                    args.decision_class,
                    "OPEN",
                    0,
                    0,
                    now,
                    now,
                ),
            )
            _event(
                conn,
                cid,
                "opened",
                {
                    "kind": args.kind,
                    "signature": args.signature,
                    "issue": args.issue,
                    "owner": args.owner,
                },
            )
            state = "OPEN"
            created = True
        else:
            state = row["state"]
            created = False
            _event(conn, cid, "open-seen", {"state": state, "owner": args.owner})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    row = _row(conn, cid)
    _print(
        {
            "class_id": cid,
            "created": created,
            "state": row["state"],
            "issue": row["issue"],
            "decision_class": row["decision_class"],
            "version": row["version"],
            "recurrence": row["recurrence"],
        }
    )
    return EXIT_OK


def op_claim(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _row(conn, args.class_id)
        if row is None:
            conn.execute("ROLLBACK")
            raise Refused("no class %s exists: open it first" % args.class_id)
        lease = _lease(conn, args.class_id)
        if (
            lease is not None
            and lease["expires"] > now
            and lease["owner"] != args.owner
        ):
            conn.execute("ROLLBACK")
            raise Refused(
                "class %s is owned by %s until %.0f (token %d): one owner per class, "
                "and an estate that lets two agents own the same failure produces two "
                "half-fixes"
                % (args.class_id, lease["owner"], lease["expires"], lease["token"])
            )
        token = (lease["token"] + 1) if lease is not None else 1
        expires = now + float(args.ttl_s)
        conn.execute(
            "INSERT INTO leases(class_id, owner, token, expires, issue) VALUES(?,?,?,?,?) "
            "ON CONFLICT(class_id) DO UPDATE SET owner=excluded.owner, token=excluded.token, "
            "expires=excluded.expires, issue=excluded.issue",
            (args.class_id, args.owner, token, expires, args.issue),
        )
        _event(
            conn,
            args.class_id,
            "claimed",
            {
                "owner": args.owner,
                "token": token,
                "expires": expires,
                "issue": args.issue,
            },
        )
        conn.execute("COMMIT")
    except Refused:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print(
        {
            "class_id": args.class_id,
            "owner": args.owner,
            "token": token,
            "expires": expires,
            "state": _row(conn, args.class_id)["state"],
        }
    )
    return EXIT_OK


def op_renew(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    try:
        lease = _lease(conn, args.class_id)
        if lease is None:
            conn.execute("ROLLBACK")
            raise Refused("class %s has no lease to renew" % args.class_id)
        if int(lease["token"]) != int(args.token):
            conn.execute("ROLLBACK")
            raise Refused(
                "token %s is stale: the current token is %d. A fencing token exists so "
                "that a crashed owner's late write cannot land on a class that has "
                "since been reassigned." % (args.token, lease["token"])
            )
        if lease["owner"] != args.owner:
            conn.execute("ROLLBACK")
            raise Refused(
                "the lease is held by %s, not %s" % (lease["owner"], args.owner)
            )
        expires = now + float(args.ttl_s)
        conn.execute(
            "UPDATE leases SET expires=? WHERE class_id=?", (expires, args.class_id)
        )
        _event(
            conn,
            args.class_id,
            "renewed",
            {"owner": args.owner, "token": int(args.token), "expires": expires},
        )
        conn.execute("COMMIT")
    except Refused:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print(
        {
            "class_id": args.class_id,
            "owner": args.owner,
            "token": int(args.token),
            "expires": expires,
        }
    )
    return EXIT_OK


def op_release(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    conn.execute("BEGIN IMMEDIATE")
    try:
        lease = _lease(conn, args.class_id)
        if lease is None:
            conn.execute("ROLLBACK")
            raise Refused("class %s has no lease" % args.class_id)
        if int(lease["token"]) != int(args.token):
            conn.execute("ROLLBACK")
            raise Refused(
                "token %s is stale (current %d)" % (args.token, lease["token"])
            )
        conn.execute("DELETE FROM leases WHERE class_id=?", (args.class_id,))
        _event(
            conn,
            args.class_id,
            "released",
            {"owner": args.owner, "token": int(args.token)},
        )
        conn.execute("COMMIT")
    except Refused:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print({"class_id": args.class_id, "released": True})
    return EXIT_OK


def _consequential(
    decision_class: Optional[str], catalog: Optional[Dict[str, Any]]
) -> bool:
    if not decision_class or not catalog:
        return False
    entry = (catalog.get("decision_classes") or {}).get(decision_class)
    if not entry:
        return False
    return entry.get("method") in ("monte_carlo", "formal")


def _verify_receipt_file(path: str) -> Dict[str, Any]:
    """Verify an assurance receipt by deterministic recomputation, through the assurance module."""
    here = Path(__file__).resolve()
    for cand in (here.parent / "assurance.py", STATE / "libexec" / "assurance.py"):
        if cand.is_file():
            if str(cand.parent) not in sys.path:
                sys.path.insert(0, str(cand.parent))
            break
    try:
        import assurance  # type: ignore
    except ImportError as exc:
        raise Blind(
            "the assurance module is not importable from %s, so a receipt cannot be "
            "verified: a resolution that cannot be checked is not a resolution"
            % here.parent
        ) from exc
    try:
        receipt = json.loads(Path(path).expanduser().read_text())
    except (OSError, ValueError) as exc:
        raise Refused("the receipt %s could not be read: %s" % (path, exc)) from exc
    catalog, _ = assurance.load_catalog()
    if catalog is None:
        raise Blind(
            "the decision-assurance catalog could not be read, so no receipt can be "
            "verified"
        )
    result = assurance.verify_receipt(receipt, catalog)
    return result


def op_resolve(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _row(conn, args.class_id)
        if row is None:
            conn.execute("ROLLBACK")
            raise Refused("no class %s exists" % args.class_id)
        lease = _lease(conn, args.class_id)
        if lease is None:
            conn.execute("ROLLBACK")
            raise Refused(
                "class %s has no lease: resolve it against a lease you hold"
                % args.class_id
            )
        if int(lease["token"]) != int(args.token):
            conn.execute("ROLLBACK")
            raise Refused(
                "token %s is stale (current %d): a resolution from a superseded owner "
                "is refused" % (args.token, lease["token"])
            )
        if lease["owner"] != args.owner:
            conn.execute("ROLLBACK")
            raise Refused(
                "the lease is held by %s, not %s" % (lease["owner"], args.owner)
            )
        if lease["expires"] <= now:
            conn.execute("ROLLBACK")
            raise Refused(
                "the lease expired at %.0f: renew it or re-claim it before resolving"
                % lease["expires"]
            )
        version = int(row["version"]) + 1
        conn.execute("COMMIT")
    except Refused:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise

    # The receipt is checked OUTSIDE the transaction: it is a pure verification and it can be
    # slow (a simulation), and a slow check must not hold the store's write lock.
    decision_class = row["decision_class"]
    receipt_text = ""
    if args.receipt_file:
        result = _verify_receipt_file(args.receipt_file)
        if result.get("verdict") == "BLIND":
            raise Blind(
                "the receipt could not be verified: %s"
                % "; ".join(result.get("problems", []))
            )
        if result.get("verdict") == "BLOCK":
            raise Refused(
                "the receipt does not verify, so the resolution was refused: %s"
                % "; ".join(result.get("problems", []))
            )
        receipt_text = Path(args.receipt_file).expanduser().read_text()
    elif _consequential(decision_class, _catalog()):
        raise Refused(
            "class %s is a consequential class (%s): it cannot be resolved without a "
            "verifiable assurance receipt" % (args.class_id, decision_class)
        )

    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "INSERT INTO resolutions(class_id, version, correction, receipt, created) "
            "VALUES(?,?,?,?,?) ON CONFLICT(class_id) DO UPDATE SET version=excluded.version, "
            "correction=excluded.correction, receipt=excluded.receipt, created=excluded.created",
            (args.class_id, version, args.correction, receipt_text, now),
        )
        conn.execute(
            "UPDATE classes SET state='RESOLVED', version=?, updated=? WHERE id=?",
            (version, now, args.class_id),
        )
        _event(
            conn,
            args.class_id,
            "resolved",
            {
                "version": version,
                "owner": args.owner,
                "token": int(args.token),
                "correction": args.correction,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print(
        {
            "class_id": args.class_id,
            "state": "RESOLVED",
            "version": version,
            "correction": args.correction,
            "receipt": bool(receipt_text),
        }
    )
    return EXIT_OK


def op_check(args: argparse.Namespace) -> int:
    """The pull-based correction broadcast: what is known about this class, right now."""
    conn = connect(args.db)
    if args.class_id:
        cid = args.class_id
    else:
        cid, _ = class_id(args.kind, args.signature)
    row = _row(conn, cid)
    if row is None:
        _print(
            {
                "class_id": cid,
                "known": False,
                "state": None,
                "correction": None,
                "correction_version": None,
                "note": "this class has never been recorded: whoever hits it is the first",
            }
        )
        return EXIT_OK
    resolution = _resolution(conn, cid)
    lease = _lease(conn, cid)
    now = time.time()
    enforcement = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM enforcement WHERE class_id=?", (cid,)
        ).fetchall()
    ]
    _print(
        {
            "class_id": cid,
            "known": True,
            "kind": row["kind"],
            "signature": row["signature"],
            "invariant": row["invariant"],
            "state": row["state"],
            "version": row["version"],
            "recurrence": row["recurrence"],
            "issue": row["issue"],
            "decision_class": row["decision_class"],
            "owner": lease["owner"] if lease else None,
            "lease_expires": lease["expires"] if lease else None,
            "lease_live": bool(lease and lease["expires"] > now),
            "correction": resolution["correction"] if resolution else None,
            "correction_version": resolution["version"] if resolution else None,
            "receipt": resolution["receipt"] if resolution else None,
            "enforcement": enforcement,
        }
    )
    return EXIT_OK


def op_observe(args: argparse.Namespace) -> int:
    """A surface saw the class. If the class was already resolved, this is a RECURRENCE."""
    conn = connect(args.db)
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _row(conn, args.class_id)
        if row is None:
            conn.execute("ROLLBACK")
            raise Refused("no class %s exists" % args.class_id)
        prior = conn.execute(
            "SELECT * FROM enforcement WHERE class_id=? AND surface=?",
            (args.class_id, args.surface),
        ).fetchone()
        version = int(row["version"])
        state = "OBSERVED"
        recurrence = False
        prevention_gap = None
        if row["state"] == "RESOLVED":
            state = "RECURRED"
            recurrence = True
            prevention_gap = {
                "class_id": args.class_id,
                "surface": args.surface,
                "published_version": version,
                "published_correction": (
                    _resolution(conn, args.class_id) or {"correction": ""}
                )["correction"],
                "gap": "the class was resolved at version %d and appeared again at %s: the "
                "correction did not hold, so either the correction was wrong or it was "
                "never adopted here" % (version, args.surface),
            }
            conn.execute(
                "UPDATE classes SET state='REOPENED', recurrence=recurrence+1, "
                "updated=? WHERE id=?",
                (now, args.class_id),
            )
            _event(conn, args.class_id, "recurrence", prevention_gap)
        if prior is None:
            conn.execute(
                "INSERT INTO enforcement(class_id, surface, state, version, receipt, evidence, "
                "observed, adopted) VALUES(?,?,?,?,?,?,?,NULL)",
                (
                    args.class_id,
                    args.surface,
                    state,
                    version,
                    args.receipt or "",
                    args.evidence or "",
                    now,
                ),
            )
        else:
            conn.execute(
                "UPDATE enforcement SET state=?, version=?, receipt=?, evidence=?, observed=? "
                "WHERE class_id=? AND surface=?",
                (
                    state,
                    version,
                    args.receipt or prior["receipt"],
                    args.evidence or "",
                    now,
                    args.class_id,
                    args.surface,
                ),
            )
        if state != "RECURRED":
            _event(
                conn,
                args.class_id,
                "observed",
                {"surface": args.surface, "state": state, "version": version},
            )
        conn.execute("COMMIT")
    except Refused:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print(
        {
            "class_id": args.class_id,
            "surface": args.surface,
            "state": state,
            "version": version,
            "recurrence": recurrence,
            "prevention_gap": prevention_gap,
        }
    )
    return EXIT_OK


def op_adopt(args: argparse.Namespace) -> int:
    """A surface acknowledges the published correction.

    Adoption requires a prior OBSERVATION by that surface and the resolution's exact version:
    a surface that never saw the class has adopted nothing, and a surface that saw a different
    version has adopted a different thing.
    """
    conn = connect(args.db)
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _row(conn, args.class_id)
        if row is None:
            conn.execute("ROLLBACK")
            raise Refused("no class %s exists" % args.class_id)
        resolution = _resolution(conn, args.class_id)
        if resolution is None:
            conn.execute("ROLLBACK")
            raise Refused(
                "class %s has no published correction to adopt" % args.class_id
            )
        if int(resolution["version"]) != int(args.version):
            conn.execute("ROLLBACK")
            raise Refused(
                "the published correction is version %d, not %d: adopting a different "
                "version is not adoption" % (resolution["version"], args.version)
            )
        prior = conn.execute(
            "SELECT * FROM enforcement WHERE class_id=? AND surface=?",
            (args.class_id, args.surface),
        ).fetchone()
        if prior is None or not prior["observed"]:
            conn.execute("ROLLBACK")
            raise Refused(
                "surface %s never observed class %s: a surface that has not seen the "
                "failure has adopted nothing" % (args.surface, args.class_id)
            )
        conn.execute(
            "UPDATE enforcement SET state='ADOPTED', version=?, receipt=?, evidence=?, adopted=? "
            "WHERE class_id=? AND surface=?",
            (
                int(args.version),
                args.receipt or "",
                args.evidence or "",
                now,
                args.class_id,
                args.surface,
            ),
        )
        _event(
            conn,
            args.class_id,
            "adopted",
            {
                "surface": args.surface,
                "version": int(args.version),
                "receipt": args.receipt or "",
            },
        )
        conn.execute("COMMIT")
    except Refused:
        raise
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print(
        {
            "class_id": args.class_id,
            "surface": args.surface,
            "state": "ADOPTED",
            "version": int(args.version),
        }
    )
    return EXIT_OK


def op_register_surface(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "INSERT INTO surfaces(name, description) VALUES(?,?) "
            "ON CONFLICT(name) DO UPDATE SET description=excluded.description",
            (args.name, args.description or ""),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _print({"surface": args.name, "registered": True})
    return EXIT_OK


def op_coverage(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    surfaces = [
        r["name"] for r in conn.execute("SELECT name FROM surfaces ORDER BY name")
    ]
    rows = []
    for row in conn.execute("SELECT * FROM classes ORDER BY id").fetchall():
        cid = row["id"]
        enforcement = {
            r["surface"]: dict(r)
            for r in conn.execute(
                "SELECT * FROM enforcement WHERE class_id=?", (cid,)
            ).fetchall()
        }
        observed = [
            s for s, e in enforcement.items() if e["state"] in ("OBSERVED", "ADOPTED")
        ]
        adopted = [s for s, e in enforcement.items() if e["state"] == "ADOPTED"]
        registered = [s for s in surfaces if s in enforcement] or observed
        rows.append(
            {
                "class_id": cid,
                "kind": row["kind"],
                "signature": row["signature"],
                "state": row["state"],
                "version": row["version"],
                "recurrence": row["recurrence"],
                "surfaces_observed": sorted(observed),
                "surfaces_adopted": sorted(adopted),
                "coverage": _round(len(adopted) / len(registered))
                if registered
                else 0.0,
            }
        )
    total = len(surfaces)
    covered = sum(1 for s in surfaces if any(s in r["surfaces_adopted"] for r in rows))
    _print(
        {
            "registered_surfaces": surfaces,
            "classes": rows,
            "estate_coverage": _round(covered / total) if total else 0.0,
            "note": "coverage is the fraction of registered surfaces that acknowledged the "
            "published correction. An unobserved surface is not a failure; an OBSERVED "
            "surface that never adopted is.",
        }
    )
    return EXIT_OK


def op_pending(args: argparse.Namespace) -> int:
    """The classes this surface has observed but not yet acknowledged.

    A surface that observed a class and has stopped producing it inherits the published
    correction; that is what `adopt` records. A surface that has never observed the class is
    not in this list, because it has adopted nothing.

    RECURRED rows are in the list too: a surface that saw the class come back after it was
    resolved has still not acknowledged the correction, and it is exactly the surface that
    needs to be told about it. Leaving RECURRED out would hide the one surface whose
    acknowledgement matters most.
    """
    conn = connect(args.db)
    rows = []
    for row in conn.execute(
        "SELECT * FROM enforcement WHERE surface=? AND state IN ('OBSERVED','RECURRED') "
        "ORDER BY class_id",
        (args.surface,),
    ).fetchall():
        resolution = _resolution(conn, row["class_id"])
        cls = _row(conn, row["class_id"])
        if resolution is None or cls is None:
            continue
        rows.append(
            {
                "class_id": row["class_id"],
                "kind": cls["kind"],
                "signature": cls["signature"],
                "version": resolution["version"],
                "correction": resolution["correction"],
                "observed": row["observed"],
            }
        )
    _print({"surface": args.surface, "pending": rows})
    return EXIT_OK


def op_events(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    rows = conn.execute(
        "SELECT * FROM events WHERE class_id=? ORDER BY id", (args.class_id,)
    ).fetchall()
    out = []
    for r in rows:
        payload = r["payload"]
        try:
            payload = json.loads(payload)
        except ValueError:
            pass
        out.append(
            {
                "id": r["id"],
                "event": r["event"],
                "created": r["created"],
                "payload": payload,
            }
        )
    _print({"class_id": args.class_id, "events": out})
    return EXIT_OK


def op_summary(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    rows = conn.execute("SELECT * FROM classes ORDER BY id").fetchall()
    out = []
    for row in rows:
        lease = _lease(conn, row["id"])
        out.append(
            {
                "class_id": row["id"],
                "kind": row["kind"],
                "signature": row["signature"],
                "state": row["state"],
                "version": row["version"],
                "recurrence": row["recurrence"],
                "issue": row["issue"],
                "decision_class": row["decision_class"],
                "owner": lease["owner"] if lease else None,
                "lease_live": bool(lease and lease["expires"] > time.time()),
            }
        )
    _print({"classes": out, "count": len(out)})
    return EXIT_OK


def _round(value: float) -> float:
    return float(round(value, 12))


def _catalog() -> Optional[Dict[str, Any]]:
    here = Path(__file__).resolve()
    for cand in (here.parent / "assurance.py", STATE / "libexec" / "assurance.py"):
        if cand.is_file():
            if str(cand.parent) not in sys.path:
                sys.path.insert(0, str(cand.parent))
            break
    try:
        import assurance  # type: ignore
    except ImportError:
        return None
    catalog, _ = assurance.load_catalog()
    return catalog


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="the estate's failure-class authority")
    ap.add_argument("--db", help="path to the failure-class store (ESTATE_FCR_DB)")
    sub = ap.add_subparsers(dest="command")

    def add(name: str, fn: Any, **kwargs: Any) -> argparse.ArgumentParser:
        p = sub.add_parser(name, **kwargs)
        p.set_defaults(func=fn)
        return p

    p = add("identify", op_identify)
    p.add_argument("--kind", required=True)
    p.add_argument("--signature", required=True)

    p = add("open", op_open)
    p.add_argument("--kind", required=True)
    p.add_argument("--signature", required=True)
    p.add_argument("--invariant", default="")
    p.add_argument("--issue", type=int, default=None)
    p.add_argument("--decision-class", dest="decision_class", default=None)
    p.add_argument("--owner", default="unknown")

    p = add("claim", op_claim)
    p.add_argument("--class", dest="class_id", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--ttl-s", dest="ttl_s", type=float, default=3600.0)
    p.add_argument("--issue", type=int, default=None)

    p = add("renew", op_renew)
    p.add_argument("--class", dest="class_id", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--token", type=int, required=True)
    p.add_argument("--ttl-s", dest="ttl_s", type=float, default=3600.0)

    p = add("release", op_release)
    p.add_argument("--class", dest="class_id", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--token", type=int, required=True)

    p = add("resolve", op_resolve)
    p.add_argument("--class", dest="class_id", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--token", type=int, required=True)
    p.add_argument("--correction", required=True)
    p.add_argument("--receipt-file", dest="receipt_file", default=None)

    p = add("check", op_check)
    p.add_argument("--class", dest="class_id", default=None)
    p.add_argument("--kind", default=None)
    p.add_argument("--signature", default=None)

    p = add("observe", op_observe)
    p.add_argument("--class", dest="class_id", required=True)
    p.add_argument("--surface", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--receipt", default="")

    p = add("adopt", op_adopt)
    p.add_argument("--class", dest="class_id", required=True)
    p.add_argument("--surface", required=True)
    p.add_argument("--version", type=int, required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--receipt", default="")

    p = add("register-surface", op_register_surface)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")

    add("coverage", op_coverage)
    p = add("pending", op_pending)
    p.add_argument("--surface", required=True)
    p = add("events", op_events)
    p.add_argument("--class", dest="class_id", required=True)
    add("summary", op_summary)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return EXIT_BLIND
    if (
        args.command == "check"
        and not args.class_id
        and not (args.kind and args.signature)
    ):
        print("REFUSED check needs --class or --kind and --signature")
        return EXIT_REFUSED
    try:
        return int(args.func(args))
    except Refused as exc:
        print("REFUSED %s" % exc)
        return EXIT_REFUSED
    except Blind as exc:
        print("BLIND %s" % exc)
        return EXIT_BLIND
    except (sqlite3.Error, OSError) as exc:
        print("BLIND the failure-class store could not be used: %s" % exc)
        return EXIT_BLIND


if __name__ == "__main__":
    sys.exit(main())
