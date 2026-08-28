"""crew#570 CP4: a signature only cosign can find is not a supply-chain control.

THE INCIDENT. `build-multiarch.yml` has signed every image it builds for months and
printed a full green `Verification for ... --` block each time, all three checks
passing. On 2026-08-28 a Kyverno `verifyImages` policy was pointed at one of those
images and returned:

    images-idp-builds-carry-an-idp-signature failed to verify image
    ghcr.io/chidionyema/sovereign-worker:main-814-...: no signatures found

Measured against GHCR with an authenticated pull token, for the manifest-list digest
the CI log says it signed (sha256:346446686948aa64ca8cc41bda1e34e618b512e713d58d11a
89bad1f1090c8e3, run 33166323423):

    tags/list?n=10000          608 tags, 182 of them `sha256-<hex>`, 0 ending `.sig`
    manifests/sha256-<hex>.sig 404
    referrers/<digest>         404 MANIFEST_UNKNOWN (GHCR does not serve the API)
    manifests/sha256-<hex>     200, an OCI index whose one manifest is
                               artifactType application/vnd.dev.sigstore.bundle.v0.3+json
                               with subject == the signed digest

sigstore/cosign-installer v4.1.2 installs cosign v3.0.6, where `--new-bundle-format`
defaults to TRUE (cmd/cosign/cli/options/sign.go:155). That mode writes a Sigstore
bundle referrer instead of the legacy `sha256-<hex>.sig` tag. Kyverno reads the legacy
tag, so it found nothing.

THE CLASS OF MISTAKE, which is what these tests actually guard: the job proved its own
work with the same tool that produced it. cosign wrote a format only cosign could find,
then cosign found it, and the run went green. Every check below either pins the format
a third party reads, or forces a non-cosign witness.
"""
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml")) + sorted(
    (REPO / ".github" / "workflows").glob("*.yaml")
)


def _run_scripts():
    """Every `run:` block in every workflow, as (workflow, job, step, text)."""
    out = []
    for wf in WORKFLOWS:
        doc = yaml.safe_load(wf.read_text())
        if not isinstance(doc, dict):
            continue
        for job_name, job in (doc.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if isinstance(step, dict) and isinstance(step.get("run"), str):
                    out.append((wf.name, job_name, step.get("name") or "<unnamed>", step["run"]))
    return out


def _cosign_invocations(verb):
    """Shell lines invoking `cosign <verb>`, joined across backslash continuations.

    Matching the raw text line by line would miss every flag on a continuation line,
    which is exactly how the `verify` call is written -- and a check that cannot see
    the flags would pass on a command that has none of them.
    """
    found = []
    for wf, job, step, script in _run_scripts():
        joined = re.sub(r"\\\n\s*", " ", script)
        for line in joined.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # `echo "  cosign verify ..."` is a human-facing instruction, not an
            # invocation -- it runs echo. It is checked separately, as a block,
            # by test_the_printed_repro_command_still_works: it is spread over
            # several echo lines, so line-at-a-time flag matching cannot judge it.
            if re.match(r"(echo|printf|cat)\b", stripped):
                continue
            if re.search(rf"\bcosign\s+{verb}\b", stripped):
                found.append((wf, job, step, stripped))
    return found


def test_the_repository_still_signs_something():
    """Guards the guard: if the sign step is ever deleted, the two flag tests below
    would pass vacuously on an empty list and report a supply chain that is not there."""
    assert _cosign_invocations("sign"), "no `cosign sign` anywhere in .github/workflows"


@pytest.mark.parametrize("verb", ["sign", "verify"])
def test_cosign_writes_and_reads_the_format_third_parties_read(verb):
    for wf, job, step, line in _cosign_invocations(verb):
        assert "--new-bundle-format=false" in line, (
            f"{wf}:{job}:{step}: `cosign {verb}` runs without --new-bundle-format=false. "
            "cosign v3 defaults that flag to true and stores the signature as a Sigstore "
            "bundle referrer; GHCR serves no referrers API, so Kyverno finds nothing and "
            "an Enforce policy refuses the image.\n  " + line
        )


def test_signing_does_not_depend_on_a_tuf_signing_config():
    """`--use-signing-config` defaults true in v3.0.6 and its own help says it requires
    the new bundle format. Left on, it contradicts the flag above."""
    for wf, job, step, line in _cosign_invocations("sign"):
        assert "--use-signing-config=false" in line, f"{wf}:{job}:{step}: {line}"


def test_a_non_cosign_witness_proves_the_signature_landed():
    """The heart of it. cosign verifying cosign's own output is not evidence that any
    other verifier can find the signature -- that is the exact hole this incident fell
    through. Something that is not cosign must resolve the legacy .sig tag in the same
    step, and fail the job when it cannot."""
    steps = [
        (wf, job, step, script)
        for wf, job, step, script in _run_scripts()
        if re.search(r"\bcosign\s+sign\b", script)
    ]
    assert steps, "no signing step found"
    for wf, job, step, script in steps:
        body = re.sub(r"^\s*#.*$", "", script, flags=re.M)
        assert ".sig" in body, (
            f"{wf}:{job}:{step}: nothing in the signing step names the legacy `.sig` tag, "
            "so nothing checks that a third party could find the signature."
        )
        # The tag is normally built into a shell variable first, so a witness line
        # says `"$image:$sigtag"` and never the literal `.sig`. Resolve those
        # assignments before looking, or the check only passes on one exact spelling.
        holders = {
            m.group(1)
            for m in re.finditer(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=.*\.sig", body, flags=re.M)
        }
        names = "|".join(sorted(holders)) or "\0"
        witness = re.search(
            rf"^\s*(docker|crane|oras|curl)\b.*(\.sig|\$\{{?({names})\b)", body, flags=re.M
        )
        assert witness, (
            f"{wf}:{job}:{step}: the `.sig` tag is named but only cosign ever looks at it. "
            "A verifier that is not cosign (docker/crane/oras/curl) must resolve it."
        )


def test_the_cosign_version_is_pinned_by_digest():
    """This whole incident is a default that changed under a floating tag. The installer
    stays pinned to a commit sha so the next flip is a diff, not a surprise."""
    pinned = []
    for wf in WORKFLOWS:
        for m in re.finditer(r"uses:\s*(sigstore/cosign-installer@\S+)", wf.read_text()):
            pinned.append((wf.name, m.group(1)))
    assert pinned, "no cosign-installer step found"
    for wf, ref in pinned:
        assert re.search(r"@[0-9a-f]{40}$", ref), f"{wf}: {ref} is not pinned to a commit sha"


def test_the_printed_repro_command_still_works():
    """The signing step ends by printing the command anyone can run to check the image
    themselves. With cosign v3 that command needs the same flag the job uses -- printed
    without it, it fails for the reader and reads as an unsigned image."""
    printed = [
        (wf, job, step, script)
        for wf, job, step, script in _run_scripts()
        if re.search(r"^\s*(echo|printf|cat)\b.*cosign\s+verify", script, flags=re.M)
    ]
    assert printed, "the signing step no longer tells anyone how to repeat the check"
    for wf, job, step, script in printed:
        assert "--new-bundle-format=false" in script, (
            f"{wf}:{job}:{step}: the repro command printed for humans omits "
            "--new-bundle-format=false, so following it verbatim reports no signature."
        )
