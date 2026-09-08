"""Incident 2026-09-08: Cyrus at Deployment revision 654, a new ReplicaSet every ten minutes.

Two correct controls made a loop. platform/edge/require-auto-reload.yaml stamps every workload
reloader.stakater.com/auto=true at admission, so a rotated Secret reaches the pod (crew#684).
An ExternalSecret with a generatorRef re-mints its Secret every refreshInterval by design. Put
together, Reloader rolled Cyrus on every mint: a pod that never lived long enough to finish a
job and a public door that timed out. The same pair sat on mcp/agentgateway (revision 1448),
hermes-agent-gateway (433) and otto-gateway (136), and had already been fixed once, by hand, on
the portal (platform/backstage/overlays/oke/github-token.yaml, crew#307) -- a fix nothing
generalised, so the next deck walked into it again.

This file grades the class, not the instance. A generator-minted Secret that is re-minted on a
timer must say which of two things it is:

  * ``reloader.stakater.com/ignore: "true"`` on the produced Secret (spec.target.template): the
    consumer reads the mounted file on every call, so the mint reaches it without a restart.
  * ``idp.platform/reload-on-mint`` on the ExternalSecret: the consumer reads at boot, so the
    roll on every mint is the rotation mechanism, and the author has said so in a sentence.

Silence is refused. The table is discovered from platform/, so a deck added tomorrow is graded
by the same rows; nothing below names cyrus.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
IGNORE = "reloader.stakater.com/ignore"
REASON = "idp.platform/reload-on-mint"
NEVER = {None, "0", "0s", "0m", "0h"}


def _generator_external_secrets() -> list[tuple[Path, dict]]:
    found = []
    for path in sorted(PLATFORM.rglob("*.yaml")):
        try:
            docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError:
            continue
        for doc in docs:
            if not isinstance(doc, dict) or doc.get("kind") != "ExternalSecret":
                continue
            spec = doc.get("spec") or {}
            sources = [
                e.get("sourceRef", {})
                for e in spec.get("dataFrom") or []
                if isinstance(e, dict)
            ]
            if any("generatorRef" in s for s in sources):
                found.append((path, doc))
    return found


def verdict(doc: dict) -> str | None:
    """None when the ExternalSecret is acceptable, else the sentence that says why not."""
    spec = doc.get("spec") or {}
    if str(spec.get("refreshInterval")) in {str(n) for n in NEVER}:
        return None  # minted once, never re-minted: no timer, nothing to roll on
    target_annotations = (
        ((spec.get("target") or {}).get("template") or {}).get("metadata") or {}
    ).get("annotations") or {}
    reason = (doc.get("metadata", {}).get("annotations") or {}).get(REASON, "")
    if target_annotations.get(IGNORE) == "true":
        return None
    if isinstance(reason, str) and len(reason.split()) >= 8:
        return None
    return (
        f"ExternalSecret {doc['metadata'].get('namespace')}/{doc['metadata'].get('name')} is "
        f"re-minted every {spec.get('refreshInterval')} and says nothing about Reloader: put "
        f'{IGNORE}: "true" on spec.target.template.metadata.annotations if the consumer reads the '
        f"file per call, or a sentence under metadata.annotations.{REASON} if it reads at boot"
    )


FOUND = _generator_external_secrets()


def test_the_table_is_not_empty() -> None:
    assert len(FOUND) >= 5, (
        "the discovery walked platform/ and found almost nothing; the glob is wrong"
    )


@pytest.mark.parametrize(
    "path,doc",
    FOUND,
    ids=[
        f"{d['metadata'].get('namespace')}/{d['metadata'].get('name')}"
        for _, d in FOUND
    ],
)
def test_every_timer_minted_secret_declares_what_reloader_does_with_it(
    path: Path, doc: dict
) -> None:
    problem = verdict(doc)
    assert problem is None, f"{path.relative_to(ROOT)}: {problem}"


def _external_secret(
    refresh: str, target_annotations: dict | None = None, reason: str | None = None
) -> dict:
    doc = {
        "kind": "ExternalSecret",
        "metadata": {"name": "x", "namespace": "y", "annotations": {}},
        "spec": {
            "refreshInterval": refresh,
            "target": {
                "name": "x",
                "template": {"metadata": {"annotations": target_annotations or {}}},
            },
            "dataFrom": [
                {
                    "sourceRef": {
                        "generatorRef": {"kind": "GithubAccessToken", "name": "x"}
                    }
                }
            ],
        },
    }
    if reason is not None:
        doc["metadata"]["annotations"][REASON] = reason
    return doc


def test_the_guard_refuses_the_pre_fix_shape_and_accepts_both_declarations() -> None:
    silent = _external_secret("10m")
    assert verdict(silent) is not None
    ignored = _external_secret("10m", {IGNORE: "true"})
    assert verdict(ignored) is None
    declared = _external_secret(
        "10m", reason="the consumer reads the file at boot, so the roll is the rotation"
    )
    assert verdict(declared) is None
    too_short = _external_secret("10m", reason="reloads")
    assert verdict(too_short) is not None
    once = _external_secret("0")
    assert verdict(once) is None
    wrong_place = _external_secret("10m")
    wrong_place["spec"]["template"] = {"metadata": {"annotations": {IGNORE: "true"}}}
    assert verdict(wrong_place) is not None, (
        "the annotation must sit on the produced Secret, not elsewhere"
    )
