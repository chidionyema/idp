"""2026-08-29: main went red on the kyverno rung (run 33248103977) with `the must-fail fixture
passed; the judge admits an unpatched chart`, while the same commit's PR run was green. The
judge in bin/idp-kyverno-render did `printf '%s\n' "$out" | grep -qE '^policy .* failed'` under
`set -o pipefail`. `grep -q` exits on the first match; printf, still writing the rest of a
kyverno report, takes SIGPIPE; pipefail hands the pipeline printf's 141, and `if` reads a
41-fail render as "ok". Whether it bites depends on how much output sits behind the first
match, so it flipped run to run: silent green, the defect class.

Two fences: the judge shape reproduced with a stub kyverno whose report is larger than a pipe
buffer, and a sweep that refuses `| grep -q` anywhere under bin/ (grep without -q reads all of
its input, so the writer never sees SIGPIPE).

Measured on the Mac with the real script and the fixture (2026-08-29): the `grep -q` pipeline
inside the script exits 141 while the fixed judge on the same `$out` prints FAIL. A process
tree that starts with SIGPIPE ignored (some agent harnesses do) turns 141 into a caught EPIPE,
so the first test below is the CI-runner truth; the sweep is the fence that holds everywhere.
"""

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
RENDER = IDP / "bin" / "idp-kyverno-render"
PIPED_GREP_Q = re.compile(r"\|\s*grep\s+-q")


def _judge_source() -> str:
    src = RENDER.read_text()
    start = src.index("judge() {")
    end = src.index("\n}\n", start) + 3
    return src[start:end]


@pytest.fixture
def stub_kyverno(tmp_path: Path) -> Path:
    """A kyverno whose report puts the failed line first and 400 KB of detail after it."""
    b = tmp_path / "bin"
    b.mkdir()
    k = b / "kyverno"
    k.write_text(
        "#!/bin/sh\n"
        "echo 'policy require-ro-rootfs -> resource ns/Deployment/x failed:'\n"
        "i=0; while [ $i -lt 6000 ]; do echo '1 - autogen-validate-readOnlyRootFilesystem validation error: Root filesystem must be read-only.'; i=$((i+1)); done\n"
        "echo 'pass: 185, fail: 41, warn: 0, error: 0, skip: 21'\n"
    )
    k.chmod(k.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "policies.yaml").write_text("")
    (tmp_path / "res.yaml").write_text("")
    return tmp_path


def test_judge_grades_a_failed_render_fail_even_when_the_report_is_larger_than_a_pipe(
    stub_kyverno,
):
    script = (
        "set -euo pipefail\n"
        f'S="{stub_kyverno}"\n'
        "_exc() { :; }\n" + _judge_source() + 'judge "render  " x "$S/res.yaml"\n'
    )
    r = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{stub_kyverno / 'bin'}:{os.environ['PATH']}"},
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.startswith("FAIL  render"), r.stdout[:200]


def test_no_script_under_bin_pipes_into_grep_q():
    offenders = []
    for p in sorted((IDP / "bin").iterdir()):
        if not p.is_file():
            continue
        try:
            head = p.open("rb").read(64)
        except OSError:
            continue
        if b"sh" not in head.split(b"\n")[0]:
            continue
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if PIPED_GREP_Q.search(line):
                offenders.append(f"{p.relative_to(IDP)}:{n}")
    assert not offenders, (
        "`| grep -q` under pipefail reads green on SIGPIPE; use `grep ... >/dev/null`: "
        + ", ".join(offenders)
    )
