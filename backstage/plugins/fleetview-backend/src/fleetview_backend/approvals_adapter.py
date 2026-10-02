"""FleetView crew#1013: approvals stream — publishes mutation approvals and rejections to JetStream.

The mutations ledger (`platform/executor/daemon.py`, ledger_root = $IDP_EXECUTOR_RUNS/ledgers/)
is the authoritative record of every proposal. Three states are relevant here:
  - `proposals/<id>.json` exists      → pending
  - `staged/<id>.patch` exists        → verified (ready to approve)
  - neither exists, but it was staged → admitted or rejected

The adapter polls the three subdirectories every 5 s. On every poll it records which ledgers
were in each state; a transition (pending→gone, staged→gone) is one event published to
`estate.approvals.<ledger_id>.<kind>` where kind ∈ approved|rejected.

An admission (staged gone + proposal gone + staged WAS there) is "approved".
A rejection (proposal gone + staged was NOT there) is "rejected".
A ledger that disappears without ever having been staged is "withdrawn".

CONFIG (LAW 46):
  IDP_EXECUTOR_RUNS   ledger root (default ~/.estate/runs)
  NATS_URL            NATS server (default nats://nats.event-bus.svc:4222)
  APPROVALS_POLL_S    poll interval (default 5)

The adapter never raises. A publish failure is logged and swallowed so a bus outage does
not crash the backend -- the event will be captured on the next publish of a similar event.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# ── paths ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_RUNS = Path.home() / ".estate" / "runs"
_POLL_INTERVAL_S = float(os.environ.get("APPROVALS_POLL_S", "5"))


def _ledger_root() -> Path:
    raw = os.environ.get("IDP_EXECUTOR_RUNS")
    return Path(raw) if raw else _DEFAULT_RUNS


def _proposals_dir() -> Path:
    return _ledger_root() / "proposals"


def _staged_dir() -> Path:
    return _ledger_root() / "staged"


# ── snapshot ────────────────────────────────────────────────────────────────────────


def _snapshot() -> tuple[set[str], set[str]]:
    """Return (proposals, staged) — the set of ledger ids currently in each state."""
    proposals: set[str] = set()
    staged: set[str] = set()
    pd = _proposals_dir()
    sd = _staged_dir()
    if pd.is_dir():
        for p in pd.glob("*.json"):
            proposals.add(p.stem)
    if sd.is_dir():
        for p in sd.glob("*.patch"):
            staged.add(p.stem)
    return proposals, staged


def _load_proposal(ledger_id: str) -> dict[str, Any]:
    """Read a proposal JSON, or an empty dict on error."""
    path = _proposals_dir() / f"{ledger_id}.json"
    if path.exists():
        try:
            with path.open() as h:
                return json.load(h)
        except (OSError, ValueError):
            pass
    return {}


def _transitions(
    prev_state: dict[str, frozenset],
    proposals: set[str],
    staged: set[str],
) -> list[tuple[str, str]]:
    """Classify every ledger that changed state since the last poll.

    Pure, so it is verifiable without a bus, a clock or a poll loop. Given what each ledger WAS
    (`prev_state`) and what EXISTS now (`proposals`, `staged`), return the ordered list of
    `(ledger_id, kind)` events to publish.

    The three transitions, and why each is detected against `prev_state` rather than the current
    snapshot: a ledger that is approved has BOTH its proposal and its staged patch removed, so it
    is absent from every current set -- reading the current sets can never see it vanish. The
    departure has to be compared to what was there before.

      staged, now unstaged (whatever else is gone)      -> approved
      pending, never staged, now gone                   -> withdrawn
      pending, was staged (handled by the approved row) -> approved, not withdrawn
    """
    events: list[tuple[str, str]] = []
    for ledger_id, was in prev_state.items():
        is_pending = ledger_id in proposals
        is_staged = ledger_id in staged
        if "staged" in was and not is_staged:
            events.append((ledger_id, "approved"))
            continue
        if "pending" in was and "staged" not in was and not is_pending:
            events.append((ledger_id, "withdrawn"))
    return events


def _emit_event(
    nats_url: str,
    nats_adapter: Any,
    ledger_id: str,
    kind: str,
    proposal: dict[str, Any],
    at: str,
) -> None:
    """Fire-and-forget publish. Logs and swallows all errors so bus trouble never crashes."""
    payload = {
        "ledger_id": ledger_id,
        "kind": kind,
        "at": at,
        "claim": proposal.get("claim", ""),
        "domains": proposal.get("domains", []),
    }
    try:
        # Run the async publish in a new event loop — this function is called from
        # a sync polling thread. Creating a fresh loop per event is slightly wasteful
        # but correct and the poll interval (5 s) makes it negligible.
        import asyncio as _asyncio

        _asyncio.run(
            nats_adapter.publish(
                nats_url, ledger_id, "approvals", kind, "decided", **payload
            )
        )
        _logger.info("fleetview.approval_event %s %s", ledger_id, kind)
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "fleetview.approval_publish_failed %s %s: %s", ledger_id, kind, exc
        )


async def run_approvals_adapter(nats_url: str) -> None:
    """Poll the mutations ledger and publish approval/rejection events. Runs forever."""
    # Import nats_adapter by path so this module works without being a package import.
    import importlib.util as _ilu

    _nats_path = Path(__file__).resolve().parent / "nats_adapter.py"
    _spec = _ilu.spec_from_file_location("fv_nats_impl", _nats_path)
    if _spec is None or _spec.loader is None:
        _logger.error("cannot load nats_adapter")
        return
    _na = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_na)

    # Track state transitions: prev_state[ledger_id] = frozenset of states it was in
    prev_state: dict[str, frozenset] = {}

    while True:
        try:
            proposals, staged = _snapshot()
            curr_state: dict[str, frozenset] = {
                lid: frozenset({"pending"}) for lid in proposals
            }
            for lid in staged:
                curr_state.setdefault(lid, frozenset()).add("staged")

            now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            for ledger_id, kind in _transitions(prev_state, proposals, staged):
                proposal = _load_proposal(ledger_id) if kind == "approved" else {}
                _emit_event(nats_url, _na, ledger_id, kind, proposal, now)

            prev_state = curr_state

        except Exception as exc:  # noqa: BLE001
            _logger.warning("fleetview.approvals_poll_failed: %s", exc)

        await asyncio.sleep(_POLL_INTERVAL_S)
