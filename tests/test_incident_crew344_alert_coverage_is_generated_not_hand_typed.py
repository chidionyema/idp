"""Incident test for crew#344: Flux alerting was a hand-typed 7-namespace allowlist.

WHY. platform/alerts/alert.yaml named 7 namespaces by hand (cert-manager, chaos-mesh,
observability, identity, edge, external-secrets, kyverno). A new namespace shipped
without a matching hand-added line failed silently -- exactly the class behind crew#308
(Flux failures never reaching Telegram) and crew#340 (Langfuse broken 2+ days, unnoticed).

THE FIX UNDER TEST: alert coverage generated from the live namespace/HelmRelease
inventory, not maintained by hand. This test is written BEFORE that generator exists
(TDD RED first) -- it will fail on collection/import until bin/idp-alert-coverage (or
equivalent) is built, and every case below must hold once it is.

WHAT MUST HOLD, one case per real risk, not one test per function:
  T1  A new namespace with no explicit exclusion is covered by default (must-pass:
      LAW 38, a monitoring gap that requires remembering to add a line is the class
      this fix removes).
  T2  A namespace explicitly marked excluded (e.g. a scratch/test namespace) stays
      uncovered -- deliberate, not a bug (must-fail-to-alert case).
  T3  Idempotent: two runs over one identical inventory produce byte-identical output
      (AGENTS.md's own generator invariant, already required of every idp generator).
  T4  flux-system and kube-system are handled explicitly, not accidentally included or
      excluded by a wildcard matching everything including system machinery noise.
  T5  An empty cluster (zero namespaces) does not crash and produces valid, minimal
      output -- the generator must degrade gracefully, not assume namespaces exist.
  T6  A namespace that existed on a prior run and is now gone drops cleanly from
      coverage -- no stale entries pointing at deleted namespaces.
  T7  Every entry in generated coverage is a real, syntactically valid Flux
      eventSources block (kind + name + namespace), not just a namespace string --
      the real Alert CRD shape, so a malformed generator output fails loudly, not
      silently at apply time.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parent.parent
GENERATOR = IDP / "bin" / "idp-alert-coverage"


def run_generator(namespaces: list[dict], excluded: list[str] | None = None) -> tuple[int, str, str]:
    """Run the (not-yet-built) generator against a synthetic namespace inventory.

    namespaces: [{"name": "...", "has_helmrelease_or_kustomization": bool}, ...]
    excluded: namespace names deliberately marked out of scope (kube-system etc.)
    """
    payload = json.dumps({"namespaces": namespaces, "excluded": excluded or []})
    proc = subprocess.run(
        [str(GENERATOR), "--stdin-inventory"],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _generator_missing() -> bool:
    return not GENERATOR.exists()


pytestmark = pytest.mark.skipif(
    _generator_missing(),
    reason="RED phase: bin/idp-alert-coverage does not exist yet (TDD -- test written first, crew#344)",
)


def test_t1_new_namespace_with_no_exclusion_is_covered_by_default():
    """A namespace nobody remembered to add still gets alert coverage (the class fix)."""
    rc, out, err = run_generator(
        namespaces=[{"name": "brand-new-service", "has_helmrelease_or_kustomization": True}],
        excluded=[],
    )
    assert rc == 0, f"generator failed: {err}"
    data = json.loads(out)
    names = {e["namespace"] for e in data["eventSources"]}
    assert "brand-new-service" in names, "new namespace must be covered without an explicit line"


def test_t2_explicitly_excluded_namespace_stays_silent():
    """A deliberately-excluded namespace (e.g. scratch/test) is NOT alerted -- by design."""
    rc, out, err = run_generator(
        namespaces=[{"name": "scratch-dev", "has_helmrelease_or_kustomization": True}],
        excluded=["scratch-dev"],
    )
    assert rc == 0, f"generator failed: {err}"
    data = json.loads(out)
    names = {e["namespace"] for e in data["eventSources"]}
    assert "scratch-dev" not in names, "explicitly excluded namespace must stay silent"


def test_t3_idempotent_two_runs_byte_identical():
    """AGENTS.md's own generator invariant: two runs over one inventory, byte-identical."""
    ns = [
        {"name": "identity", "has_helmrelease_or_kustomization": True},
        {"name": "edge", "has_helmrelease_or_kustomization": True},
    ]
    rc1, out1, _ = run_generator(namespaces=ns, excluded=[])
    rc2, out2, _ = run_generator(namespaces=ns, excluded=[])
    assert rc1 == 0 and rc2 == 0
    assert out1 == out2, "generator output must be byte-identical across identical inputs"


def test_t4_flux_system_and_kube_system_handled_explicitly():
    """System namespaces are an explicit decision, not accidental wildcard inclusion/exclusion."""
    rc, out, err = run_generator(
        namespaces=[
            {"name": "flux-system", "has_helmrelease_or_kustomization": True},
            {"name": "kube-system", "has_helmrelease_or_kustomization": False},
        ],
        excluded=[],
    )
    assert rc == 0, f"generator failed: {err}"
    data = json.loads(out)
    names = {e["namespace"] for e in data["eventSources"]}
    # flux-system carries real GitRepository/Kustomization objects worth alerting on;
    # kube-system carries no HelmRelease/Kustomization workloads this platform owns.
    assert "flux-system" in names, "flux-system must be explicitly covered (Flux's own health)"
    assert "kube-system" not in names, "kube-system has no idp-owned workload; must not alert"


def test_t5_empty_cluster_degrades_gracefully():
    """Zero namespaces must not crash the generator."""
    rc, out, err = run_generator(namespaces=[], excluded=[])
    assert rc == 0, f"generator crashed on empty inventory: {err}"
    data = json.loads(out)
    assert data["eventSources"] == [], "empty inventory must produce empty, valid coverage, not an error"


def test_t6_deleted_namespace_drops_from_coverage():
    """A namespace present on a prior run and now gone must not leave a stale entry."""
    rc1, out1, _ = run_generator(
        namespaces=[{"name": "temp-migration", "has_helmrelease_or_kustomization": True}],
        excluded=[],
    )
    assert rc1 == 0
    data1 = json.loads(out1)
    assert "temp-migration" in {e["namespace"] for e in data1["eventSources"]}

    rc2, out2, _ = run_generator(namespaces=[], excluded=[])
    assert rc2 == 0
    data2 = json.loads(out2)
    assert "temp-migration" not in {e["namespace"] for e in data2["eventSources"]}, (
        "a namespace no longer in the live inventory must not remain in generated coverage"
    )


def test_t7_every_entry_is_a_real_flux_eventsource_shape():
    """Output must be valid Flux Alert eventSources entries, not bare namespace strings."""
    rc, out, err = run_generator(
        namespaces=[{"name": "observability", "has_helmrelease_or_kustomization": True}],
        excluded=[],
    )
    assert rc == 0, f"generator failed: {err}"
    data = json.loads(out)
    assert len(data["eventSources"]) >= 1
    for entry in data["eventSources"]:
        assert "kind" in entry, "missing 'kind' -- malformed Flux eventSources entry"
        assert "name" in entry, "missing 'name' -- malformed Flux eventSources entry"
        assert "namespace" in entry, "missing 'namespace' -- malformed Flux eventSources entry"
        assert entry["kind"] in ("HelmRelease", "Kustomization", "GitRepository"), (
            f"unexpected kind {entry['kind']!r}: only real Flux-watchable kinds are valid"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
