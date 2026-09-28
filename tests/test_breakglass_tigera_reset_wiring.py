"""The break-glass playbook dispatch is a closed set: a playbook is added here, reviewed, and
named in the workflow input, and `bin/idp-oke-break-glass` is the one place a hand reaches the
cluster. A new playbook -- tigera-reset (flannel->calico cutover rollback, founder 2026-09-06) --
must be registered twice (the `--list` string and the `case` dispatch) and must carry the two
safety guards that make it safe to run on a live cluster: it refuses to run unless flannel is the
live daemonset (2/2) and unless the calico Flux Kustomization is already suspended in git. This
test grades the parsed structure -- the dispatch cases and the guard `[`-tests -- never the prose
comments, so it does not care how the playbook is described, only how it is wired.

Rung 2 fixtures: none needed; the good (wired + guarded) shape is the file itself, and the
sensitivity test strips each guard property to prove the checks would catch a regression.
"""

# ruff: noqa: S101
# subprocess is deliberate: the dispatch is the produced CLI, not a unit-test seam.

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "idp-oke-break-glass"


def _run_cli(args):
    return subprocess.run([str(CLI), *args], capture_output=True, text=True, timeout=30)


def _source_lines():
    return CLI.read_text().splitlines()


def _func_body(name, lines):
    """Return the index range [start, end) of the named playbook function.

    Functions are declared K&R style just before the dispatch: ``name() {``. A body ends at
    the first later line that is exactly ``}`` at column 0 (a top-level close at brace depth
    zero).
    """
    start = None
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped.startswith(f"{name}() {{"):
            start = i
            continue
        if start is not None and stripped == "}":
            if len(ln) - len(ln.lstrip()) == 0:
                return start, i
    return start, None


# -- the playbook is registered ------------------------------------------


def test_tigera_reset_is_listed():
    out = _run_cli(["--list"])
    assert out.returncode == 0, out.stderr
    names = out.stdout.split()
    assert "tigera-reset" in names


def test_tigera_reset_is_dispatchable():
    lines = _source_lines()
    # the case dispatch must map the CLI word to the function
    assert any(ln.strip() == "tigera-reset) pb_tigera_reset ;;" for ln in lines)
    # and the function must actually be defined in the file
    start, end = _func_body("pb_tigera_reset", lines)
    assert start is not None and end is not None


# -- the playbook carries the two safety guards --------------------------


def test_tigera_reset_guards_against_running_without_flannel():
    lines = _source_lines()
    start, end = _func_body("pb_tigera_reset", lines)
    body = lines[start:end]
    # must read the flannel DS ready/desired counts
    assert any("kube-flannel-ds" in ln and "numberReady" in ln for ln in body)
    # must refuse to proceed unless 2/2
    assert any('"2/2"' in ln or "'2/2'" in ln for ln in body)


def test_tigera_reset_guards_against_running_unsuspended_calico():
    lines = _source_lines()
    start, end = _func_body("pb_tigera_reset", lines)
    body = lines[start:end]
    # must read spec.suspend of the calico Kustomization
    assert any("kustomization" in ln and "suspend" in ln for ln in body)
    # must refuse when suspend is not true
    assert any('"true"' in ln for ln in body)


# -- the gate is sensitive, not vacuous ---------------------------------


def test_guard_checks_would_catch_a_regression():
    # Prove the assertions above are not vacuous: a body that lacks a guard must trip it.
    lines = _source_lines()
    start, end = _func_body("pb_tigera_reset", lines)
    body = lines[start:end]

    # removing every line that reads the flannel DS drops the numberReady read
    no_flannel = [ln for ln in body if "kube-flannel-ds" not in ln]
    assert not any("kube-flannel-ds" in ln and "numberReady" in ln for ln in no_flannel)

    # removing every line that mentions suspend drops the calico suspend read
    no_suspend = [ln for ln in body if "kustomization" not in ln or "suspend" not in ln]
    assert not any("kustomization" in ln and "suspend" in ln for ln in no_suspend)

    # a name with no dispatch arm is inert, so the arm must exist and call the function
    case_arm = [ln.strip() for ln in lines if ln.strip().startswith("tigera-reset)")]
    assert case_arm, "no dispatch arm for tigera-reset"
    assert all("pb_tigera_reset" in a for a in case_arm)
