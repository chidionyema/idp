"""crew#483 (2026-08-27): idp#388 put `reconcile.fluxcd.io/resetAt` on HelmRelease k8s-infra to
retry an install that Kyverno had refused before its waiver existed. helm-controller resets the
failure count only when resetAt equals requestedAt (that is what `flux reconcile hr --reset`
writes), so the release never retried and the pre-waiver denial stood for 30 minutes. Rule: a
Flux resetAt or forceAt annotation in git always comes with a requestedAt of the same value."""

from pathlib import Path

import yaml

PLATFORM = Path(__file__).resolve().parents[1] / "platform"
TRIGGERS = ("reconcile.fluxcd.io/resetAt", "reconcile.fluxcd.io/forceAt")


def _annotated() -> list[tuple[str, dict]]:
    out = []
    for f in sorted(PLATFORM.rglob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            ann = (d or {}).get("metadata", {}).get("annotations") or {}
            if any(t in ann for t in TRIGGERS):
                out.append((f"{f.relative_to(PLATFORM)}:{d['kind']}/{d['metadata']['name']}", ann))
    return out


def test_every_flux_reset_or_force_annotation_pairs_a_matching_requested_at() -> None:
    found = _annotated()
    assert found, "the k8s-infra reset this test was written for is gone; delete the test with it"
    for where, ann in found:
        requested = ann.get("reconcile.fluxcd.io/requestedAt")
        for t in TRIGGERS:
            if t in ann:
                assert ann[t] == requested, f"{where}: {t}={ann[t]!r} requestedAt={requested!r}"
