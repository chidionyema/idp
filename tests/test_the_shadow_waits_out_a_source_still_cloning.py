"""The shadow waits for a floor source that is still cloning; it does not fail the PR on it.

Incident: 2026-09-27. shadow-verify went red on #4475, #4516 and #4535 with `the shadow floor
shadow-floor-eso-crds did not converge -- Source artifact not found, retrying in 30s`. The same
run's diagnostics showed that Kustomization Ready 18s later, `Applied revision: v2.9.0`. The ESO
repository is the largest floor clone, so its Kustomization reconciled before the GitRepository
had an artifact, kustomize-controller reported reason ArtifactFailed and retried, and wait_ks
had already returned that transient state as the verdict.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def ks(status, reason, message):
    return {
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": status,
                    "reason": reason,
                    "message": message,
                }
            ],
            "inventory": {"entries": [{"id": "crd"}]},
        }
    }


def drive(monkeypatch, shadow, states, clock_step=1.0):
    seq = iter(states)
    last = [None]

    def fake_status(name):
        last[0] = next(seq, last[0])
        return last[0]

    now = [0.0]
    monkeypatch.setattr(shadow, "ks_status", fake_status)
    monkeypatch.setattr(shadow.time, "time", lambda: now[0])
    monkeypatch.setattr(
        shadow.time, "sleep", lambda s: now.__setitem__(0, now[0] + clock_step)
    )


ARTIFACT = ks("False", "ArtifactFailed", "Source artifact not found, retrying in 30s")


def test_a_source_still_cloning_is_waited_out(monkeypatch):
    shadow = load_shadow()
    applied = ks(
        "True", "ReconciliationSucceeded", "Applied revision: v2.9.0@sha1:378b"
    )
    drive(monkeypatch, shadow, [ARTIFACT, ARTIFACT, applied])
    ready, msg, inv = shadow.wait_ks("shadow-floor-eso-crds", 100)
    assert ready, msg
    assert msg.startswith("Applied revision")
    assert inv == [{"id": "crd"}]


def test_a_source_that_never_arrives_still_fails_at_the_deadline(monkeypatch):
    shadow = load_shadow()
    drive(monkeypatch, shadow, [ARTIFACT], clock_step=10.0)
    ready, msg, _ = shadow.wait_ks("shadow-floor-eso-crds", 100)
    assert not ready
    assert "timed out" in msg and "Source artifact not found" in msg


def test_a_real_build_failure_is_still_the_verdict_at_once(monkeypatch):
    shadow = load_shadow()
    broken = ks("False", "BuildFailed", 'no matches for kind "ExternalSecret"')
    drive(monkeypatch, shadow, [broken])
    ready, msg, _ = shadow.wait_ks("platform-llm", 100)
    assert not ready
    assert "ExternalSecret" in msg and "timed out" not in msg
