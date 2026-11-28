"""The operational verdict on its real path: three sigstore bundles, three issuers, no key.

Founder ruling (#8759, 2026-11-28): the HMAC custody model is deleted. A receipt verifies
only as a sigstore bundle signed by a short-lived identity the control plane issued, and the
verifier holds no secret: no key is read, and there is no verifier key to lose.

The sigstore tools (`gh attestation verify`, `cosign verify-blob-attestation`) are the trust
boundary with the Fulcio root and the transparency log, so the tests replace that one call
with a local double doing the same three checks offline: the certificate identity, the OIDC
issuer and the DSSE signature over the signed bytes. Everything else -- the policy loader,
the issuer-distinctness rule, the bindings and the refusals -- is the production code.

The fixtures here are synthetic: a self-signed certificate and an ed25519 signature prove
the gate logic, not a physical effect. A production effect still needs a real bundle signed
by an allowlisted issuer.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.x509.oid import NameOID, ObjectIdentifier

from greenlane import github as G

HEAD = "b" * 40
REV = "a" * 40
URL = "https://production.example.test/health"
NEEDLE = "service-ready"
BODY = "service-ready\n"
ISSUE = "chidionyema/idp#8415"
LANE = "lane/proof"

# Fulcio's OIDC issuer extension. The issuer is IN the certificate, not in a secret.
OIDC_ISSUER_OID = ObjectIdentifier("1.3.6.1.4.1.57264.1.8")

# Three fixture issuers, each its own trust domain.
FIXTURE_ISSUERS = (
    ("https://signer-a.example.test/effect", "https://oidc-a.example.test"),
    ("https://signer-b.example.test/effect", "https://oidc-b.example.test"),
    ("https://signer-c.example.test/effect", "https://oidc-c.example.test"),
)


def _pae(payload: bytes) -> bytes:
    """The DSSE pre-authentication encoding: "DSSEv1" SP LEN(type) SP type SP LEN SP payload."""
    payload_type = b""
    return (
        b"DSSEv1 "
        + str(len(payload_type)).encode()
        + b" "
        + payload_type
        + b" "
        + str(len(payload)).encode()
        + b" "
        + payload
    )


def _certificate(identity: str, issuer: str) -> tuple[bytes, ed25519.Ed25519PrivateKey]:
    key = ed25519.Ed25519PrivateKey.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, identity)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(minutes=30))
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(identity)]),
            critical=False,
        )
        .add_extension(
            x509.UnrecognizedExtension(OIDC_ISSUER_OID, issuer.encode("utf-8")),
            critical=False,
        )
        .sign(key, None)
    )
    return cert.public_bytes(serialization.Encoding.PEM), key


def _statement(
    *,
    issue: str = ISSUE,
    lane: str = LANE,
    head: str = HEAD,
    tip: str = REV,
    target: str = URL,
    status: int = 200,
    body: str = BODY,
    body_sha: str | None = None,
) -> dict:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": target,
                "digest": {"sha256": hashlib.sha256(body.encode()).hexdigest()},
            }
        ],
        "predicateType": G.EFFECT_PREDICATE_TYPE,
        "predicate": {
            "issue": issue,
            "lane": lane,
            "head": head,
            "tip": tip,
            "target": target,
            "status": status,
            "body_sha256": body_sha or hashlib.sha256(body.encode()).hexdigest(),
        },
    }


def _bundle(
    identity: str,
    issuer: str,
    *,
    resign: bool = True,
    **statement_kwargs,
) -> dict:
    """A sigstore bundle: a DSSE envelope around an in-toto statement, with a certificate."""
    statement = _statement(**statement_kwargs)
    payload = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode()
    pem, key = _certificate(identity, issuer)
    signature = key.sign(_pae(payload)) if resign else b""
    return {
        "mediaType": "application/vnd.dev.sigstore.bundle.v0.3+json",
        "verificationMaterial": {"certificate": {"rawBytes": pem.decode()}},
        "dsseEnvelope": {
            "payload": base64.b64encode(payload).decode(),
            "signatures": [{"sig": base64.b64encode(signature).decode(), "keyid": ""}],
        },
    }


def _forged(bundle: dict) -> dict:
    """The same statement, re-serialized: the content holds, the signed bytes do not."""
    forged = json.loads(json.dumps(bundle))
    payload = base64.b64decode(forged["dsseEnvelope"]["payload"])
    statement = json.loads(payload)
    # Same keys, same values, different bytes: the signature no longer covers them.
    reordered = json.dumps(statement, sort_keys=False, separators=(", ", ": ")).encode()
    forged["dsseEnvelope"]["payload"] = base64.b64encode(reordered).decode()
    return forged


def _verify_double(
    bundle: dict, identity: str, issuer: str, artifact: bytes
) -> tuple[bool, str]:
    """What `gh attestation verify --cert-identity ID --cert-oidc-issuer ISSUER` checks.

    The double stands in for the tool, not for the gate: it answers only "does this bundle
    carry a certificate for this identity and issuer, does it attest this artifact, and is
    the DSSE signature over the signed bytes valid".
    """
    try:
        material = bundle["verificationMaterial"]["certificate"]["rawBytes"]
        cert = x509.load_pem_x509_certificate(material.encode())
    except (KeyError, TypeError, ValueError):
        return False, "no certificate"
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return False, "no identity"
    if identity not in [uri.value for uri in san]:
        return False, "certificate identity does not match"
    try:
        extension = cert.extensions.get_extension_for_oid(OIDC_ISSUER_OID).value
    except x509.ExtensionNotFound:
        return False, "no issuer"
    if extension.value.decode("utf-8") != issuer:
        return False, "certificate issuer does not match"
    envelope = bundle.get("dsseEnvelope")
    if not isinstance(envelope, dict):
        return False, "no DSSE envelope"
    payload = base64.b64decode(envelope.get("payload", ""))
    statement = json.loads(payload)
    digests = {
        (subject.get("digest") or {}).get("sha256")
        for subject in statement.get("subject") or []
    }
    if hashlib.sha256(artifact).hexdigest() not in digests:
        return False, "bundle does not attest this artifact"
    try:
        signature = base64.b64decode(envelope["signatures"][0]["sig"])
        cert.public_key().verify(signature, _pae(payload))
    except (KeyError, IndexError, TypeError, ValueError):
        return False, "signature does not verify"
    except Exception as exc:  # cryptography raises InvalidSignature
        return False, f"signature does not verify: {exc}"
    return True, "verified"


def _policy(pairs) -> dict:
    return {
        "version": 1,
        "signers": [
            {
                "name": f"signer-{index}",
                "certificate_identity": identity,
                "oidc_issuer": issuer,
                "state": "verified",
            }
            for index, (identity, issuer) in enumerate(pairs)
        ],
    }


def _rec(**over) -> dict:
    rec = {
        "head": HEAD,
        "tip": REV,
        "claim": ISSUE,
        "lane": LANE,
        "observed_body": BODY,
    }
    rec.update(over)
    return rec


def _use_fixture_issuers(monkeypatch, pairs=FIXTURE_ISSUERS):
    monkeypatch.setattr(G, "_verify_sigstore_bundle", _verify_double)
    monkeypatch.setattr(G, "load_effect_signer_policy", lambda *a, **k: _policy(pairs))


# -- the policy loader: a committed allowlist, never a key ----------------------------------


def test_the_committed_allowlist_is_the_only_source_of_signers():
    policy = G.load_effect_signer_policy()
    allowed = G.effect_allowed_signers(policy)
    assert allowed == [
        (
            "https://github.com/chidionyema/idp/.github/workflows/"
            "effect-receipt.yml@refs/heads/main",
            "https://token.actions.githubusercontent.com",
        )
    ], "only a verified signer is enforced"


def test_declared_signers_are_ignored_by_the_verifier():
    policy = G.load_effect_signer_policy()
    states = {
        entry.get("name"): entry.get("state")
        for entry in policy.get("signers", [])
        if isinstance(entry, dict)
    }
    assert states.get("k3s-spiffe-effect-receipt") == "declared"
    assert states.get("cloudflare-edge-effect-receipt") == "declared"
    allowed = G.effect_allowed_signers(policy)
    assert len(allowed) == 1, "a declared issuer is not an issuer"


def test_greenlane_may_never_certify_its_own_deployment():
    allowed = G.effect_allowed_signers(G.load_effect_signer_policy())
    assert not any("greenlane.yml" in identity for identity, _ in allowed)


def test_an_unreadable_allowlist_is_blind_never_empty():
    try:
        G.load_effect_signer_policy(Path("/nonexistent/effect-signers.v1.json"))
    except ValueError as exc:
        assert "unreadable" in str(exc)
    else:
        raise AssertionError("a missing allowlist must not read as an empty allowlist")


# -- the issuer-distinctness rule ------------------------------------------------------------


def test_three_issuers_are_three_proofs():
    assert G.effect_signers_are_distinct(list(FIXTURE_ISSUERS))


def test_three_bundles_from_one_issuer_are_one_issuer():
    pairs = [
        ("https://signer-a.example.test/effect", "https://oidc-one.example.test"),
        ("https://signer-b.example.test/effect", "https://oidc-one.example.test"),
        ("https://signer-c.example.test/effect", "https://oidc-one.example.test"),
    ]
    assert not G.effect_signers_are_distinct(pairs)


def test_three_github_actions_workflows_are_one_issuer():
    pairs = [
        (
            "https://github.com/chidionyema/idp/.github/workflows/a.yml@refs/heads/main",
            G.GITHUB_ACTIONS_OIDC_ISSUER,
        ),
        (
            "https://github.com/chidionyema/idp/.github/workflows/b.yml@refs/heads/main",
            G.GITHUB_ACTIONS_OIDC_ISSUER,
        ),
        (
            "https://github.com/chidionyema/idp/.github/workflows/c.yml@refs/heads/main",
            G.GITHUB_ACTIONS_OIDC_ISSUER,
        ),
    ]
    assert not G.effect_signers_are_distinct(pairs), (
        "one OIDC issuer mints every workflow identity: that is one issuer, not three"
    )


def test_two_bundles_are_never_three_proofs():
    assert not G.effect_signers_are_distinct(list(FIXTURE_ISSUERS[:2]))


# -- the verifier holds no secret -------------------------------------------------------------


def test_the_verifier_reads_no_key():
    source = Path(G.__file__).read_text()
    for name in (
        "EPISTEMIC_AUTHORITY_KEYS_JSON",
        "EPISTEMIC_QUAD_KEY_HEX",
        "EPISTEMIC_QUAD_CUSTODY_JSON",
        "EPISTEMIC_MIN_FENCE",
    ):
        assert name not in source, f"the HMAC custody model is deleted: {name}"


def test_the_tools_are_asked_for_the_allowlisted_identity_and_issuer():
    argv = G.effect_verify_argv("bundle.json", "artifact", "IDENT", "ISSUER")
    assert argv[:3] == ["gh", "attestation", "verify"]
    assert "--cert-identity" in argv and "IDENT" in argv
    assert "--cert-oidc-issuer" in argv and "ISSUER" in argv
    cosign = G.effect_verify_cosign_argv("bundle.json", "artifact", "IDENT", "ISSUER")
    assert cosign[:2] == ["cosign", "verify-blob-attestation"]
    assert "--certificate-identity" in cosign and "IDENT" in cosign
    assert "--certificate-oidc-issuer" in cosign and "ISSUER" in cosign


def test_an_absent_sigstore_tool_is_blind_never_a_pass(monkeypatch):
    def refuse(*_argv, **_kwargs):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(G.subprocess, "run", refuse)
    ok, why = G._verify_sigstore_bundle({}, "IDENT", "ISSUER", b"artifact")
    assert ok is False
    assert "did not verify" in why


# -- the known-good path: three fixture bundles from three fixture issuers --------------------


def test_three_verified_bundles_from_three_issuers_pass(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    rec = _rec(epistemic_receipts=bundles)
    assert G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE) == ""
    assert len(rec["epistemic_verified_signers"]) == 3
    assert rec["epistemic_bundles_sha256"]


# -- the falsifiers: known-bad evidence must be refused --------------------------------------


def test_three_bundles_from_one_issuer_are_refused(monkeypatch):
    pairs = [
        ("https://signer-a.example.test/effect", "https://oidc-one.example.test"),
        ("https://signer-b.example.test/effect", "https://oidc-one.example.test"),
        ("https://signer-c.example.test/effect", "https://oidc-one.example.test"),
    ]
    _use_fixture_issuers(monkeypatch, pairs)
    bundles = [_bundle(identity, issuer) for identity, issuer in pairs]
    rec = _rec(epistemic_receipts=bundles)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "ERR_EFFECT_SIGNERS_NOT_DISTINCT" in reason


def test_a_tip_mismatch_is_refused(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    bundles[1] = _bundle(FIXTURE_ISSUERS[1][0], FIXTURE_ISSUERS[1][1], tip="c" * 40)
    rec = _rec(epistemic_receipts=bundles)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "BLIND" in reason
    assert "binds another lane, tip or target" in reason


def test_a_forged_bundle_is_refused(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    bundles[2] = _forged(bundles[2])
    rec = _rec(epistemic_receipts=bundles)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "BLIND" in reason
    assert "not signed by an allowlisted issuer" in reason


def test_a_bundle_signed_by_an_unknown_issuer_is_refused(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    bundles[0] = _bundle("https://rogue.example.test/effect", "https://rogue.test")
    rec = _rec(epistemic_receipts=bundles)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "not signed by an allowlisted issuer" in reason


def test_a_bundle_that_attests_nothing_we_hold_is_refused(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    rec = _rec(epistemic_receipts=bundles, observed_body="a different body\n")
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "BLIND" in reason
    assert "artifact this verifier does not hold" in reason


def test_a_bundle_that_misstates_the_body_it_signed_is_refused(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    bundles[0] = _bundle(
        FIXTURE_ISSUERS[0][0],
        FIXTURE_ISSUERS[0][1],
        body_sha=hashlib.sha256(b"a body nobody observed").hexdigest(),
    )
    rec = _rec(epistemic_receipts=bundles)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "BLIND" in reason
    assert "misstates the body it signed" in reason


def test_two_bundles_are_refused(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS[:2]]
    rec = _rec(epistemic_receipts=bundles)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "ERR_INSUFFICIENT_RUNTIME_PROOFS" in reason


def test_the_source_plane_can_never_claim_operational_even_when_get_200(monkeypatch):
    backend = G.GitHubBackend.__new__(G.GitHubBackend)
    backend._claim_of = lambda _: ("chidionyema/idp", "8415")
    backend._contract = lambda *_: {
        "accept": (
            "GET https://raw.githubusercontent.com/chidionyema/idp/main/greenlane/"
            'github.py expect 200 contains "verify_operational" within 180m'
        ),
        "optimus": "claims.ship_contract_enforced baseline=UNKNOWN target=1",
    }
    backend._optimus_readings = lambda _: {"claims.ship_contract_enforced": 1.0}
    monkeypatch.setattr(G, "_http_get", lambda *_: (200, "verify_operational"))
    verdict, reason = backend.verify_operational("lane/source-only", {"tip": REV})
    assert verdict == "pending"
    assert "ERR_PROXY_GREEN_SUBSTITUTION" in reason


# -- the join: the receipt comes from the claim issue, and only for this lane ------------------


def _envelope(receipts, *, issue=ISSUE, lane=LANE, head=HEAD, tip=REV, target=URL):
    return {
        "issue": issue,
        "lane": lane,
        "head": head,
        "tip": tip,
        "target": target,
        "receipts": receipts,
    }


def _comment(envelope):
    return {"body": "EPISTEMIC-EFFECT-V1\n" + json.dumps(envelope)}


def _join(monkeypatch, envelope):
    body = "EPISTEMIC-EFFECT-V1\n" + json.dumps(envelope)

    def run(*argv, **_kwargs):
        endpoint = argv[2]
        if endpoint.endswith("/issues/8415"):
            return json.dumps({"comments": 1})
        if "/issues/8415/comments?per_page=100&page=1" in endpoint:
            return json.dumps([{"body": body}])
        raise AssertionError(f"unexpected read: {endpoint}")

    monkeypatch.setattr(G, "_run", run)
    backend = G.GitHubBackend.__new__(G.GitHubBackend)
    return backend._epistemic_receipts_from_claim(
        "chidionyema/idp", "8415", LANE, _rec(), URL
    )


def test_a_receipt_that_only_quotes_a_github_url_is_refused(monkeypatch):
    envelope = _envelope(
        [
            "https://github.com/chidionyema/idp/actions/runs/42",
            "https://github.com/chidionyema/idp/actions/runs/43",
            "https://github.com/chidionyema/idp/actions/runs/44",
        ]
    )
    receipts, error = _join(monkeypatch, envelope)
    assert receipts == []
    assert "ERR_PROXY_GREEN_SUBSTITUTION" in error


def test_a_receipt_that_only_quotes_a_github_url_in_a_dict_is_refused(monkeypatch):
    envelope = _envelope(
        [
            {"url": "https://github.com/chidionyema/idp/actions/runs/42"},
            {"url": "https://api.github.com/repos/chidionyema/idp/commits/main"},
            {"url": "https://raw.githubusercontent.com/chidionyema/idp/main/README.md"},
        ]
    )
    receipts, error = _join(monkeypatch, envelope)
    assert receipts == []
    assert "ERR_PROXY_GREEN_SUBSTITUTION" in error


def test_a_receipt_for_another_lane_never_replays(monkeypatch):
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    envelope = _envelope(bundles, lane="lane/other")
    receipts, error = _join(monkeypatch, envelope)
    assert receipts == []
    assert "ERR_NO_SIGNED_EFFECT_RECEIPT_FOR_EXACT_LANE" in error


def test_a_receipt_for_another_target_never_replays(monkeypatch):
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    envelope = _envelope(bundles, target="https://different.example.test/health")
    receipts, error = _join(monkeypatch, envelope)
    assert receipts == []
    assert "ERR_NO_SIGNED_EFFECT_RECEIPT_FOR_EXACT_LANE" in error


def test_two_receipts_are_never_three_proofs(monkeypatch):
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS[:2]]
    receipts, error = _join(monkeypatch, _envelope(bundles))
    assert receipts == []
    assert "ERR_EFFECT_RECEIPT_CARDINALITY" in error


# -- the verdict: the real path, from the landed lane to the posted verdict -------------------


def _backend(monkeypatch, envelope):
    body = "EPISTEMIC-EFFECT-V1\n" + json.dumps(envelope)

    def run(*argv, **_kwargs):
        endpoint = argv[2]
        if endpoint.endswith("/issues/8415"):
            return json.dumps({"comments": 1})
        if "/issues/8415/comments?per_page=100&page=1" in endpoint:
            return json.dumps([{"body": body}])
        raise AssertionError(f"unexpected read: {endpoint}")

    monkeypatch.setattr(G, "_run", run)
    backend = G.GitHubBackend.__new__(G.GitHubBackend)
    backend._claim_of = lambda _: ("chidionyema/idp", "8415")
    backend._contract = lambda *_: {
        "accept": (
            "GET https://production.example.test/health expect 200 "
            'contains "service-ready" within 180m'
        ),
        "optimus": "claims.ship_contract_enforced baseline=UNKNOWN target=1",
    }
    backend._optimus_readings = lambda _: {"claims.ship_contract_enforced": 1.0}
    monkeypatch.setattr(G, "_http_get", lambda *_: (200, BODY))
    return backend


def test_the_verdict_passes_on_three_verified_bundles_from_three_issuers(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    backend = _backend(monkeypatch, _envelope(bundles))
    rec = {"head": HEAD, "tip": REV}
    verdict, why = backend.verify_operational(LANE, rec)
    assert verdict == "pass", why
    assert "sigstore bundles=3" in why
    assert len(rec["epistemic_verified_signers"]) == 3
    assert "epistemic_receipts" not in rec


def test_the_verdict_stays_pending_on_a_forged_bundle(monkeypatch):
    _use_fixture_issuers(monkeypatch)
    bundles = [_bundle(identity, issuer) for identity, issuer in FIXTURE_ISSUERS]
    bundles[0] = _forged(bundles[0])
    backend = _backend(monkeypatch, _envelope(bundles))
    verdict, why = backend.verify_operational(LANE, {"head": HEAD, "tip": REV})
    assert verdict == "pending", why
    assert "BLIND" in why
