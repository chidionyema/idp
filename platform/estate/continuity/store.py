"""MissionStore: the deterministic custody authority (ESTATE-P0).

Every mutation goes through compare-and-swap under BEGIN IMMEDIATE. Acceptance
and the initial checkpoint land in one transaction: a mission never exists only
inside a conversation. Workers propose; this store decides.
"""

from __future__ import annotations

import json
from types import MappingProxyType
import sqlite3
import time
from typing import Any, Dict, Optional

from .accept import AcceptMixin
from .accept_txn import AcceptTxnMixin
from .checkpoints import CheckpointMixin
from .control import ControlMixin
from .effects import EffectsMixin
from .fields import InvalidTransition, UnknownField
from .leases import LeaseMixin
from .recovery import RecoveryMixin
from .schema import SCHEMA
from .schema2 import SCHEMA_2
from .transitions import TransitionMixin


class MissionStore(
    AcceptTxnMixin,
    ControlMixin,
    EffectsMixin,
    TransitionMixin,
    CheckpointMixin,
    LeaseMixin,
    AcceptMixin,
    RecoveryMixin,
):
    def __init__(self, path, *, trusted_verifier_keys=None) -> None:
        # This registry must come from the host's independently admitted
        # configuration, never from a worker's receipt. An unconfigured host
        # may retain pending intents but cannot certify operational effects.
        keys = dict(trusted_verifier_keys or {})
        if any(
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(key, bytes)
            or len(key) != 32
            for name, key in keys.items()
        ):
            raise ValueError(
                "trusted verifier keys must be Ed25519 32-byte public keys"
            )
        if len(set(keys.values())) != len(keys):
            raise ValueError(
                "one public key cannot represent multiple independent verifiers"
            )
        self._trusted_verifier_keys = MappingProxyType(keys)
        self.path = str(path)
        self.db = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.db.executescript(SCHEMA_2)

    def close(self) -> None:
        self.db.close()

    def _strict(self, record: Dict[str, Any], fields) -> Dict[str, Any]:
        unknown = set(record) - set(fields)
        if unknown:
            raise UnknownField(f"unknown fields: {sorted(unknown)}")
        missing = {"mission_id"} & set(fields) - set(record)
        if missing:
            raise UnknownField(f"missing fields: {sorted(missing)}")
        return record

    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            "SELECT * FROM missions WHERE mission_id=?", (mission_id,)
        ).fetchone()
        if row is None:
            return None
        mission = dict(row)
        mission["dependencies"] = json.loads(mission["dependencies"])
        return mission

    def _require(self, mission_id: str) -> Dict[str, Any]:
        mission = self.get_mission(mission_id)
        if mission is None:
            raise InvalidTransition(f"unknown mission {mission_id}")
        return mission

    def _event(
        self,
        mission_id,
        to_state,
        actor,
        cause,
        evidence="",
        attempt_id=None,
        lease_epoch=None,
        from_state=None,
        cur=None,
    ):
        cur.execute(
            "INSERT INTO mission_events (mission_id, attempt_id, lease_epoch,"
            " from_state, to_state, actor, cause, evidence, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                mission_id,
                attempt_id,
                lease_epoch,
                from_state,
                to_state,
                actor,
                cause,
                evidence,
                time.time(),
            ),
        )
