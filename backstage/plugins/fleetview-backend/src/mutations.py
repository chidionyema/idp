"""FleetView door onto the typed multi-domain mutation ledger (docs/tickets/2026-09-15-typed-
multidomain-mutation-ledger.md, "The door").

Before this file, `propose_mutation`/`verify_mutation`/`seal_mutation`/`admit_mutation`
(`platform/executor/daemon.py`) had no Backstage surface at all -- grep across
`backstage/packages/app/src` and `backstage/plugins` for `propose|mutation` matched nothing
outside `node_modules`. A person could only reach them from an MCP tool call, which is exactly
the gap the standing rule about doors exists to catch. This module is the read/act half; the
"Pending mutations" card in `EstatePage`'s consuming pages is the door itself.

No second gauntlet, no second transport (LAW 43): this module never re-implements
`verify()`/`sign()`/`verify_attestation()`. It reads the same on-disk records
`platform/executor/daemon.py` already writes under `ledger_root()`, and for the two mutating
actions (approve, reject) it speaks the exact same JSON-over-AF_UNIX protocol
`mcp/plugins/estate_executor.py`'s `_verifier_call` speaks to the one executor daemon.

Why a ledger's per-domain verdict can be reported without re-running the gauntlet: `verify()`
writes `staged/<ledger_id>.patch` on exactly one path -- an all-or-nothing pass across every
domain the proposal named (`_seal_mutation`'s own docstring: "that file existing is what proves
verify_mutation ran and passed"). So `staged/<ledger_id>.patch` existing is not a guess at the
per-domain outcome, it is the same fact `seal_mutation`/`admit_mutation` already trust before
acting -- every domain the proposal listed is "VERIFIED", or the file would not be there.

"Approve and merge" never calls `admit_mutation` on the agent's own initiative -- there is no
autonomous loop anywhere in this plugin that reaches `approve()`. It exists to be the target of
one human's button press in Backstage, which is "the founder's own merge path" the spec
requires: `admit_mutation` still only ever produces a new branch and a commit, `pr_required:
True`, never a merge to `main` -- this module changes who is allowed to press the button, not
what the button does.

CONFIG (LAW 46): `IDP_EXECUTOR_RUNS` / `IDP_EXECUTOR_SOCKET`, the same two variables
`platform/executor/daemon.py` and `mcp/plugins/estate_executor.py` already read -- a second
default here would be a second place this estate's ledger path could drift from the daemon's.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any


class InvalidQuery(ValueError):
    """Raised for a request naming no ledger -- routes.py turns this into 400."""


class LedgerUnavailable(RuntimeError):
    """Raised when the executor daemon is not answering -- routes.py turns this into 503, the
    same status `blast_radius_envelope` already uses for "could not be read"."""


def _ledger_root() -> Path:
    runs = os.environ.get("IDP_EXECUTOR_RUNS") or os.path.expanduser("~/.estate/runs")
    return Path(runs) / "ledgers"


def _executor_socket() -> Path:
    return Path(
        os.environ.get(
            "IDP_EXECUTOR_SOCKET", str(Path.home() / ".estate" / "executor.sock")
        )
    )


def _call_executor(payload: dict[str, Any]) -> dict[str, Any]:
    """One request, one reply, to the same socket `_verifier_call` in estate_executor.py speaks
    to. Duplicated rather than imported: that module lives outside this plugin's package and
    importing across the two would be the second transport LAW 43 forbids in the other
    direction -- this is the same six lines of socket handling, not a second protocol."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(55)
        sock.connect(str(_executor_socket()))
        sock.sendall((json.dumps(payload) + "\n").encode())
        raw = b""
        while b"\n" not in raw:
            chunk = sock.recv(65536)
            if not chunk:
                break
            raw += chunk
        sock.close()
    except OSError as exc:
        raise LedgerUnavailable(
            f"the executor is not answering on {_executor_socket()}: {exc}"
        ) from exc
    try:
        return json.loads(raw.decode().splitlines()[0])
    except (ValueError, IndexError) as exc:
        raise LedgerUnavailable(
            "the daemon answered something that is not JSON"
        ) from exc


def _per_domain(domains: list[str], verified: bool) -> dict[str, str]:
    if verified:
        return {d: "VERIFIED" for d in domains}
    return {d: "not yet verified" for d in domains}


def list_pending() -> list[dict[str, Any]]:
    """Every mutation ledger still open: proposed, and either awaiting verification or verified
    and awaiting the founder's approve/reject. A ledger that failed verification or was already
    admitted has no `proposals/<id>.json` left -- `_verify_mutation`/`_admit_mutation` unlink it
    on both of those paths, so this listing needs no separate status field to hide those rows;
    they are simply gone, the same way a spent job leaves no row in `read_job`'s mailbox.
    """
    proposals_dir = _ledger_root() / "proposals"
    staged_dir = _ledger_root() / "staged"
    if not proposals_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for entry in sorted(proposals_dir.glob("*.json")):
        ledger_id = entry.stem
        try:
            with open(entry) as handle:
                proposal = json.load(handle)
        except (OSError, ValueError):
            continue
        domains = proposal.get("domains", [])
        verified = (staged_dir / f"{ledger_id}.patch").exists()
        rows.append(
            {
                "ledger_id": ledger_id,
                "claim": proposal.get("claim", ""),
                "domains": domains,
                "status": "verified" if verified else "pending_verification",
                "per_domain": _per_domain(domains, verified),
            }
        )
    return rows


def approve(ledger_id: str) -> dict[str, Any]:
    """Seal, then admit, the founder's own ledger -- called only from the button, never from an
    agent's own task loop. Refuses (rather than guessing) a ledger that is not yet verified: an
    approve on an unverified ledger would otherwise hang on `seal_mutation`'s own "no verified
    bundle" refusal, which is the correct answer but not one this door should make the caller
    decode -- checked here so the reply is unambiguous.
    """
    if not ledger_id:
        raise InvalidQuery("approve needs a ledger_id")
    staged_path = _ledger_root() / "staged" / f"{ledger_id}.patch"
    if not staged_path.exists():
        return {
            "ok": False,
            "error": f"ledger {ledger_id!r} is not verified yet; nothing to approve",
        }
    seal = _call_executor({"verb": "seal_mutation", "ledger_id": ledger_id})
    if not seal.get("ok"):
        return seal
    return _call_executor(
        {
            "verb": "admit_mutation",
            "ledger_id": ledger_id,
            "attestation": seal.get("attestation"),
        }
    )


def reject(ledger_id: str) -> dict[str, Any]:
    """Withdraw a pending ledger. No git object is ever touched -- a ledger that was never
    admitted has produced no branch and no commit (see this module's own docstring), so
    rejecting one is deleting the proposal record and its staged bundle, nothing more.
    """
    if not ledger_id:
        raise InvalidQuery("reject needs a ledger_id")
    proposal_path = _ledger_root() / "proposals" / f"{ledger_id}.json"
    if not proposal_path.exists():
        return {"ok": False, "error": f"no pending ledger {ledger_id!r}"}
    staged_path = _ledger_root() / "staged" / f"{ledger_id}.patch"
    proposal_path.unlink()
    if staged_path.exists():
        staged_path.unlink()
    return {"ok": True, "ledger_id": ledger_id, "rejected": True}
