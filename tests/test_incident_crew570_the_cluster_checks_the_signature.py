"""crew#570 CP4, 2026-08-28: the estate signs every image it builds and the cluster never looked.

Measured against the live cluster on 2026-08-28: `verifyImages` rules = 0. Meanwhile
build-multiarch.yml signs each pushed digest with keyless cosign and verifies it in the same run
(run 33166323423, "Verification for ghcr.io/chidionyema/sovereign-worker@sha256:346446686948..."
at 11:14:37Z), and hermes-v2's build-agent-image.yml does the same for hermes-agent. Admission
then accepted whatever the tag happened to point at. The attacker's move was never to forge the
signature; it was to push an unsigned image under the same name.

The dangerous half of closing that hole is the scope. `ghcr.io/chidionyema/*` is the obvious
pattern and it is wrong: three images under that prefix are signed by nobody, and an Enforce rule
matching them takes DNS and the catalogue down at the next pod restart (LAW 38 -- a guard that
refuses correct work is an outage). So the enforced set has to be exactly the set CI signs, and
it has to STAY exactly that set: add a Dockerfile to this repo and the policy must grow with it,
or the next image ships unverified and nothing says so.

These tests derive the signed set from the things that actually do the signing -- `bin/dockerfiles`
(the same command build-multiarch.yml's `discover` job runs) and the two workflows' cosign
invocations -- and hold the policy to it. They read no prose and trust no comment.
"""
import fnmatch
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

IDP = Path(__file__).resolve().parents[1]
POLICY = IDP / "platform" / "edge" / "verify-image-signatures.yaml"
BUILD_WORKFLOW = IDP / ".github" / "workflows" / "build-multiarch.yml"
KUSTOMIZATION = IDP / "platform" / "edge" / "kustomization.yaml"
MANIFEST_ROOTS = ["platform", "clusters", "backstage"]
REGISTRY_PREFIX = "ghcr.io/chidionyema/"
ISSUER = "https://token.actions.githubusercontent.com"

# Images under our own registry prefix that NO workflow signs. Enforcing on these is the outage.
# Each is here because a search for a workflow that pushes it came back empty, not because it was
# inconvenient: only build-multiarch.yml (idp) and build-agent-image.yml (hermes-v2) run
# `cosign sign` anywhere in the estate.
UNSIGNED = {
    "ghcr.io/chidionyema/mirror/external-dns",
    "ghcr.io/chidionyema/idp/estate-catalog",
    "ghcr.io/chidionyema/idp/estate-db",
}


@pytest.fixture(scope="module")
def policy():
    doc = yaml.safe_load(POLICY.read_text())
    assert doc["kind"] == "ClusterPolicy", doc["kind"]
    return doc


def _image_rules(policy):
    """(rule name, the one verifyImages entry) for every rule in the policy."""
    out = []
    for rule in policy["spec"]["rules"]:
        entries = rule.get("verifyImages") or []
        assert len(entries) == 1, f"{rule['name']} has {len(entries)} verifyImages entries"
        out.append((rule["name"], entries[0]))
    return out


def _bare(pattern: str) -> str:
    """`ghcr.io/chidionyema/backstage:*` -> `ghcr.io/chidionyema/backstage`."""
    return re.split(r"[:@]", pattern)[0]


def _covers(pattern: str, image: str) -> bool:
    """Does this imageReferences pattern reach this repository?

    Kyverno matches imageReferences as globs, so `ghcr.io/chidionyema/*` reaches every image in
    the estate. Comparing the two as strings is the silent miss case: it would call a blanket
    pattern "not the unsigned image" and pass while the rule refuses it at admission.
    """
    return fnmatch.fnmatchcase(image, _bare(pattern))


def _enforced_repos(policy) -> set[str]:
    return {_bare(p)
            for name, e in _image_rules(policy) if e.get("failureAction") == "Enforce"
            for p in e["imageReferences"]}


def _images_ci_signs() -> set[str]:
    """The set of images that something in this estate actually runs `cosign sign` on.

    idp: whatever `bin/dockerfiles` discovers, named ghcr.io/<owner>/<name> by build-multiarch.yml.
    hermes-v2: the single IMAGE its build-agent-image.yml declares. That repo is not checked out
    here, so its one image is named as a constant and asserted against the idp side below.
    """
    out = subprocess.run([str(IDP / "bin" / "dockerfiles"), "--json"],
                         capture_output=True, text=True, cwd=IDP, timeout=60)
    assert out.returncode == 0, out.stderr
    idp = {REGISTRY_PREFIX + d["name"] for d in json.loads(out.stdout)}
    return idp | {"ghcr.io/chidionyema/hermes-agent"}


def _manifest_images() -> set[str]:
    """Every ghcr.io/chidionyema image this repo asks the cluster to run."""
    found = set()
    pattern = re.compile(re.escape(REGISTRY_PREFIX) + r"[a-z0-9._/-]+")
    for root in MANIFEST_ROOTS:
        for f in (IDP / root).rglob("*"):
            if not f.is_file() or f.suffix not in {".yaml", ".yml"}:
                continue
            for m in pattern.findall(f.read_text(errors="ignore")):
                found.add(_bare(m).rstrip("./-"))
    return found


def test_the_enforced_set_is_exactly_what_ci_signs(policy):
    """The anti-drift assertion. Add a Dockerfile and this fails until the policy names it --
    which is the only thing standing between a new image and shipping unverified."""
    assert _enforced_repos(policy) == _images_ci_signs()


def test_no_image_is_enforced_against_a_signature_that_does_not_exist(policy):
    """The other direction: enforcing on an unsigned image is a self-inflicted outage."""
    enforced_patterns = [p for name, e in _image_rules(policy)
                         if e.get("failureAction") == "Enforce" for p in e["imageReferences"]]
    reached = {image for image in UNSIGNED
               for p in enforced_patterns if _covers(p, image)}
    assert reached == set(), f"Enforce reaches unsigned images: {sorted(reached)}"


def test_every_estate_image_is_classified_by_some_rule(policy):
    """No silent miss case. An image that matches no rule at all is admitted unverified and
    produces no PolicyReport row either, so nobody ever learns it was skipped."""
    rules = _image_rules(policy)
    for image in _manifest_images():
        matched = [name for name, e in rules
                   if any(_covers(p, image) for p in e["imageReferences"])]
        assert matched, f"{image} matches no rule in {POLICY.name}"


def test_the_unsigned_three_are_audited_not_ignored(policy):
    """They are excluded from Enforce, which is correct, and they must still be counted."""
    audit = [e for name, e in _image_rules(policy) if e.get("failureAction") == "Audit"]
    assert audit, "nothing audits the images we do not enforce on"
    catch_all = [e for e in audit if REGISTRY_PREFIX + "*" in e["imageReferences"]]
    assert catch_all, "the audit rule does not cover the whole registry prefix"
    for e in catch_all:
        skipped = {_bare(p) for p in e.get("skipImageReferences", [])}
        assert skipped == _enforced_repos(policy), (
            "the audit rule must skip exactly what the Enforce rules already cover, so every "
            "other estate image is a PolicyReport row")
        for image in UNSIGNED:
            assert image not in skipped, f"{image} is skipped by both Enforce and Audit"


def test_verify_digest_is_off_everywhere(policy):
    """Every manifest in this repo pins images by TAG (backstage main-1450). verifyDigest: true
    demands a digest reference and would refuse all four signed images on the spot."""
    for name, e in _image_rules(policy):
        assert e.get("verifyDigest") is False, f"{name} sets verifyDigest {e.get('verifyDigest')!r}"


def test_every_attestor_pins_an_identity_and_the_github_issuer(policy):
    """Without --certificate-identity-regexp, cosign accepts any certificate in the public Fulcio
    root -- every GitHub repository there is -- so an image signed by a stranger passes. The
    identity is the whole check; build-multiarch.yml already verifies with this same pair."""
    for name, e in _image_rules(policy):
        entries = [entry for a in e["attestors"] for entry in a["entries"]]
        assert entries, f"{name} has no attestor entries"
        for entry in entries:
            keyless = entry["keyless"]
            assert keyless["issuer"] == ISSUER, (name, keyless.get("issuer"))
            assert keyless["subject"].startswith("https://github.com/chidionyema/"), (
                name, keyless["subject"])
            assert keyless["subject"] != "*", name


def test_the_idp_images_are_pinned_to_the_idp_workflow(policy):
    """Folding hermes-agent into the idp identity would accept an idp-signed image under the
    hermes-agent name AND refuse the real hermes-agent build. They are different repositories."""
    by_repo = {}
    for name, e in _image_rules(policy):
        if e.get("failureAction") != "Enforce":
            continue
        subjects = {entry["keyless"]["subject"] for a in e["attestors"] for entry in a["entries"]}
        assert len(subjects) == 1, f"{name} accepts {len(subjects)} identities"
        for p in e["imageReferences"]:
            by_repo[_bare(p)] = subjects.pop() if subjects else None
            subjects = {by_repo[_bare(p)]}
    assert by_repo["ghcr.io/chidionyema/hermes-agent"].startswith(
        "https://github.com/chidionyema/hermes-v2/")
    for image in _images_ci_signs() - {"ghcr.io/chidionyema/hermes-agent"}:
        assert by_repo[image].startswith("https://github.com/chidionyema/idp/"), image


def test_the_policy_is_reconciled(policy):
    """A policy file no kustomization lists is a file, not a control. crew#483 is the incident:
    the cluster is what enforces, and Flux is what puts it there."""
    listed = yaml.safe_load(KUSTOMIZATION.read_text())["resources"]
    assert POLICY.name in listed, listed


def test_background_scanning_is_off(policy):
    """verifyImages reaches a registry and a transparency log; Kyverno will not run these rules
    in a background scan, and declaring background: true makes the policy look like it covers
    already-running pods when it covers only admission."""
    assert policy["spec"]["background"] is False
