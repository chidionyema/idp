"""The portal must never receive or emit a secret. This module is where that is enforced.

THE RULING (founder, 2026-09-18). The portal's strongest property is that it holds no vault
credentials and never sees the agent key or the cluster token. `[Authorize this device]` must
not become a browser-based key-delivery flow, because that would either break that property or
require enough device-bound challenge machinery that it stops being a simple button. So:

  * the portal passes ONLY an opaque challenge identifier: never a key, a token, a vault
    credential, or a path to one;
  * a local helper on the device performs the actual delivery through the existing
    `bin/idp-mac-secret-deliver` path, which still refuses an agent session by design;
  * the button degrades to a guided "install/run this helper" step when no handler is present.

WHY A MODULE AND NOT JUST A CONVENTION. A convention is a thing a future change can quietly
break: one `secret` field in a response body, one query parameter carrying a token, and the
property is gone with no test to notice. `assert_no_secret` and `challenge_for` are total
functions that a test suite can hold every route to, and `test_fleetview_device_access.py`
does exactly that -- including reading this package's own source for the field names it must
never emit.

WHAT A CHALLENGE IS. A nonce: random, single-use, expiring, and carrying nothing but its own
identity. It is what the helper proves possession of when it asks the broker for the identity.
It is deliberately NOT a capability: holding it grants nothing on its own, so leaking it to a
log or a referrer costs nothing.
"""

from __future__ import annotations

import re
import secrets
from typing import Any

# A challenge lives ten minutes. Long enough to open a helper and finish, short enough that one
# left in a browser history is stale before anyone could use it.
CHALLENGE_TTL_S = 600

# 32 bytes of `secrets.token_urlsafe` -> 43 chars. Bounded here so a caller cannot smuggle a
# long opaque blob (a base64 secret, say) through a field the tests expect to be an identifier.
CHALLENGE_MIN_LEN = 32
CHALLENGE_MAX_LEN = 64

# Field names that must never appear in a response this package builds. Matching is on the
# normalised name, so `accessToken`, `access_token` and `ACCESS-TOKEN` are one entry.
_FORBIDDEN_NAME = re.compile(
    r"(secret|token|password|passphrase|credential|private[_-]?key|api[_-]?key|bearer)",
    re.IGNORECASE,
)

# Values that look like the credentials themselves rather than an identifier. A JWT has two
# dots and a long middle segment; a vault OCID starts `ocid1.`; a PEM block announces itself.
#
# The JWT pattern keys on the STRUCTURE (`ey`+base64url, then a dotted payload that decodes to
# JSON) rather than on a minimum segment length. Measured 2026-09-18: a length-based pattern
# (`{10,}` per segment) let a short-signature token through, which the suite caught with
# `eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefgh` -- an 8-char signature. Real HS256 tokens
# have 43-char signatures, but "real ones are long" is not a property to stake a secret check on.
_FORBIDDEN_VALUE = [
    re.compile(
        r"\bey[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]{2,}"
    ),  # JWT, any length
    re.compile(r"\bocid1\.[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+"),  # OCI OCID
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM
    re.compile(r"\bsk-[A-Za-z0-9]{16,}"),  # vendor-style key
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub token
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack token
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
]

# The keys this module is allowed to emit. An allowlist rather than a denylist, because a
# denylist has to be updated for every new name anyone invents.
_ALLOWED_KEYS = frozenset(
    {
        "challenge",
        "scheme",
        "url",
        "state",
        "scope",
        "expires_in",
        "expires_at",
        "subject",
        "reason",
        "error",
        "kubeconfig",  # a PATH, not a credential -- asserted by shape below
        "has_key",  # a boolean: whether a key EXISTS, never the key
        "device",
        "helper",
        "helper_present",
        "installed",
    }
)

# `kubeconfig` is the one allowed key whose value names a file that does hold a token. The
# portal may show the path (it is a location, and the tile already does) but the path must look
# like a path and must not be a URL, so it cannot become a way to fetch the file.
_PATH_OK = re.compile(r"^(/|~)[\w./~-]*$")


class SecretLeak(RuntimeError):
    """Raised when something this module was asked to emit would carry a secret.

    A hard failure on purpose. A leak that is logged and allowed through is a leak, and a
    caller that catches this and continues has made the decision to ship a credential -- which
    is a decision this module exists to make impossible by accident.
    """


def new_challenge() -> str:
    """A fresh single-use nonce. Random, bounded, and carrying no information."""
    c = secrets.token_urlsafe(32)
    # token_urlsafe may strip to slightly under 43; pad deterministically to the floor so the
    # length assertion below is a property of the generator and not of chance.
    if len(c) < CHALLENGE_MIN_LEN:
        c = (c + secrets.token_urlsafe(32))[:CHALLENGE_MIN_LEN]
    return c[:CHALLENGE_MAX_LEN]


def is_well_formed_challenge(value: str) -> bool:
    """True when `value` is the shape this module issues and nothing else.

    The helper calls this before doing anything with a challenge it was handed, so a malformed
    or oversized value from a URL scheme is refused rather than passed onward.
    """
    if not isinstance(value, str):
        return False
    if not (CHALLENGE_MIN_LEN <= len(value) <= CHALLENGE_MAX_LEN):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+", value))


def assert_no_secret(payload: Any, where: str = "response") -> None:
    """Walk `payload` and raise `SecretLeak` if anything in it looks like a secret.

    Both directions are checked: a field NAME that says it holds a secret, and a VALUE shaped
    like one. The name check catches a well-meant `{"token": "..."}`; the value check catches
    the same credential under an innocent name, which is the failure a name check alone misses.
    """
    problems: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                key = str(k)
                if key not in _ALLOWED_KEYS:
                    problems.append(f"{path}.{key} is not an allowed field")
                elif _FORBIDDEN_NAME.search(key):
                    # An allowed-listed name can still be forbidden; belt and braces, so
                    # adding a name to the allowlist by mistake cannot open this hole.
                    problems.append(f"{path}.{key} names a secret")
                if key == "kubeconfig" and isinstance(v, str) and not _PATH_OK.match(v):
                    problems.append(f"{path}.{key} is not a filesystem path: {v!r}")
                walk(v, f"{path}.{key}")
        elif isinstance(node, (list, tuple)):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            for pat in _FORBIDDEN_VALUE:
                if pat.search(node):
                    problems.append(
                        f"{path} carries a value shaped like a credential: {node[:24]}..."
                    )
                    break

    walk(payload, where)
    if problems:
        raise SecretLeak("; ".join(problems))


def handoff_payload(
    challenge: str,
    *,
    state: str,
    expires_in: int | None = None,
    subject: str | None = None,
    kubeconfig: str | None = None,
) -> dict[str, Any]:
    """Build the tile's payload, then prove it carries no secret before returning it.

    Building and checking in one function means a caller cannot construct a payload and forget
    to check it. Every field is optional-by-`None` rather than omitted, so the tile has one
    shape and the forbidden-name check sees every key that could ever be present.
    """
    if not is_well_formed_challenge(challenge):
        raise SecretLeak(f"challenge is not well formed: {challenge!r}")

    payload: dict[str, Any] = {"challenge": challenge, "state": state}
    if expires_in is not None:
        payload["expires_in"] = int(expires_in)
    if subject is not None:
        payload["subject"] = subject
    if kubeconfig is not None:
        payload["kubeconfig"] = kubeconfig

    assert_no_secret(payload, where="handoff")
    return payload


def handoff_url(challenge: str, *, base: str = "idp-device://authorize") -> str:
    """The local URL the button opens. Carries the challenge and nothing else.

    A URL scheme rather than an http link on purpose: `idp-device://` can only be handled by
    something installed on this machine, which is exactly the delivery boundary the ruling
    names. An http URL would be reachable by any browser anywhere and would invite exactly the
    portal-delivered-secret flow that was rejected.
    """
    if not is_well_formed_challenge(challenge):
        raise SecretLeak(f"refusing to build a handoff URL from {challenge!r}")
    url = f"{base}?challenge={challenge}"
    assert_no_secret({"url": url}, where="handoff_url")
    return url
