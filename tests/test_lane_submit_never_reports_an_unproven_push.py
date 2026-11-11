"""`lane-submit` must never report a push it has not proved.

Measured 2026-11-11, twice in one session: `estate-execute lane-submit` printed

    [estate] status=ok
    ok    claim-gate  no other live agent holds these files

while the push had been REFUSED by the pre-push gate. The first time the refusal was
`FAIL diagnosis-gate router change with no Diagnosis: commit-message line`; the second,
after that was fixed, `FAIL estate-diagnose H1 posterior 0.72 < 0.95`. `git ls-remote --heads
origin <lane>` was empty both times -- nothing had left the machine -- and the only record of
the refusal was a file in the temp directory that the step printed the path of and then
exited 0 anyway.

That is AGENTS.md section 9 R1 (a gate that fails open) inside the door agents are told to
trust, and it is the same class as the fabricated `tokens_saved` this session started from: a
surface reporting a success it did not measure.

The rule, and the two mechanisms this file pins down:

  1. exit 0 means the remote ref EQUALS the sha. Nothing else. An in-flight push, a push that
     exited 0 while origin has not shown the ref, and a refused push are all non-zero.
  2. a push that finished and failed must carry the refusal it wrote into its own log, so the
     agent reads the reason instead of the exit code.

Both are proved by BEHAVIOUR: the step's own shell is taken out of the intent file and run in
a sandbox where `git` is a stand-in. A text assertion can only prove the words are still there;
the defect this file exists for was a word (`exit 0`) doing the wrong thing.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

INTENT = (
    Path(__file__).resolve().parents[1] / "platform/estate/intents/lane-submit.yaml"
)


def _step_cmd(name: str) -> str:
    doc = yaml.safe_load(INTENT.read_text())
    for step in doc["steps"]:
        if step["name"] == name:
            return step["cmd"]
    raise AssertionError(f"{INTENT} has no step named {name!r}")


def _strip_templates(cmd: str) -> str:
    """The intent is a template; these tests supply their own cwd and lane."""
    return cmd.replace("{{cwd}}", ".").replace("{{lane}}", "")


@pytest.fixture()
def sandbox():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def _git_stub(tmp: Path, body: str) -> None:
    git = tmp / "git"
    git.write_text("#!/bin/sh\n" + body)
    git.chmod(git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _run_push_step(
    tmp: Path, git_body: str, *, sha: str = "deadbeef"
) -> subprocess.CompletedProcess:
    _git_stub(tmp, git_body)
    cmd = _strip_templates(_step_cmd("push the lane"))
    env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}")
    script = f"sha_override={sha}\n{cmd}"
    return subprocess.run(
        ["sh", "-c", script],
        cwd=tmp,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


# A fake git that answers the two questions the step asks: the shas it needs, and the remote ref.
_FAKE_GIT_BASE = """
case "$1" in
  rev-parse) echo "${SHA:-abc123}" ;;
  ls-remote) echo "${REMOTE_REF:-}" ;;
  config) echo "https://github.com/chidionyema/idp.git" ;;
  push) {body} ;;
esac
"""


def _base_git(config_url: str = "https://github.com/chidionyema/idp.git") -> str:
    return f'if [ "$1" = config ]; then echo "{config_url}"; exit 0; fi\n'


def test_a_refused_push_never_exits_zero(sandbox: Path):
    """THE FALSIFIER. A push that the pre-push gate refuses must not be reported as ok.

    Before 2026-11-11 the in-flight branch exited 0, and the harness turned that into
    `[estate] status=ok`. This test fails against that code and passes against the fix.
    """
    body = (
        _base_git()
        + 'case "$1" in\n'
        + "  rev-parse) echo abc123 ;;\n"
        + "  ls-remote) exit 0 ;;\n"  # origin has no ref: the push did not land
        + '  push) echo "FAIL  diagnosis-gate  router change with no Diagnosis: line" >&2; '
        + "exit 1 ;;\n"
        + "esac\n"
    )
    result = _run_push_step(sandbox, body)

    assert result.returncode != 0, (
        "lane-submit reported success for a push it could not prove had landed. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "diagnosis-gate" in combined, (
        "the refusal the push wrote into its own log was not carried back to the caller: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_an_in_flight_push_is_not_reported_as_ok():
    """A text guard on the specific defect: the in-flight branch must not `exit 0`.

    Kept alongside the behavioural test because the behavioural one cannot make a push hang
    for eighteen observations without spending the whole test budget; this asserts the exact
    line that was wrong."""
    cmd = _strip_templates(_step_cmd("push the lane"))
    in_flight = cmd.split("if push_alive; then", 1)[1].split("fi\n", 1)[0]
    assert "IN-FLIGHT" in in_flight, "the in-flight branch is gone; rewrite this test"
    exits = re.findall(r"^\s*exit (\d+)", in_flight, re.MULTILINE)
    assert exits, f"the in-flight branch no longer names its exit code: {in_flight!r}"
    assert all(int(code) != 0 for code in exits), (
        "the in-flight branch exits 0, so the harness reports status=ok for a push that has "
        f"not landed (2026-11-11): exits={exits}"
    )


def test_a_sent_push_that_origin_has_not_shown_is_not_reported_as_ok():
    """`SENT` is also unproven. git saying it sent something is not origin showing the ref."""
    cmd = _strip_templates(_step_cmd("push the lane"))
    sent = cmd.split('if [ "$rc" -eq 0 ]; then', 1)[1].split("fi\n", 1)[0]
    assert "SENT" in sent, "the sent branch is gone; rewrite this test"
    exits = re.findall(r"^\s*exit (\d+)", sent, re.MULTILINE)
    assert exits, f"the sent branch no longer names its exit code: {sent!r}"
    assert all(int(code) != 0 for code in exits), (
        f"the sent branch exits 0 for a push origin never confirmed: exits={exits}"
    )


def test_a_proved_push_still_exits_zero(sandbox: Path):
    """The other half of the falsifier: a good push must NOT be turned red by this change.

    A guard that refuses correct work is an outage, so the fix must be proved to accept the
    success case as well as reject the failure case."""
    body = (
        _base_git()
        + 'case "$1" in\n'
        + "  rev-parse) echo abc123 ;;\n"
        + '  ls-remote) printf "abc123\\trefs/heads/lane/x\\n" ;;\n'
        + "  push) exit 0 ;;\n"
        + "esac\n"
    )
    result = _run_push_step(sandbox, body)
    assert result.returncode == 0, (
        "a push whose ref IS on origin was reported as a failure: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "ok      lane-submit" in result.stdout + result.stderr, (
        f"the success message is gone: {result.stdout!r} {result.stderr!r}"
    )
