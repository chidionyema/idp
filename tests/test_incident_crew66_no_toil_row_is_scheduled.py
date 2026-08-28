"""crew#66, 2026-08-28. Founder, verbatim: "wee need to also audit the platfron for anything that
breaks this standard and alert". The no-toil gate (ci.yml no-toil-gate) judges only the files a
pull request changes, so a manual-step sentence that reaches the tree through any other door is
never read again: nothing scheduled swept the whole tree, and the one-off sweep run that day
spent more than five minutes inside backstage/node_modules and reported four upstream READMEs
as our toil, because `find` pruned only the top-level ./node_modules.

Rule: bin/idp-verify-drill carries a `no-toil` row that runs bin/idp-no-toil --sweep, its
workflow installs the conftest the sweep needs (a row that cannot run is BLIND, not a pass),
and the sweep prunes vendored trees at any depth.

On main: no row, no conftest in verify-drill.yml, and the prune is `-path ./node_modules`.
No sockets: every check reads the working tree; the sweep itself runs only under conftest and
against a temporary tree of two files."""
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin" / "idp-verify-drill"
WORKFLOW = ROOT / ".github" / "workflows" / "verify-drill.yml"
RUNNER = ROOT / "bin" / "idp-no-toil"


def test_verify_drill_has_a_no_toil_row_that_runs_the_sweep():
    s = DRILL.read_text()
    assert 'idp-no-toil" --sweep' in s, "no scheduled sweep: the gate only ever reads a PR's files"
    assert "fail no-toil" in s and "bl no-toil" in s and "ok no-toil" in s


def test_verify_drill_workflow_installs_conftest():
    s = WORKFLOW.read_text()
    assert "conftest_0.62.0_Linux_x86_64" in s, "no conftest on the runner: the row would be BLIND every hour"


def test_sweep_prunes_vendored_trees_at_any_depth():
    s = RUNNER.read_text()
    assert "-path ./node_modules -prune" not in s, "top-level prune only: backstage/node_modules is swept"
    assert "-name node_modules" in s and "-prune" in s


@pytest.mark.skipif(shutil.which("conftest") is None, reason="conftest is not installed; CI pins v0.62.0")
def test_sweep_skips_a_nested_node_modules_readme(tmp_path):
    (tmp_path / "policy").mkdir()
    (tmp_path / "bin").mkdir()
    shutil.copy(ROOT / "policy" / "no-manual-steps.rego", tmp_path / "policy" / "no-manual-steps.rego")
    shutil.copy(RUNNER, tmp_path / "bin" / "idp-no-toil")
    vendored = tmp_path / "app" / "node_modules" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / "README.md").write_text("Click here to paste this value.\n")
    (tmp_path / "README.md").write_text("Flux reconciles it; nothing to do by hand.\n")
    r = subprocess.run(
        [str(tmp_path / "bin" / "idp-no-toil"), "--sweep"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "IDP_ROOT": str(tmp_path)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "node_modules" not in r.stdout
