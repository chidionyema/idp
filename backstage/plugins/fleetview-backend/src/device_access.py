"""Device access state: what THIS device's read-only cluster identity is, if anything.

WHY A ROUTE AND NOT A BROWSER CALL. The state lives on the device (`bin/idp-jit status`) and
the browser is not allowed to hold the agent key, so the browser cannot answer this question
by itself. The page asks this door, the door runs the command, and the answer travels back as
JSON. The portal never sees a key, never sees a token, and never talks to OCI.

WHAT THIS DELIBERATELY DOES NOT DO. It does not provision. Putting the agent key on a device
is the one act in this whole design that belongs to the owner, and `bin/idp-mac-secret-deliver`
already refuses an agent session by design. A route that could provision would be a route that
can make any caller trustworthy, which is the property the broker exists to deny.

CONFIG (LAW 46): none. The path to `bin/idp-jit` is derived from this file's own location, so
a worktree, a cluster sidecar and a laptop all run the copy beside them rather than a literal.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# <repo>/backstage/plugins/fleetview-backend/src/device_access.py -> <repo>
_ROOT = Path(__file__).resolve().parents[4]
_JIT = _ROOT / "bin" / "idp-jit"

# A status read is one local subprocess and must not be able to hang a page refresh. Ten
# seconds is generous for a file read and a JSON print; the only slow path would be a broker
# round trip, and `status` deliberately makes none.
_TIMEOUT_S = 10


class DeviceStatusUnavailable(RuntimeError):
    """Raised when the status could not be read at all.

    Distinct from every per-device state: 'this device is not provisioned' is an answer, and
    'the question could not be asked' is not. Collapsing them would let a broken read render
    as a permissive state, which is the one failure this surface must not have.
    """


def device_status() -> dict[str, Any]:
    """The body for `GET /api/fleetview/device-status`.

    Always answers with a `state` field naming one of the four real states, so a caller never
    has to interpret a missing field. Any inability to read becomes `unreadable` with the
    reason attached -- never a default of `active`.
    """
    if not _JIT.exists():
        raise DeviceStatusUnavailable(f"{_JIT} does not exist")

    try:
        p = subprocess.run(  # noqa: S603 - a fixed path into this checkout, no shell
            [_JIT_EXE(), str(_JIT), "status"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DeviceStatusUnavailable(f"status timed out after {_TIMEOUT_S}s") from exc
    except OSError as exc:
        raise DeviceStatusUnavailable(f"status could not run: {exc}") from exc

    if p.returncode != 0:
        raise DeviceStatusUnavailable(
            f"status exited {p.returncode}: {(p.stderr or p.stdout or '').strip()[:200]}"
        )

    try:
        doc = json.loads(p.stdout)
    except ValueError as exc:
        raise DeviceStatusUnavailable(
            f"status did not return JSON: {p.stdout[:200]}"
        ) from exc

    if not isinstance(doc, dict) or "state" not in doc:
        raise DeviceStatusUnavailable(f"status returned no state: {str(doc)[:200]}")
    return doc


def _JIT_EXE() -> str:
    """The interpreter to run `bin/idp-jit` with.

    `idp-jit` carries a `#!/usr/bin/env python3` shebang and is executable, so in principle it
    can be run directly. Calling the interpreter explicitly is what this module does instead,
    because a sidecar container has no guarantee about the exec bit surviving a ConfigMap mount
    and a 126 from a non-executable file reads exactly like a broken command.
    """
    import sys

    return sys.executable


def device_status_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/device-status`.

    200 with the state when it was read; 503 with `state: unreadable` and the reason when it was
    not. Both carry a state, so the page has one shape to render and no absent-field branch --
    `sessions_envelope`'s rule, applied to a one-device surface.
    """
    try:
        return device_status(), 200
    except DeviceStatusUnavailable as exc:
        return {"state": "unreadable", "error": str(exc)}, 503
