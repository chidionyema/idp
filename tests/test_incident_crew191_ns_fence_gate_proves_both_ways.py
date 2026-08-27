"""crew#191, founder 2026-08-24: "Apply a Default Deny All NetworkPolicy to every namespace".
Measured before any fence existed: a pod in one namespace reached a pod in another by IP,
no credential, HTTP 200 in 4ms. This pins the gate both ways (LAW 15) and pins the four
rules by name, so a rule cannot be dropped from the gate without this test naming it."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "ns-fence-gate"
FIX = ROOT / "tests" / "fixtures" / "ns-fence"


def _run(path: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE), str(path)], capture_output=True, text=True, check=False)


def test_a_fenced_namespace_passes():
    r = _run(FIX / "good.yaml")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fixture-fenced" in r.stdout


def test_a_flat_namespace_is_refused_on_all_four_rules():
    r = _run(FIX / "bad.yaml")
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout
    for rule in ("no ResourceQuota", "no LimitRange", "denies Ingress", "denies Egress"):
        assert rule in out, rule


def test_a_quota_without_a_limitrange_is_a_defect_not_a_partial_win():
    # LAW 38: a ResourceQuota counting requests.cpu with no LimitRange makes every
    # pod without an explicit request unschedulable; the gate must name it.
    r = _run(FIX / "bad.yaml")
    assert "no LimitRange" in r.stdout


def test_a_missing_path_is_blind_not_a_verdict():
    r = _run(ROOT / "tests" / "fixtures" / "ns-fence" / "does-not-exist.yaml")
    assert r.returncode != 0
