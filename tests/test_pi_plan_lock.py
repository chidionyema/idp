"""pi-plan-lock (idp#6675): no tool runs without a declared plan, and no tool result is unbounded.

The rules are pure TypeScript with no pi import, so they run under node's own test runner. This
wrapper makes them part of the python suite, which is the one the gates run. Skipped only when
node itself is absent or too old for --experimental-strip-types (22.6+), the same convention as
the kustomize and go tests; on this laptop and the CI runners with setup-node 22 it executes.
"""

import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extensions" / "pi-plan-lock"


def _node_ok() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    m = re.match(r"v(\d+)\.(\d+)", out.strip())
    return bool(m) and (int(m[1]), int(m[2])) >= (22, 6)


@pytest.mark.skipif(not _node_ok(), reason="node >= 22.6 is not installed")
def test_plan_rules_hold():
    r = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--test",
            str(EXT / "plan.test.ts"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]
    assert re.search(r"# pass [1-9]", r.stdout), "node ran no tests: " + r.stdout[-500:]


def test_the_extension_wires_every_rule_it_tests():
    """The pure rules are only a gate if index.ts actually calls them."""
    src = (EXT / "index.ts").read_text()
    for needle in (
        '"tool_call"',
        '"tool_result"',
        "authorize(",
        "capText(",
        "apply(",
        "registerTool",
    ):
        assert needle in src, (
            f"index.ts never uses {needle}: the rule exists and nothing enforces it"
        )
    for tool in (
        "declare_plan",
        "revise_plan",
        "add_bdd",
        "address_edgecases",
        "address_2nd_order_effects",
        "complete_goal",
    ):
        assert f'name: "{tool}"' in src, f"index.ts does not register {tool}"
    assert "declare_plan" in src and "complete_goal" in src


def _install(ext_dir, *args):
    return subprocess.run(
        [
            str(ROOT / "bin" / "pi-plan-lock-install"),
            "--extensions-dir",
            str(ext_dir),
            *args,
        ],
        capture_output=True,
        text=True,
    )


def test_installer_copies_checks_and_detects_drift(tmp_path):
    ext = tmp_path / "extensions"
    ext.mkdir()
    assert _install(ext, "--check").returncode == 1, (
        "a missing install must read as drift"
    )
    assert _install(ext).returncode == 0
    for name in ("index.ts", "plan.ts"):
        assert (ext / "pi-plan-lock" / name).read_bytes() == (EXT / name).read_bytes()
    assert _install(ext, "--check").returncode == 0
    (ext / "pi-plan-lock" / "plan.ts").write_text("// stale\n")
    assert _install(ext, "--check").returncode == 1
    assert _install(ext).returncode == 0 and _install(ext, "--check").returncode == 0


def test_installer_creates_nothing_when_pi_is_absent(tmp_path):
    r = _install(tmp_path / "no-pi")
    assert r.returncode == 0 and "absent" in r.stdout
    assert not (tmp_path / "no-pi").exists()
