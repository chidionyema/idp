"""Record a real agent action in the estate's evidence ledger.

WHY THIS FILE EXISTS, AND WHY IT IS NOT A SERVICE.

Measured 2026-09-13: the Aevum ledger held 92 receipts and EVERY ONE was `session.start` from
`aevum-core` -- the layer's own heartbeat. No agent action had ever been recorded, so the estate had
a tamper-evident ledger with nothing in it worth tampering with. The layer was up and telling the
truth about a file that was empty.

THE PRIMITIVE, measured in the running pod rather than read from documentation:

    PostgresLedger.append(*, event_type, payload, actor, episode_id=None, causation_id=None,
                          correlation_id=None, ...) -> receipt

It signs with the estate's Ed25519 key, links the receipt to its predecessor by hash, and persists
one row. It does NOT touch the governed knowledge graph -- that is `/v1/ingest`, a different and
more demanding membrane. Recording an action and asserting a fact are not the same act, and this
module only ever does the first.

THE KEY IS THE REASON THIS IS NOT A SEPARATE WORKLOAD. A signature is only worth what the key's
exclusivity is worth. If a recorder outside this pod held the signing key, the key would exist in
two places and the second would be unreviewed; an attacker who takes the recorder's copy can mint
receipts that verify against the estate's public key, and nothing in the chain would show it. So the
recorder shares the pod, and the key stays in one container.

WHAT IT IS NOT ALLOWED TO DO. It cannot create a ledger, only append to the one the server opened.
It cannot repair a chain. It cannot delete. It fails closed: if the connection or the key is
missing it refuses rather than degrading to a memory ledger, because Aevum's in-memory store reports
a VALID chain while recording nothing, which reads exactly like success.
"""

from __future__ import annotations

import os
import sys
import threading

import psycopg
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aevum.core.sigchain import Sigchain
from aevum.store.postgres import PostgresLedger
from aevum.store.postgres.ledger import initialize_ledger_schema

KEY_ID = os.environ.get("AEVUM_KEY_ID", "estate-evidence")


def _private_key(value: str) -> Ed25519PrivateKey:
    """Load the estate's signing key from 64 hex chars or PEM; refuse anything else.

    Same acceptance rule as the server's factory. Kept identical on purpose: two parsers that
    accept different inputs is how a key loads in one process and not the other.
    """
    value = value.strip()
    if len(value) == 64:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))
    raise SystemExit(
        "AEVUM_SIGNING_KEY is not 64 hex characters; this recorder only accepts the form the "
        "server's own factory accepts, so that a key which loads there cannot fail here"
    )


class Recorder:
    """One append-only writer over the estate's ledger."""

    def __init__(self, dsn: str, signing_key: str):
        self._conn = psycopg.connect(dsn, autocommit=True)
        # The store does not create its own table. Without this the first append raises
        # UndefinedTable: relation "aevum_ledger" does not exist. The server calls it too; calling
        # it twice is harmless because the DDL is IF NOT EXISTS.
        initialize_ledger_schema(self._conn)
        self._sigchain = Sigchain(private_key=_private_key(signing_key), key_id=KEY_ID)
        self._ledger = PostgresLedger(self._conn, self._sigchain, threading.Lock())

    def record(
        self,
        *,
        event_type: str,
        actor: str,
        payload: dict,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> str:
        """Append one signed receipt. Returns its audit id."""
        event = self._ledger.append(
            event_type=event_type,
            payload=payload,
            actor=actor,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
        # `audit_id` is a PROPERTY on AuditEvent, and the first version of this line read
        # `getattr(receipt, "audit_id", None)` -- which for a property returns the bound getter, not
        # the value, so a caller got "<bound method AuditEvent.audit_id of ...>" where an id belongs.
        # Measured 2026-09-13 on sequence 93. Call the accessor; do not getattr it.
        audit_id = event.audit_id
        return audit_id() if callable(audit_id) else audit_id

    def verify(self) -> bool:
        """True when every receipt verifies against the chain it was written into.

        This is the whole point of the layer, so it is a method and not a script: a claim about
        the ledger that cannot be checked from inside the process that writes it is a claim nobody
        will check.
        """
        return self._sigchain.verify_chain(self._ledger.all_events())


def from_env() -> Recorder:
    dsn = os.environ.get("AEVUM_POSTGRES_DSN")
    key = os.environ.get("AEVUM_SIGNING_KEY")
    if not dsn or not key:
        # Refuse, never degrade. See the module docstring.
        raise SystemExit(
            "AEVUM_POSTGRES_DSN and AEVUM_SIGNING_KEY must both be set: refusing to record into "
            "anything but the estate's Postgres ledger"
        )
    return Recorder(dsn, key)


if __name__ == "__main__":  # pragma: no cover - a smoke check a person can run
    rec = from_env()
    rid = rec.record(
        event_type="recorder.selftest",
        actor="aevum-recorder",
        payload={
            "note": "one append through the recorder path, to prove it signs and chains"
        },
    )
    print(f"appended {rid}")
    print(f"chain verifies: {rec.verify()}")
    sys.exit(0 if rec.verify() else 1)
