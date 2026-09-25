"""fleetview_backend — voice + sessions plugin for Backstage.

Canonical imports for the package's public surface.
"""

from fleetview_backend import (
    claude_code_adapter,
    executor_link,
    graph,
    ledger_tail,
    mutations,
    nats_adapter,
    notes,
    outbox,
    sessions,
)
from fleetview_backend.routes import (
    add_nudge,
    blast_radius_envelope,
    check_receipts_envelope,
    graph_envelope,
    mutations_envelope,
    notes_envelope,
    signals_envelope,
    sessions_envelope,
    stream_frames,
)

__all__ = [
    "sessions_envelope",
    "stream_frames",
    "notes_envelope",
    "add_nudge",
    "blast_radius_envelope",
    "graph_envelope",
    "check_receipts_envelope",
    "signals_envelope",
    "mutations_envelope",
]
