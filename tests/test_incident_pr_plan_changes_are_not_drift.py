"""Incident 2026-08-26: oke-check run 32925504695 failed idp#160 on the PR's own planned changes (rc=2),
and rule-guard blocks a merge on any red check, so a platform/oci PR could never merge.
Rule: on pull_request the workflow sets OKE_CHECK_EXPECT_CHANGES=1 and --check passes rc=2; on
schedule/dispatch the variable is 0 and rc=2 stays FAIL."""

import os, re, subprocess, pathlib

IDP = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = IDP / "bin" / "idp-oke-rebuild"
WF = IDP / ".github" / "workflows" / "oke-check.yml"


def _check_branch(expect: str, rc: int) -> str:
    """Run the --check case body with a fake tofu that exits rc, under the given env value."""
    src = SCRIPT.read_text()
    body = (
        re.search(r"  --check\)\n(.*?)  --apply\)", src, re.S)
        .group(1)
        .rstrip()
        .removesuffix(";;")
    )
    stub = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "fake-tofu-bin"
    stub.mkdir(exist_ok=True)
    (stub / "tofu").write_text(f"#!/bin/sh\nexit {rc}\n")
    (stub / "tofu").chmod(0o755)
    step_fn = re.search(r"^step\(\) \{.*?^\}\n", src, re.S | re.M).group(0)
    prog = (
        f'FAILED=""; TF="{stub}"; TFVARS=()\n{step_fn}\n{body}\necho "FAILED=[$FAILED]"'
    )
    env = {
        **os.environ,
        "PATH": f"{stub}:{os.environ['PATH']}",
        "OKE_CHECK_EXPECT_CHANGES": expect,
    }
    return subprocess.run(
        ["bash", "-c", prog], env=env, capture_output=True, text=True
    ).stdout


def test_pull_request_rc2_passes_and_schedule_rc2_fails():
    assert "FAILED=[]" in _check_branch("1", 2)  # PR: plan changes are the PR
    assert "FAILED=[ tofu-plan]" in _check_branch("0", 2)  # schedule/dispatch: drift
    assert "FAILED=[ tofu-plan]" in _check_branch("1", 1)  # a broken plan never passes
