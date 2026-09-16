"""The in-cluster half of the mutations relay: one laptop, long-polling, over the tailnet.

Why a relay, not a second ledger. `mutations.py`'s `list_pending`/`approve`/`reject` already read
and act on the one mutation ledger `platform/executor/daemon.py` owns (`ledger_root()`,
`~/.estate/runs/ledgers` by default) and speak its one AF_UNIX protocol (`_call_executor`). Both
are laptop-local by construction: `daemon.py`'s `live_worktree()` derives the working tree from
the daemon's own file location, so the daemon can only ever mean the founder's real, current,
possibly-uncommitted checkout -- no cluster Pod has an equivalent, and shipping git-push
credentials into an HTTP-fronted cluster service to fake one would be the second, larger attack
surface ADR 0025 and LAW 21 both exist to rule out. So the ledger and the daemon stay laptop-side,
unmoved, and this module is the wire between an in-cluster HTTP call and that unmoved laptop
process -- never a second store, never a second gauntlet (LAW 43).

Why long-poll, not a WebSocket dependency. `platform/executor/daemon.py` is stdlib-only
(`socketserver`), by design. A plain `POST` the laptop companion holds open needs nothing beyond
`urllib`/`http.client` on the laptop side and nothing beyond FastAPI's existing stack in-cluster --
one fewer dependency to pin, audit and let drift (THE HEADLINE: never script what a proven
platform already solves, and never add what it does not need to).

Why "is the laptop connected" is a liveness window, not a boolean flag flipped once. A laptop
that goes to sleep, loses the tailnet, or is simply not running the companion this hour must read
as disconnected within one poll interval, not linger as "connected" from the last time it asked --
the same "verified, not asserted" discipline ADR 0029 holds documents to.

Transport trust: reachability here is gated below the application layer, by
`platform/tailscale/policy.hujson`'s deny-by-default ACL naming `tag:founder-mac` as the only
source that may reach `tag:estate-fleetview-executor` at all -- the same mutual, cryptographic
node authentication (Tailscale/WireGuard) every other laptop-to-cluster door in this estate
already trusts (`platform/jit/deployment.yaml`'s own comment: "the tailnet is the identity layer
that already exists here, it is federated ... so the ACL is the authentication"). This is not
X.509 client-certificate mTLS; it is the estate's one existing mutual-auth mechanism for exactly
this laptop<->cluster shape, reused rather than a second, bespoke PKI stood up beside it. See the
PR description for the precise gap this leaves, named rather than hidden.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

# One laptop, one connection, in memory -- the same "one replica, deliberately" shape
# platform/jit/deployment.yaml documents for its own in-memory pending-request table: a second
# fleetview-backend replica would hold a different queue, and a request could land on whichever
# pod the Service picked. The catalogue Deployment this sidecar rides in is already `Recreate`
# (platform/backstage/overlays/oke/kustomization.yaml), so there is never more than one of these
# alive at once.
_ALIVE_WINDOW_SEC = 45.0  # comfortably above the companion's own poll cadence (below)
POLL_TIMEOUT_SEC = 25.0
RELAY_TIMEOUT_SEC = (
    50.0  # stays under bin/idp-exec's 60s ceiling with margin for the HTTP hop
)

_last_poll_at: float = 0.0
_queue: "asyncio.Queue[dict[str, Any]]" = asyncio.Queue()
_pending: dict[str, "asyncio.Future[dict[str, Any]]"] = {}


class NotConnected(RuntimeError):
    """No laptop has polled within the liveness window -- routes.py turns this into an honest
    'executor not connected' envelope, never a fake empty-success."""


class RelayTimeout(RuntimeError):
    """The laptop was connected but did not answer this one request in time (asleep mid-poll,
    a slow git operation, a lost tailnet mid-flight)."""


def is_connected() -> bool:
    return (time.monotonic() - _last_poll_at) < _ALIVE_WINDOW_SEC


async def poll(timeout: float = POLL_TIMEOUT_SEC) -> dict[str, Any]:
    """Laptop-facing. Marks the connection alive for one liveness window, then waits for the
    next queued verb (or times out idle) -- the long-poll itself IS the heartbeat, so there is no
    separate 'register' call and nothing to forget to send."""
    global _last_poll_at
    _last_poll_at = time.monotonic()
    try:
        item = await asyncio.wait_for(_queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return {"idle": True}
    return item


async def reply(request_id: str, result: dict[str, Any]) -> bool:
    """Laptop-facing. Resolves the matching `relay()` call below. Returns False for a
    request_id nothing is waiting on (relay already timed out and gave up) -- the laptop's POST
    still gets a 200, since a slow answer arriving late is not the laptop's fault to see as one."""
    future = _pending.pop(request_id, None)
    if future is None or future.done():
        return False
    future.set_result(result)
    return True


async def relay(
    verb: str, payload: dict[str, Any], timeout: float = RELAY_TIMEOUT_SEC
) -> dict[str, Any]:
    """Cluster-facing. Queues one verb for the connected laptop and waits for its reply."""
    if not is_connected():
        raise NotConnected(
            "no laptop has polled /executor/poll within the liveness window"
        )
    request_id = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    future: "asyncio.Future[dict[str, Any]]" = loop.create_future()
    _pending[request_id] = future
    await _queue.put({"request_id": request_id, "verb": verb, "payload": payload})
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError as exc:
        _pending.pop(request_id, None)
        raise RelayTimeout(
            f"the laptop did not answer {verb!r} within {timeout}s"
        ) from exc
