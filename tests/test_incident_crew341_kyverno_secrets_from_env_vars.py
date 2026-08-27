"""Incident test for crew#341: no Kyverno policy blocked a secret read via env vars.

WHY. Confirmed 2026-08-26: no `secrets-not-from-env-vars`/`secrets-not-from-envfrom`
policy existed anywhere in this repo. platform/observability/langfuse.yaml happens to
do secrets correctly (ExternalSecret -> volume mount) by authorial care, not by
enforcement -- nothing would have caught a future Helm chart's default
env.valueFrom.secretKeyRef or envFrom.secretRef. Real upstream Kyverno community
policy (kyverno/policies, other-cel/disallow-secrets-from-env-vars), not hand-rolled
(LAW 19/43), verified against the real `kyverno` CLI (not simulated) before landing.

Real, honest deviation from the literal upstream CEL text, documented here and in
platform/edge/kyverno-secrets-policy.yaml: the upstream nested-.orValue() form threw
"no such overload" against this machine's `kyverno apply` (CLI 1.19.0) on the real
must-fail fixture. Rewritten with has()/exists(), re-verified identical pass/fail on
every fixture before landing -- this test is that re-verification, permanent.

Runs the real `kyverno` CLI against 5 real fixtures (tests/fixtures/kyverno-secrets/):
  T1  secretKeyRef in env (must-fail): the exact class this policy exists to catch.
  T2  envFrom.secretRef (must-fail): the bulk-injection variant of the same class.
  T3  ExternalSecret-as-volume-mount (must-pass): today's real, already-shipped
      correct pattern (langfuse) must not be refused by the new policy.
  T4  zero env vars at all (must-pass): the policy must not require env to exist,
      only refuse it when it IS a secret reference -- a false requirement here
      would be a guard refusing correct work (LAW 38).
  T5  ConfigMap-sourced env, not Secret (must-pass): the real false-positive risk
      of a guard written too broadly -- configMapKeyRef/configMapRef must be
      allowed; only *Secret* references are the actual risk.

Skipped, not failed, when the `kyverno` CLI binary is not installed -- this is an
environment dependency (LAW 19: build on the mature tool), not something to fake
with a hand-rolled CEL evaluator.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "platform" / "edge" / "kyverno-secrets-policy.yaml"
FIXTURES = ROOT / "tests" / "fixtures" / "kyverno-secrets"

pytestmark = pytest.mark.skipif(
    shutil.which("kyverno") is None,
    reason="kyverno CLI not installed -- LAW 19, real tool required, no hand-rolled CEL simulator",
)


def _apply(fixture_name: str) -> tuple[int, str]:
    fixture = FIXTURES / fixture_name
    assert fixture.exists(), f"missing fixture: {fixture}"
    proc = subprocess.run(
        ["kyverno", "apply", str(POLICY), "--resource", str(fixture)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _fail_count(output: str) -> int:
    for line in output.splitlines():
        if line.strip().startswith("pass:"):
            # "pass: 0, fail: 1, warn: 0, error: 0, skip: 0"
            parts = dict(p.strip().split(":") for p in line.split(","))
            return int(parts["fail"].strip())
    raise AssertionError(f"could not find pass/fail summary line in: {output!r}")


def test_t1_secretkeyref_in_env_is_refused():
    _rc, out = _apply("pod-secretkeyref.bad.yaml")
    assert _fail_count(out) == 1, f"secretKeyRef-in-env must be refused, got: {out}"
    assert "no such overload" not in out, f"CEL expression error, not a policy match: {out}"


def test_t2_envfrom_secretref_is_refused():
    _rc, out = _apply("pod-envfrom-secretref.bad.yaml")
    assert _fail_count(out) == 1, f"envFrom.secretRef must be refused, got: {out}"
    assert "no such overload" not in out, f"CEL expression error, not a policy match: {out}"


def test_t3_externalsecret_volume_mount_pattern_passes():
    """The real, already-shipped pattern (langfuse) must not be caught by this policy."""
    _rc, out = _apply("pod-externalsecret-pattern.good.yaml")
    assert _fail_count(out) == 0, f"vault-backed volume-mount secrets must pass, got: {out}"


def test_t4_pod_with_no_env_at_all_passes():
    """A guard that requires env to exist would refuse correct work (LAW 38)."""
    _rc, out = _apply("pod-no-secrets-at-all.good.yaml")
    assert _fail_count(out) == 0, f"a pod with no env vars must not be refused, got: {out}"


def test_t5_configmap_sourced_env_passes():
    """Real false-positive risk: only Secret references are the risk, not ConfigMap."""
    _rc, out = _apply("pod-plain-configmap-env.good.yaml")
    assert _fail_count(out) == 0, f"ConfigMap-sourced env must be allowed, got: {out}"
