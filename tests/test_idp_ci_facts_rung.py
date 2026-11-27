"""The facts rung of bin/idp-ci refuses what a lane can cause and warns on what time causes.

idp#8602: eight 30-day facts aged out together and every push from the Mac went red, though
no lane had touched them. The rung is extracted from the real script and run against a stub
`estate-claim-check` that prints each verdict, so the test grades the rung itself.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "bin" / "idp-ci").read_text(encoding="utf-8")
START = SCRIPT.index("facts_n=0\n")
END = SCRIPT.index('[ "$facts_n" -gt 0 ]', START)
RUNG = SCRIPT[START:END]


def run_rung(tmp_path: Path, verify_out: str, verify_rc: int) -> tuple[str, str]:
    idp = tmp_path / "idp"
    (idp / "bin").mkdir(parents=True)
    (idp / "facts").mkdir()
    (idp / "facts" / "repo.jsonl").write_text("{}\n")
    stub = idp / "bin" / "estate-claim-check"
    stub.write_text(f"#!/bin/sh\ncat <<'OUT'\n{verify_out}\nOUT\nexit {verify_rc}\n")
    stub.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    cmd = (
        'say() { printf "%s\\n" "$*"; }; fail=0\n'
        + RUNG
        + 'printf "fail=%s\\n" "$fail"\n'
    )
    p = subprocess.run(
        ["bash", "-c", cmd],
        env={"IDP": str(idp), "HOME": str(home), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0, p.stderr
    out = p.stdout
    return out.splitlines()[0], out.strip().splitlines()[-1]


@pytest.mark.parametrize(
    "verify_out, verify_rc, first, fail",
    [
        (
            "PASS  a1  rows=3\n1/1 facts re-executed. verdict: PASS",
            0,
            "ok    facts",
            "fail=0",
        ),
        (
            "STALE  125be8c0aa7b  R2-evidence  measured 2675171s ago, valid for 2592000s\n"
            "0/1 facts re-executed. verdict: FAIL",
            1,
            "warn  facts",
            "fail=0",
        ),
        (
            "UNWITNESSED  b2  input lives in another checkout\nverdict: FAIL",
            1,
            "warn  facts",
            "fail=0",
        ),
        (
            "CONTRADICTED  c3  stored 586884, measured 12\nverdict: FAIL",
            1,
            "FAIL  facts",
            "fail=1",
        ),
        (
            "STALE  d4  aged\nTAMPERED  e5  digest differs\nverdict: FAIL",
            1,
            "FAIL  facts",
            "fail=1",
        ),
        (
            "Traceback (most recent call last):\nValueError: bad store",
            1,
            "FAIL  facts",
            "fail=1",
        ),
    ],
    ids=[
        "pass",
        "stale-warns",
        "unwitnessed-warns",
        "contradicted-fails",
        "tampered-wins",
        "crash-refuses",
    ],
)
def test_facts_rung_verdict(tmp_path, verify_out, verify_rc, first, fail):
    line, last = run_rung(tmp_path, verify_out, verify_rc)
    assert line.startswith(first), line
    assert last == fail


def test_a_stale_warning_names_the_row_and_the_door(tmp_path):
    idp = tmp_path
    line, _ = run_rung(idp, "STALE  125be8c0aa7b  aged\nverdict: FAIL", 1)
    full = subprocess.run(
        ["bash", "-c", 'say() { printf "%s\\n" "$*"; }; fail=0\n' + RUNG],
        env={
            "IDP": str(idp / "idp"),
            "HOME": str(idp / "home"),
            "PATH": "/usr/bin:/bin",
        },
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    assert "STALE  125be8c0aa7b" in full
    assert "re-measure: bin/estate-claim-check --store" in full


if __name__ == "__main__" and "--optimus" in __import__("sys").argv:
    # Registered measure ci.facts_rung_time_reds: 1 when the rung reds a lane on a STALE-only
    # store (time, not the lane), 0 when it warns. Exit 0 with the line, or non-zero and silent.
    import sys
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        first, last = run_rung(Path(d), "STALE  r1  aged\nverdict: FAIL", 1)
    print(f"optimus.ci.facts_rung_time_reds={1 if last == 'fail=1' else 0}")
    sys.exit(0)
