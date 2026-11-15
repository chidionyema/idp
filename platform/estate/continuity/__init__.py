"""Durable mission custody: the mission, not the session, is the unit of
execution (ESTATE-P0).

Extends the estate's system of record pattern (the SQLite WAL database that
already owns instruction_ledger and ticket_fences) with missions, attempts,
checkpoints, external effects and failure classes. Lease epochs follow the
same fencing-token pattern ticket_fences already proves.
"""

from .fields import (  # noqa: F401
    CheckpointRejected,
    DuplicateEffect,
    FencedWriteError,
    InvalidTransition,
    LeaseNotAcquired,
    RecordRejected,
    StaleFenceError,
    UnknownField,
)
from .model import (  # noqa: F401
    MISSION_STATES,
    NO_PROGRESS_BOUND_S,
    TRANSITIONS,
)
from .records import (  # noqa: F401
    ACTIVE_ATTEMPT_STATES,
    ATTEMPT_FIELDS,
    CHECKPOINT_FIELDS,
    EFFECT_FIELDS,
    FAILURE_CLASS_FIELDS,
    STALE_ATTEMPT_STATES,
)
from .store import MissionStore  # noqa: F401
from .util import canonical, digest_of  # noqa: F401

__all__ = [
    "ACTIVE_ATTEMPT_STATES",
    "ATTEMPT_FIELDS",
    "CHECKPOINT_FIELDS",
    "CheckpointRejected",
    "DuplicateEffect",
    "EFFECT_FIELDS",
    "FAILURE_CLASS_FIELDS",
    "FencedWriteError",
    "InvalidTransition",
    "LeaseNotAcquired",
    "MISSION_STATES",
    "MissionStore",
    "NO_PROGRESS_BOUND_S",
    "RecordRejected",
    "STALE_ATTEMPT_STATES",
    "StaleFenceError",
    "TRANSITIONS",
    "UnknownField",
    "canonical",
    "digest_of",
]
