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
                    out.append(
                        (
                            wf.name,
                            job_name,
                            step.get("name") or "<unnamed>",
                            step["run"],
                        )
                    )
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
            # A `cosign` inside a quoted string is TEXT, not a command: the retry
            # loop's `echo "cosign sign failed twice"` and the printed repro
            # instructions both mention it without running it. Judging those as
            # invocations fails a workflow that is correct, which is its own
            # outage (LAW 38). Strip quoted spans before deciding, then match the
            # flags against the original line -- flags are never quoted.
            bare = re.sub(r"\"[^\"]*\"|'[^']*'", " ", stripped)
            if re.search(rf"\bcosign\s+{verb}\b", bare):
                found.append((wf, job, step, stripped))
    return found


def test_signing_does_not_depend_on_a_tuf_signing_config():
    """`--use-signing-config` defaults true in v3.0.6 and its own help says it requires
    the new bundle format. Left on, it contradicts the flag above."""
    for wf, job, step, line in _cosign_invocations("sign"):
        assert "--use-signing-config=false" in line, f"{wf}:{job}:{step}: {line}"
