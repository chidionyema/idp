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
  6. The cap never eats a `FAIL` line and never truncates in silence. Rules 1-5 shipped with
     `| tail -40` over the whole block, and every test above has exactly one failing dir, so the
     cap never bit. `bin/idp-kyverno-render $dirs` judges ~25 dirs in one run: with two failing
     dirs at 25 policy lines each, the last 40 of 52 lines contain the second dir's header and
     none of the first's, and the block opens mid-stream on an indented policy line with no dir
     above it and no note that 12 lines were cut -- the operator reads one failing dir where
     there are two. That is rule 1 defeated by a threshold instead of by a grep. A Kyverno policy
     bump fails many dirs at once, which is when the cap fires, so this is the ordinary case.

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


# ---------------------------------------------------------------------------
# Rule 6. crew#292, 2026-08-28.
# ---------------------------------------------------------------------------


def _two_failing_dirs(policy_lines=25):
    """What a policy bump looks like: two dirs refused, each with its own policy list."""
    out = ["ok    render   external-dns (edge, 0 patches): pass: 32, fail: 0"]
    for d in ("platform/state", "platform/litellm"):
        out.append(f"FAIL  plain    {d}: pass: 30, fail: {policy_lines}")
        out += [f"      policy rule-{i} -> {d.split('/')[1]} failed" for i in range(policy_lines)]
    return "\n".join(out)


def test_the_cap_never_eats_a_failing_dir():
    """The regression: `| tail -40` kept zero lines naming the first dir."""
    out = run(_two_failing_dirs())
    assert "platform/state" in out, out
    assert "platform/litellm" in out, out


def test_a_capped_block_names_every_failing_dir_before_it_drops_anything():
    """The `FAIL` lines are the index into the failure, so they come first and uncapped."""
    out = run(_two_failing_dirs())
    body = [ln.strip() for ln in out.splitlines() if ln != HEAD and ln.strip()]
    heads = [i for i, ln in enumerate(body) if ln.startswith("FAIL  plain")]
    assert len(heads) == 2, body[:6]
    assert heads == [0, 1], "a dropped line came before a dir header; the index is not first"


def test_the_cap_says_how_many_lines_it_dropped():
    """A silent truncation reads as `that was all of it`. 52 in, 40 out, 12 named."""
    out = run(_two_failing_dirs())
    assert "12 of 52 lines dropped by the cap" in out, out
    assert "2 dir(s) failed" in out, out


def test_a_block_that_fits_is_not_annotated_at_all():
    """Under the cap nothing is added: the 24-clean-dirs and tool-error cases are untouched."""
    out = run("FAIL  plain    platform/state: pass: 30, fail: 1\n      policy x -> y failed")
    assert "dropped by the cap" not in out, out
    body = [ln for ln in out.splitlines() if ln != HEAD and ln.strip()]
    assert len(body) == 2, body


def test_the_capped_block_is_still_one_screen():
    """Rule 5 is not traded away to buy rule 6: the total is still 40 lines."""
    body = [ln for ln in run(_two_failing_dirs()).splitlines() if ln != HEAD and ln.strip()]
    assert len(body) == 40, len(body)
