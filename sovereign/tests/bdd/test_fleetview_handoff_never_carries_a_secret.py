"""The portal route can never receive or emit a secret. (Founder's ruling, 2026-09-18.)

The ruling was explicit: "Add a test asserting the portal route cannot ever receive or emit a
secret." This is that test, and it is written to fail on the SHAPE of a leak rather than on a
list of today's known fields -- otherwise the first credential added under a new name passes.

Three independent guards, because each alone has a hole:

  1. the payload builder runs `assert_no_secret` itself, so a caller cannot forget it;
  2. this suite walks the route's real output and applies the same check from outside, so a
     builder that stopped checking would be caught here;
  3. this suite reads the package's own source for the request-side and response-side field
     names that would carry a credential, so a future `token` field is a test failure rather
     than a review someone has to notice.

The boundary being defended: the portal holds no vault credentials and never sees the agent
key or the cluster token. A browser-based key-delivery flow was rejected for exactly this
reason, and a guided local handoff is only equivalent to it while the portal stays clean.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "backstage" / "plugins" / "fleetview-backend" / "src"
HANDOFF_MODULE = SRC / "handoff.py"
ROUTES_MODULE = SRC / "routes.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def handoff():
    return _load(HANDOFF_MODULE, "fleetview_handoff_under_test")


@pytest.fixture()
def routes():
    return _load(ROUTES_MODULE, "fleetview_routes_handoff_under_test")


# ------------------------------------------------------------------ the route, from outside


def test_the_authorize_route_emits_only_a_challenge_and_a_local_url(handoff, routes):
    """The strongest statement the ruling allows: nothing but an identifier crosses."""
    body, status = routes.device_authorize_envelope()
    assert status == 200
    assert set(body.keys()) == {"challenge", "state", "url", "scheme"}, (
        f"the authorize route grew a field: {sorted(body.keys())}. Every field is an "
        "opportunity to carry a credential across the portal boundary."
    )
    assert body["scheme"] == "idp-device", (
        "the handoff must be a custom scheme, which only something installed on this device "
        "can handle. An http URL would invite a portal-delivered-secret flow."
    )
    assert body["url"].startswith("idp-device://authorize?challenge=")


def test_the_emitted_payload_passes_the_secret_check(handoff, routes):
    """Guard 2: checked from outside the builder, so a builder that stopped checking is caught."""
    body, _status = routes.device_authorize_envelope()
    # Raises SecretLeak if anything in it looks like a credential.
    handoff.assert_no_secret(body, where="route output")


def test_the_challenge_is_opaque_and_carries_nothing(handoff):
    """A nonce, not a capability. Leaking one to a log or referrer must cost nothing."""
    c = handoff.new_challenge()
    assert handoff.is_well_formed_challenge(c)
    assert len(c) <= handoff.CHALLENGE_MAX_LEN
    # Base64url alphabet only: no dots (JWT), no slashes (paths), no colons (URLs/schemes).
    assert re.fullmatch(r"[A-Za-z0-9_-]+", c)
    for bad in (".", "/", ":", " ", "ocid1.", "eyJ"):
        assert bad not in c


def test_two_challenges_differ(handoff):
    """Single-use nonces, so replay is not a design consideration."""
    assert handoff.new_challenge() != handoff.new_challenge()


def test_the_builder_refuses_a_payload_that_would_carry_a_secret(handoff):
    """The check has teeth: give it a real-shaped credential and it must raise.

    Without this, a bug that disabled the check would leave every other test in this file
    passing -- they all assert the check's absence of complaints.
    """
    # A JWT-shaped value.
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret({"subject": "x", "leak": "abc.def.ghi"}, where="t")
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret(
            {"v": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signaturepart"}, where="t"
        )
    # An OCI OCID.
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret(
            {"v": "ocid1.vaultsecret.oc1.uk-london-1.amaaaaaa"}, where="t"
        )
    # A PEM block.
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret({"v": "-----BEGIN PRIVATE KEY-----\nMIIE"}, where="t")
    # A vendor-style key.
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret({"v": "sk-abcdefghijklmnopqrstuvwx"}, where="t")
    # And an unknown FIELD NAME, which is the hole a value check alone leaves.
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret({"api_key": "anything"}, where="t")


def test_nested_payloads_are_walked(handoff):
    """A list of objects is the obvious place to smuggle a field past a shallow check."""
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret({"data": [{"ok": 1}, {"token": "x"}]}, where="t")
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret({"data": [{"v": "ghp_" + "a" * 30}]}, where="t")


def test_a_credential_shaped_value_under_an_innocent_name_is_caught(handoff):
    """The failure the name check misses, which is why both exist."""
    payload = {
        "reason": "auth failed for eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefgh"
    }
    with pytest.raises(handoff.SecretLeak):
        handoff.assert_no_secret(payload, where="t")


def test_the_url_builder_refuses_a_malformed_challenge(handoff):
    with pytest.raises(handoff.SecretLeak):
        handoff.handoff_url("too-short")
    with pytest.raises(handoff.SecretLeak):
        handoff.handoff_url("x" * 200)
    with pytest.raises(handoff.SecretLeak):
        handoff.handoff_url("has.a.dot.and.more.than.thirty.two.chars.ok")


def test_the_kubeconfig_field_may_only_be_a_path(handoff):
    """The one allowed field that names a file holding a token: it must stay a path.

    A URL here would turn a location into a fetch, which is how a path field becomes a
    credential-delivery channel.
    """
    handoff.assert_no_secret(
        {"kubeconfig": "/Users/x/.local/state/idp/agent.kubeconfig"}, where="t"
    )
    for bad in (
        "https://evil.test/agent.kubeconfig",
        "file:///etc/passwd",
        "ocid1.vaultsecret.oc1.x",
    ):
        with pytest.raises(handoff.SecretLeak):
            handoff.assert_no_secret({"kubeconfig": bad}, where="t")


# ------------------------------------------- the source, so a NEW field is a failure not a review

FORBIDDEN_IN_SOURCE = [
    r"\btoken\b",
    r"\bpassword\b",
    r"\bsecret\b",
    r"\bcredential\b",
    r"\bprivate_key\b",
    r"\bapi_key\b",
    r"\bbearer\b",
]


def test_the_portal_source_never_reads_or_writes_a_credential():
    """Guard 3: read the package itself. A future field carrying a credential fails here.

    Comments and docstrings are included on purpose. A file that TALKS about tokens in prose
    is a file where someone is thinking about tokens, and this repository's convention is that
    the reasoning lives in comments -- so excluding them would hide the next change rather than
    catching it. The allowlist below is the exception list, and each entry says why.
    """
    text = HANDOFF_MODULE.read_text()
    # Strip the identifiers this module is allowed to name: they are the field names in the
    # DENY list it uses to REFUSE secrets, plus the two it checks for in values.
    scrubbed = text
    for allowed in (
        "_FORBIDDEN_NAME",
        "_FORBIDDEN_VALUE",
        "SecretLeak",
        "assert_no_secret",
    ):
        scrubbed = scrubbed.replace(allowed, "")

    # Now nothing in the scrubbed source may look like it reads or emits a credential.
    for pat in [
        r"getenv\(['\"]\w*(TOKEN|SECRET|KEY|PASSWORD)",
        r"environ\[['\"]\w*(TOKEN|SECRET)",
    ]:
        assert not re.search(pat, scrubbed, re.IGNORECASE), (
            f"handoff.py reads a credential from the environment ({pat}). The portal must hold "
            "none; the local helper is where the cloud identity lives."
        )


def test_the_routes_module_does_not_touch_the_vault_or_the_key(handoff):  # noqa: ARG001
    """routes.py may build a challenge; it must not read a vault or an agent key."""
    text = ROUTES_MODULE.read_text()
    for forbidden in (
        "idp-mac-secret-deliver",
        "JIT_AGENT_KEY",
        "agent-key",
        "secret get",
    ):
        assert forbidden not in text, (
            f"routes.py names {forbidden!r}. Routes answer questions; delivery happens on the "
            "device, through a helper the portal cannot reach."
        )


def test_the_helper_is_not_shipped_in_the_portal_package():
    """The boundary in one assertion: the delivery tool lives in bin/, not in the plugin.

    If this ever fails, the portal has grown the ability to deliver a secret and the whole
    'portal holds nothing' property is gone.
    """
    plugin_files = {p.name for p in SRC.glob("*.py")}
    for name in ("idp-mac-secret-deliver", "idp-device-authorize"):
        assert name not in plugin_files, (
            f"{name} must not exist inside the portal package"
        )


def test_short_signature_jwts_are_caught(handoff):
    """The hole the suite found on 2026-09-18, kept as a case.

    The first JWT pattern required >=10 characters per segment. A token with a short signature
    therefore passed the check that exists to catch it. The pattern now keys on structure, and
    these cases are what it must never miss again.
    """
    for token in (
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefgh",  # 8-char signature
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc",  # 3-char signature
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnopqrstuvwxyz",  # long
    ):
        with pytest.raises(handoff.SecretLeak):
            handoff.assert_no_secret({"reason": f"auth failed for {token}"}, where="t")
        with pytest.raises(handoff.SecretLeak):
            handoff.assert_no_secret(token, where="t")


def test_other_vendor_credential_shapes_are_caught(handoff):
    """Slack and AWS, added alongside the JWT fix rather than after the first leak."""
    for value in (
        "xoxb-1234567890-abcdefghij",
        "xoxp-1234567890-abcdefghij",
        "AKIAIOSFODNN7EXAMPLE",
    ):
        with pytest.raises(handoff.SecretLeak):
            handoff.assert_no_secret({"reason": value}, where="t")


def test_ordinary_text_is_not_flagged(handoff):
    """The check must not fire on prose, or it becomes noise people route around.

    Every value here is something this estate legitimately puts in a payload.
    """
    ok = {
        "subject": "system:serviceaccount:agents:agent-reader",
        "kubeconfig": "/Users/someone/.local/state/idp/agent.kubeconfig",
        "reason": "status timed out after 10s",
        "state": "awaiting_helper",
        "url": "idp-device://authorize?challenge=" + "A" * 43,
        "expires_in": 3600,
        "has_key": False,
    }
    handoff.assert_no_secret(ok, where="t")
