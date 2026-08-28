"""crew#292: bin/idp-ci's kyverno rung printed a headline and nothing else.

On idp#589 the offline-gate job failed with exactly two lines in the log:

    FAIL  kyverno  a HelmRelease or workload render fails admission policy
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No dir, no policy, no cause. The rung captured the judge's whole output into `$kyv`
and then printed `grep -E '^(FAIL|      )'` of it. Those two shapes are what
bin/idp-kyverno-render emits *when it reaches a verdict*: `FAIL  plain <dir>: ...`
and the indented `policy ... failed` lines under it. A render that dies before any
verdict -- kustomize `error: must build at directory`, a helm template failure, a
chart that will not pull -- writes neither shape, so the grep matched nothing and the
one sentence that said why was destroyed by the instrument reporting it (LAW 28), and
nobody could attribute the failure without re-running the judge by hand (LAW 29).

The rules this file holds:

  1. Whatever the judge said about a failure reaches the log. Not a shape of it.
  2. A tool error that names no policy -- the shape that produced the bare underline --
     is the case that must survive, because it is the one the old grep dropped.
  3. The verdict shapes that used to survive still survive: the `FAIL` line and the
     indented `policy ... failed` lines under it.
  4. `ok` verdicts are dropped. Twenty-four clean dirs must not bury the failing one.
  5. The block is tail-capped, so a judge that floods cannot flood the receipt.

The block is not copied here. It is read out of bin/idp-ci at the line where the
kyverno rung decides a non-zero rc, and executed, so a change to that file is graded
by these tests rather than a paraphrase of it.
"""
import pathlib
import subprocess

import pytest

IDP = pathlib.Path(__file__).resolve().parents[1]
CI = IDP / "bin" / "idp-ci"
HEAD = "FAIL  kyverno  a HelmRelease or workload render fails admission policy"


def _branch():
    """The real body of the `kyv_rc != 0` arm, lifted from bin/idp-ci by its own lines."""
    src = CI.read_text().splitlines()
    start = next(i for i, ln in enumerate(src) if ln.strip() == 'elif [ "$kyv_rc" != 0 ]; then')
    end = next(i for i in range(start + 1, len(src)) if src[i].lstrip().startswith("elif "))
    body = "\n".join(src[start + 1 : end])
    assert "kyv" in body, "the arm no longer reads the judge's output; this test is stale"
    return body


def run(kyv):
    """Execute that arm with the judge's output as bin/idp-ci would have captured it."""
    script = "say() { printf '%s\\n' \"$1\"; }\nfail=0\nkyv=$(cat <<'K_EOF'\n" + kyv + "\nK_EOF\n)\n" + _branch()
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_the_headline_still_names_the_rung():
    assert HEAD in run("FAIL  plain    platform/state: pass: 3, fail: 1")


def test_a_tool_error_that_names_no_policy_reaches_the_log():
    """Rule 2: the exact shape that left run 33173089759 with a bare underline."""
    err = "error: must build at directory: not a valid directory: evalsymlink failure on 'platform/state'"
    out = run("policies  26 ClusterPolicies from /tmp/p\n" + err)
    assert err in out, out


@pytest.mark.parametrize(
    "line",
    [
        "Error: template: chart/templates/deploy.yaml:12:14: executing at <.Values.image.tag>: nil pointer",
        "Error: failed to download chart, no cached repo found",
        "panic: runtime error: invalid memory address",
    ],
)
def test_a_failure_the_judge_did_not_shape_as_a_verdict_still_travels(line):
    assert line in run(line)


def test_the_verdict_lines_that_always_survived_still_survive():
    """Rule 3: fixing the drop must not lose what the old grep did catch."""
    out = run(
        "ok    render   external-dns (edge, 0 patches): pass: 32, fail: 0\n"
        "FAIL  plain    platform/state: pass: 30, fail: 1, warn: 0, error: 0, skip: 1\n"
        "      policy require-run-as-nonroot -> state-collector failed"
    )
    assert "FAIL  plain    platform/state:" in out
    assert "policy require-run-as-nonroot -> state-collector failed" in out


def test_the_clean_dirs_do_not_bury_the_failing_one():
    """Rule 4: twenty-four `ok` verdicts and one failure prints one failure."""
    noise = "\n".join(f"ok    render   chart-{i} (ns, 0 patches): pass: 30, fail: 0" for i in range(24))
    out = run(noise + "\nFAIL  plain    platform/state: pass: 30, fail: 1")
    assert "ok    render" not in out
    assert "platform/state" in out
    assert len([ln for ln in out.splitlines() if ln.strip() and ln != HEAD]) == 1, out


def test_a_judge_that_floods_cannot_flood_the_receipt():
    """Rule 5: the cap is on the block, and the tail is where the cause is."""
    out = run("\n".join(f"error: line {i}" for i in range(200)))
    body = [ln for ln in out.splitlines() if ln != HEAD and ln.strip()]
    assert len(body) <= 40, len(body)
    assert "error: line 199" in out, "the cap kept the head and threw away the last thing said"


def test_the_rung_that_calls_this_arm_is_the_one_that_captured_the_judge():
    """The arm is reached from the real capture, not from a branch nothing runs."""
    src = CI.read_text()
    assert 'kyv=$( (cd "$IDP" && bin/idp-kyverno-render $dirs) 2>&1 ); kyv_rc=$?' in src
