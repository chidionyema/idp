"""idp#731 / idp#780 (2026-08-29): HelmRelease observability/langfuse sat InProgress after a failed
upgrade and the observability Kustomization timed out for 20 minutes at a time from ~10:14Z, because
`remediation: { retries: 3 }` was spent and helm-controller then waits for a spec change or a hand
`flux reconcile hr --reset` -- which the git-only estate cannot run (crew#483 k8s-infra and crew#227
spire were the same class). helm-controller v1.6.3, HelmRelease v2 spec, sections 'Install
remediation' and 'Upgrade remediation': "a negative integer equals to an infinite number of
retries". Every HelmRelease carries -1, so a release that failed during an outage heals when the
outage ends, and a release that is really broken stays a red row instead of a silent one."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRIES = re.compile(r"retries:\s*(-?\d+)")


def helmrelease_files():
    return sorted(
        p
        for p in (ROOT / "platform").rglob("*.yaml")
        if re.search(r"^kind: HelmRelease$", p.read_text(), re.M)
    )


def test_there_are_helmreleases_to_grade():
    assert len(helmrelease_files()) >= 20


def test_every_helmrelease_retries_forever():
    finite = {}
    for p in helmrelease_files():
        for m in RETRIES.finditer(p.read_text()):
            if int(m.group(1)) >= 0:
                finite.setdefault(str(p.relative_to(ROOT)), []).append(m.group(0))
    assert not finite, (
        f"a finite retry count strands the release after an outage (idp#731): {finite}"
    )


def test_every_helmrelease_declares_remediation():
    missing = [
        str(p.relative_to(ROOT))
        for p in helmrelease_files()
        if "remediation" not in p.read_text()
    ]
    assert not missing, (
        f"no remediation block means retries: 0, one failure and it is stuck: {missing}"
    )


def test_langfuse_names_the_incident():
    text = (ROOT / "platform/observability/langfuse.yaml").read_text()
    assert "idp#731" in text and "infinite number of retries" in text
