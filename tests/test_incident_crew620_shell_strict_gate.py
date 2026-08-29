"""crew#620 CP2/CP3 (founder ruling, 2026-08-29): "strict shell practice estate-wide with
immediate effect". bin/idp-shell-strict is the gate: shellcheck -S warning, shfmt -d, a
`set -euo pipefail` (or `set -eu` + `set -o pipefail`) and a trap, on every shell file under
bin/, .githooks/ and scripts/. This proves the gate both ways on synthetic fixtures (LAW 38:
a gate only ever seen refusing has never been shown to permit) and proves the CI wiring names
the job and the checker, so the workflow cannot silently stop calling it.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-shell-strict"
HAVE_SHELLCHECK = shutil.which("shellcheck") is not None
HAVE_SHFMT = shutil.which("shfmt") is not None

CLEAN = '#!/usr/bin/env bash\nset -euo pipefail\ntrap \'echo "$0: exit $?" >&2\' EXIT\necho hi\n'


def run_gate(*files):
    return subprocess.run(
        [sys.executable, str(GATE), "--files", *[str(f) for f in files]],
        capture_output=True, text=True,
    )


def test_passes_on_a_clean_file(tmp_path):
    f = tmp_path / "clean.sh"
    f.write_text(CLEAN)
    r = run_gate(f)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok    shell-strict" in r.stdout


@pytest.mark.skipif(not HAVE_SHELLCHECK, reason="shellcheck not installed")
def test_refuses_a_shellcheck_warning(tmp_path):
    f = tmp_path / "sc.sh"
    f.write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\ntrap \'true\' EXIT\n'
        'for f in $(ls); do echo "$f"; done\n'
    )
    r = run_gate(f)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"shell-strict: {f}: shellcheck -S warning found issues" in r.stdout


@pytest.mark.skipif(not HAVE_SHFMT, reason="shfmt not installed")
def test_refuses_an_unformatted_file(tmp_path):
    f = tmp_path / "fmt.sh"
    f.write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\ntrap \'true\' EXIT\n'
        'if true; then\necho hi\nfi\n'
    )
    r = run_gate(f)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"shell-strict: {f}: not shfmt-formatted" in r.stdout


def test_refuses_a_missing_strict_mode(tmp_path):
    f = tmp_path / "nostrict.sh"
    f.write_text('#!/usr/bin/env bash\ntrap \'true\' EXIT\necho hi\n')
    r = run_gate(f)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"shell-strict: {f}: missing 'set -euo pipefail'" in r.stdout


def test_set_eu_plus_set_o_pipefail_is_accepted(tmp_path):
    f = tmp_path / "splitstrict.sh"
    f.write_text(
        '#!/usr/bin/env bash\nset -eu\nset -o pipefail\ntrap \'true\' EXIT\necho hi\n'
    )
    r = run_gate(f)
    assert "missing 'set -euo pipefail'" not in r.stdout, r.stdout


def test_refuses_a_missing_trap(tmp_path):
    f = tmp_path / "notrap.sh"
    f.write_text('#!/usr/bin/env bash\nset -euo pipefail\necho hi\n')
    r = run_gate(f)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"shell-strict: {f}: missing a trap" in r.stdout


def test_default_discovery_finds_the_repos_own_shell_files():
    # No --files: discovery walks bin/, .githooks/, scripts/. The repo's own files must
    # come back clean, because this test runs after the sweep that fixed every red.
    r = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok    shell-strict" in r.stdout


def test_workflow_names_the_job_and_the_checker():
    wf = (ROOT / ".github" / "workflows" / "fast-gate.yml").read_text()
    assert "shell-strict" in wf, "fast-gate.yml does not name a shell-strict job"
    assert "bin/idp-shell-strict" in wf, "fast-gate.yml does not call bin/idp-shell-strict"
