"""Incident 2026-08-27 (crew#539 CP4, oke-check 33125334695 and 33124930652): main's check went
red on `node pools not ACTIVE: a1-spot` minutes after the cluster autoscaler first started, and the
row never said which state the pool was in (LAW 28). A pool being resized is UPDATING; grading that
red makes a gate that refuses the platform doing its job (LAW 38). Rule: nodes_oci names every
non-ACTIVE pool as name(STATE); UPDATING passes and is said as a resize in flight; any other
state (CREATING, DELETING, FAILED, ...) is still red. Both ways, through the file backend of
bin/idp-cloud, never a mock of the function under test."""

import re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oke-rebuild"


def _fn() -> str:
    m = re.search(r"^nodes_oci\(\) \{.*?fi; \}\n", SCRIPT.read_text(), re.S | re.M)
    assert m, "nodes_oci() not found"
    return m.group(0)


_N = [0]


def _run(tmp_path, pools: dict) -> tuple[int, str]:
    _N[0] += 1
    root = (
        tmp_path / f"cloud{_N[0]}"
    )  # a fresh backend per call: one test drives two states
    (root / "nodepools").mkdir(parents=True)
    for name, state in pools.items():
        (root / "nodepools" / name).write_text(state + "\n")
    script = (
        f'IDP="{ROOT}"; export IDP_CLOUD_BACKEND=file IDP_CLOUD_FILE_ROOT="{root}"\n'
        + _fn()
        + "nodes_oci\n"
    )
    p = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def test_a_pool_being_resized_is_not_a_red_row_and_is_named(tmp_path):
    rc, out = _run(tmp_path, {"a1": "ACTIVE", "a1-spot": "UPDATING"})
    assert rc == 0, out
    assert "UPDATING" in out and "a1-spot" in out, out


def test_any_other_state_is_red_and_the_state_is_on_the_line(tmp_path):
    rc, out = _run(tmp_path, {"a1": "ACTIVE", "a1-spot": "CREATING"})
    assert rc == 1 and "a1-spot(CREATING)" in out, out
    rc, out = _run(tmp_path, {"a1": "DELETING", "a1-spot": "UPDATING"})
    assert rc == 1 and "a1(DELETING)" in out and "UPDATING: a1-spot" in out, out


def test_no_pools_is_red(tmp_path):
    rc, out = _run(tmp_path, {})
    assert rc == 1 and out == "no node pools", out
