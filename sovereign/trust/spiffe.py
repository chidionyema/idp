"""SPIFFE identity for a sovereign agent (R31, spec v1.0 4.4).

`platform/spire/values.yaml` already runs SPIRE on the estate cluster with
trust domain `estate.internal`, and nothing under sovereign/ referenced it.
This is that reference.

What is deliberately NOT here: a hand-rolled SVID. The SPIFFE Workload API
is a gRPC service and the SPIFFE project ships the client
(`pip install spiffe`, the py-spiffe library). This module calls that
library when it is installed and a Workload API endpoint is reachable, and
otherwise returns a dev identity that says so in its own fields. It never
mints something that looks attested. LAW 43: the rejected alternative was
writing an X.509 fetch against the socket by hand, which would be a worse
copy of a CNCF-maintained client and would still not do rotation.

The dev fallback is labelled three ways at once, because one label is
something a caller can forget to read:

  source        == spiffe.dev_fallback_label ("dev-fallback")
  trusted       is False
  the ID's first path segment is spiffe.dev_path_prefix ("dev"), which no
                ClusterSPIFFEID in platform/spire/ can produce -- real IDs
                there are /ns/<namespace>/sa/<serviceaccount>.

Ghost agents: 3 missed heartbeats revokes the SVID and isolates the agent
from the bus. The registry is a small JSON file under $ESTATE_HOME so the
CLI and the worker (two processes) see the same revocations; it is state,
not an audit trail, so it is not the signed receipt chain.
"""
from __future__ import annotations

import getpass
import json
import os
import socket
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.trust import config_keys as ck

# Both separators are config keys, not literals: sovereign/config.py's
# lint refuses a bare string carrying "/" or ":" outside the config
# tables (cp22, LAW 46), and a SPIFFE ID is made of exactly those two.
_SCHEME_SUFFIX = str(ck.get("spiffe.scheme_suffix"))
_PATH_SEP = str(ck.get("trust.posix_separator"))


def trust_domain() -> str:
    return str(ck.get("spiffe.trust_domain"))


def make_id(*path_segments: str) -> str:
    scheme = str(ck.get("spiffe.scheme"))
    path = _PATH_SEP.join(str(s) for s in path_segments if s)
    return f"{scheme}{_SCHEME_SUFFIX}{trust_domain()}{_PATH_SEP}{path}"


def endpoint() -> str:
    """The Workload API endpoint: the SPIFFE-standard env var if it is
    set, else the configured default."""
    env_name = str(ck.get("spiffe.socket_env"))
    return os.environ.get(env_name) or str(ck.get("spiffe.default_socket_path"))


def _socket_path(addr: str) -> str:
    _, _, rest = addr.partition(_SCHEME_SUFFIX)
    return rest or addr


def _dev_identity(reason: str) -> dict[str, Any]:
    """An identity that is obviously not attested, and says why."""
    return {
        "spiffe_id": make_id(str(ck.get("spiffe.dev_path_prefix")), getpass.getuser(), socket.gethostname()),
        "source": str(ck.get("spiffe.dev_fallback_label")),
        "trusted": False,
        "reason": reason,
        "trust_domain": trust_domain(),
        "expires_at": None,
    }


def identity() -> dict[str, Any]:
    """This process's SPIFFE identity. Always returns a dict; `trusted` is
    True only when a SPIRE agent attested it through the Workload API."""
    addr = endpoint()
    path = _socket_path(addr)
    if not Path(path).exists():
        return _dev_identity("no workload api endpoint")
    try:
        from spiffe import WorkloadApiClient  # type: ignore
    except ImportError:
        # The socket is there but the client is not installed. Fail to a
        # labelled dev identity rather than guess at the wire format --
        # an identity nobody attested must never claim it was attested.
        return _dev_identity("py-spiffe not installed")
    try:
        with WorkloadApiClient(spiffe_socket_path=addr) as client:
            svid = client.fetch_x509_svid()
    except Exception as exc:  # pragma: no cover - needs a live SPIRE agent
        return _dev_identity(f"workload api unavailable ({exc})")
    return {
        "spiffe_id": str(svid.spiffe_id),
        "source": str(ck.get("spiffe.attested_label")),
        "trusted": True,
        "reason": None,
        "trust_domain": trust_domain(),
        "expires_at": getattr(getattr(svid, "leaf", None), "not_valid_after", None),
    }


# ---------------------------------------------------------------------------
# Ghost agent detection: 3 missed heartbeats = SVID expiry.
# ---------------------------------------------------------------------------


def _registry_path() -> Path:
    return config.SOVEREIGN_HOME / str(ck.get("spiffe.registry_filename"))


def _load() -> dict[str, Any]:
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True))
    os.replace(tmp, path)


def beat(spiffe_id: str, now: float | None = None) -> dict[str, Any]:
    """Record a heartbeat. Clears the missed count. A revoked identity is
    NOT resurrected by a heartbeat -- re-attestation is SPIRE's job, not a
    liveness ping's, or a ghost that starts breathing again would let
    itself back onto the bus."""
    data = _load()
    entry = data.get(spiffe_id) or {}
    if entry.get("revoked"):
        return dict(entry)
    entry["last_beat"] = now if now is not None else time.time()
    entry["missed"] = 0
    entry["revoked"] = False
    data[spiffe_id] = entry
    _save(data)
    return dict(entry)


def miss(spiffe_id: str) -> dict[str, Any]:
    """Record one missed heartbeat, revoking at the configured limit."""
    limit = int(ck.get("spiffe.max_missed_heartbeats"))
    data = _load()
    entry = data.get(spiffe_id) or {"last_beat": None, "missed": 0, "revoked": False}
    entry["missed"] = int(entry.get("missed", 0)) + 1
    if entry["missed"] >= limit:
        entry["revoked"] = True
        entry["revoked_at"] = time.time()
    data[spiffe_id] = entry
    _save(data)
    return dict(entry)


def sweep(now: float | None = None) -> list[str]:
    """Charge a missed heartbeat to every identity whose last beat is
    older than one interval, and return the ids revoked by this sweep.
    This is the scheduled half: `miss()` is for a caller that already
    knows a beat did not arrive."""
    interval = float(ck.get("spiffe.heartbeat_interval_s"))
    now = now if now is not None else time.time()
    revoked_now: list[str] = []
    for spiffe_id, entry in sorted(_load().items()):
        if entry.get("revoked"):
            continue
        last = entry.get("last_beat")
        if last is None or (now - float(last)) > interval:
            after = miss(spiffe_id)
            if after.get("revoked"):
                revoked_now.append(spiffe_id)
    return revoked_now


def is_revoked(spiffe_id: str) -> bool:
    entry = _load().get(spiffe_id) or {}
    return bool(entry.get("revoked"))


def status(spiffe_id: str | None = None) -> dict[str, Any]:
    data = _load()
    if spiffe_id is None:
        return data
    return dict(data.get(spiffe_id) or {})
