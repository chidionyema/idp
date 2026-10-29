"""The bdd proof gate grades one way, and it can fail (2026-10-29).

`bin/idp-bdd-proof-gate` used to have two opinions: file mode demanded a runner's own
counts and a matching head, while `--live` demanded only that a block existed. The same
block was refused by one and accepted by the other -- measured on PR #7466: `refused:
the proof block carries no passing BDD run` (exit 1) from file mode, `ok: PR #7466
carries a BDD-PROOF block` (exit 0) from `--live`, one identical body. A gate with two
opinions is a gate that cannot be trusted to say no.

These tests pin the closed contract:

  * ONE grader. `grade()` is the only place a verdict is produced, and both modes call
    it, so the same pull request cannot get two verdicts.
  * TWO evidence shapes, both the runner's own. Counts the runner printed ("36 passed
    in 24.03s"), or a checks citation (`checks: <sha> <name,...>`) that the gate
    verifies ITSELF against GitHub's check-runs API for that exact commit -- so the
    block's own words are never taken on trust.
  * IT CAN FAIL. Every refusal below is asserted. A gate whose refusals were never
    exercised is a gate that cannot fail.

The three fixtures under `tests/fixtures/bdd-proof/` were written for this gate and
committed without a single test reading them -- an orphaned corpus, which is a corpus
that proves nothing. They are the falsifier corpus here.
"""

import json
import pathlib
from importlib.machinery import SourceFileLoader

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-bdd-proof-gate"
FIXTURES = ROOT / "tests" / "fixtures" / "bdd-proof"


def load_gate():
    """The gate, loaded as a module (it has no .py suffix: it is a bin/ script)."""
    return SourceFileLoader("bdd_proof_gate_under_test", str(GATE)).load_module()


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


# --------------------------------------------------------------------------
# The orphan corpus, now read by something.
# --------------------------------------------------------------------------


def test_good_fixture_is_accepted():
    gate = load_gate()
    code, msg = gate.grade(fixture("good"), verify=False)
    assert code == 0, f"a real proof was refused: {msg}"


def test_bad_fixture_is_refused():
    """Prose only. `I ran the BDD suite and it passed locally.` is a claim, not a run."""
    gate = load_gate()
    code, msg = gate.grade(fixture("bad"), verify=False)
    assert code == 1, f"a prose claim was accepted: {msg}"
    assert "carries no" in msg, f"the refusal named the wrong reason: {msg}"


def test_stale_head_fixture_is_refused():
    """The proof names `aaaa...` but the pull request's head is `cccc...`."""
    gate = load_gate()
    code, msg = gate.grade(fixture("stale-head"), verify=False)
    assert code == 1, f"a proof on the wrong head was accepted: {msg}"
    assert "head is" in msg, f"the refusal named the wrong reason: {msg}"


# --------------------------------------------------------------------------
# One grader: the two modes cannot disagree.
# --------------------------------------------------------------------------


def test_file_mode_and_live_mode_grade_the_same_pull_request_identically():
    """The defect this file exists for, pinned.

    The live mode fetches a pull request and hands it to `grade()`. The file mode reads
    a pull request from a file and hands it to the SAME `grade()`. So the verdict is
    identical by construction -- and this test proves the construction, rather than
    trusting it: it grades one pull request through the file-mode entry point and
    through the live-mode entry point's grader, and requires the same code and the same
    refusal reason.
    """
    gate = load_gate()
    pr = fixture("bad")

    # File mode: the whole process, on the fixture on disk.
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(GATE), str(FIXTURES / "bad.json")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 1, f"file mode accepted a prose claim: {proc.stdout}"

    # Live mode's grader, on the same pull request.
    code, msg = gate.grade(pr)
    assert code == 1, f"live mode accepted a prose claim: {msg}"
    assert "carries no" in msg, f"live mode named a different reason: {msg}"

    # The same reason, so the refusal reads the same to whoever is watching.
    assert "carries no" in proc.stderr, (
        f"file mode named a different reason: {proc.stderr}"
    )


def test_the_same_pull_request_gets_the_same_verdict_every_time():
    """No ordering, no caching, no first-call-wins: one pull request, one verdict."""
    gate = load_gate()
    pr = fixture("good")
    verdicts = {gate.grade(pr, verify=False) for _ in range(5)}
    assert len(verdicts) == 1, f"the grader disagreed with itself: {verdicts}"


# --------------------------------------------------------------------------
# The two evidence shapes.
# --------------------------------------------------------------------------


def test_counts_are_accepted_as_the_runners_own_evidence():
    gate = load_gate()
    for line in (
        "36 passed in 24.03s",
        "31 scenarios (31 passed)",
        "8 features (8 passed)",
        "142 steps (142 passed)",
        "0 failed",
        "Tests: 31 passed, 31 total",
    ):
        block = f"BDD-PROOF\nhead: abc1234\n{line}\nEND-BDD-PROOF"
        assert gate.looks_like_a_pass(block), f"a real runner line was refused: {line}"


@pytest.mark.parametrize(
    "prose",
    [
        "i ran the tests and they passed",
        "tests pass",
        "all green",
        "bdd is green",
        "verified manually",
    ],
)
def test_prose_is_never_a_pass(prose):
    gate = load_gate()
    block = f"BDD-PROOF\nhead: abc1234\n{prose}\nEND-BDD-PROOF"
    assert not gate.looks_like_a_pass(block), f"prose was taken as a run: {prose}"


def test_a_checks_citation_is_parsed():
    gate = load_gate()
    block = "BDD-PROOF\nhead: abc1234\nchecks: abc1234 test, bdd\nEND-BDD-PROOF"
    assert gate.checks_citation(gate.extract_block(block)) == (
        "abc1234",
        ["test", "bdd"],
    )


def test_a_counts_block_has_no_checks_citation():
    """The two shapes are distinguishable, so the gate knows which rule to apply."""
    gate = load_gate()
    block = "BDD-PROOF\nhead: abc1234\n36 passed in 24.03s\nEND-BDD-PROOF"
    assert gate.checks_citation(gate.extract_block(block)) is None


def test_a_citation_on_the_right_head_is_accepted():
    """The citation path, with verification switched off (no network in a unit test)."""
    gate = load_gate()
    pr = {
        "title": "t",
        "headRefOid": "abc1234def",
        "body": "BDD-PROOF\nhead: abc1234\nchecks: abc1234 test\nEND-BDD-PROOF",
    }
    code, msg = gate.grade(pr, verify=False)
    assert code == 0, f"a citation on this head was refused: {msg}"


def test_a_citation_naming_a_red_check_is_refused(monkeypatch):
    """THE FALSIFIER for the citation shape.

    A citation is evidence only because the gate re-reads the ground truth. Here the
    check runs are stubbed so the test needs no network: one green check and one red
    one. The green citation passes; the red citation is refused, and the refusal names
    the check and its conclusion.
    """
    gate = load_gate()

    runs = [
        {"name": "test", "status": "completed", "conclusion": "success"},
        {"name": "bdd", "status": "completed", "conclusion": "failure"},
        {"name": "slow", "status": "in_progress", "conclusion": None},
    ]
    monkeypatch.setattr(gate, "check_runs_for", lambda sha: runs)

    green = {
        "title": "t",
        "headRefOid": "abc1234def",
        "body": "BDD-PROOF\nhead: abc1234\nchecks: abc1234 test\nEND-BDD-PROOF",
    }
    code, msg = gate.grade(green)
    assert code == 0, f"a green citation was refused: {msg}"

    red = {
        "title": "t",
        "headRefOid": "abc1234def",
        "body": "BDD-PROOF\nhead: abc1234\nchecks: abc1234 bdd\nEND-BDD-PROOF",
    }
    code, msg = gate.grade(red)
    assert code == 1, f"a RED citation was accepted: {msg}"
    assert "bdd" in msg and "failure" in msg, f"the refusal did not name it: {msg}"

    pending = {
        "title": "t",
        "headRefOid": "abc1234def",
        "body": "BDD-PROOF\nhead: abc1234\nchecks: abc1234 slow\nEND-BDD-PROOF",
    }
    code, msg = gate.grade(pending)
    assert code == 1, f"a PENDING citation was accepted: {msg}"

    missing = {
        "title": "t",
        "headRefOid": "abc1234def",
        "body": "BDD-PROOF\nhead: abc1234\nchecks: abc1234 never-ran\nEND-BDD-PROOF",
    }
    code, msg = gate.grade(missing)
    assert code == 1, f"a citation naming a check that never ran was accepted: {msg}"
    assert "did not run" in msg, f"the refusal did not name it: {msg}"


def test_a_citation_that_cannot_be_verified_is_blind_not_a_pass(monkeypatch):
    """gh down -> exit 2 BLIND. Never a pass: a gate that cannot read the truth must
    not pass on silence."""
    gate = load_gate()

    def boom(sha):
        raise RuntimeError("gh could not read the check runs")

    monkeypatch.setattr(gate, "check_runs_for", boom)
    pr = {
        "title": "t",
        "headRefOid": "abc1234def",
        "body": "BDD-PROOF\nhead: abc1234\nchecks: abc1234 test\nEND-BDD-PROOF",
    }
    code, msg = gate.grade(pr)
    assert code == 2, f"an unverifiable citation was not BLIND: {code} {msg}"


# --------------------------------------------------------------------------
# The producer: what the Greenlane writes must satisfy the gate.
# --------------------------------------------------------------------------


def test_the_greenlane_producer_writes_a_block_the_gate_accepts(monkeypatch):
    """One producer, one shape: what greenlane/github.py writes must pass the gate.

    The Greenlane cannot cite runner COUNTS (CI's counts live in the job log, and the
    check-runs API returns an empty output.title and output.summary for every check run
    on this repository -- measured 2026-10-29 over all 100 check runs on commit
    2f6b2fb37). So it writes a checks citation, and this test proves that shape is
    accepted by the one grader -- which is the whole point of the change.
    """
    gate = load_gate()
    import sys

    sys.path.insert(0, str(ROOT))
    try:
        from greenlane.github import GitHubBackend  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 - the module may need optional deps
        pytest.skip(f"greenlane.github is not importable in this environment: {exc}")
    finally:
        sys.path.pop(0)

    required = ["fast-gate / fast-gate", "bdd", "test"]
    gg = GitHubBackend.__new__(GitHubBackend)
    gg.required = required
    gg.repo = "chidionyema/idp"

    sha = "abc1234def5678"

    # The producer reads the ground truth itself, so the check runs are stubbed at the
    # API boundary. The `greenlane` check is ABSENT here on purpose: the Greenlane
    # creates that check while landing, so before landing it did not run, and a producer
    # that cited it would be refused by the gate for citing a check that does not exist.
    ran_green = ["fast-gate / fast-gate", "bdd"]
    runs = [
        {"name": n, "status": "completed", "conclusion": "success"} for n in ran_green
    ]
    gg.gh = lambda path, method="GET", fields=None: {"check_runs": runs}

    block = gg._proof_block(sha)

    assert "greenlane" not in required, "the fixture lost its absent check"
    assert "test" not in block, f"the producer cited a check that did not run: {block}"
    assert "bdd" in block, (
        f"the producer failed to cite a check that ran green: {block}"
    )

    # The block the producer wrote must satisfy the one grader.
    monkeypatch.setattr(gate, "check_runs_for", lambda s: runs)
    pr = {"title": "t", "headRefOid": sha, "body": block}
    code, msg = gate.grade(pr)
    assert code == 0, f"the Greenlane's own block was refused by the gate: {msg}"


# --------------------------------------------------------------------------
# The gate's own self-test runs, and it is a test of the refusals.
# --------------------------------------------------------------------------


def test_the_gate_self_test_passes():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(GATE), "--self-test"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"the gate's self-test failed: {proc.stderr}"
    assert "ok bdd-proof-gate --self-test" in proc.stdout, proc.stdout


def test_the_gate_self_test_actually_fails_when_the_grader_is_broken(tmp_path):
    """THE FALSIFIER FOR THE FALSIFIER.

    A self-test that cannot fail is not a self-test. So: take the gate, break its
    refusal -- make `grade()` accept everything -- and prove the self-test then fails.
    If the self-test still passed, the self-test would be decoration, and this whole
    file would be decoration too.
    """
    import subprocess
    import sys

    broken = tmp_path / "broken-gate"
    text = GATE.read_text()
    # Make the grader accept every proof: the refusal path becomes unreachable.
    patched = text.replace(
        "    if not looks_like_a_pass(block):\n"
        '        return 1, "the proof block carries no passing BDD run"\n',
        "    if not looks_like_a_pass(block):\n"
        '        return 0, "ok: bdd proof on head {proved}"\n',
    )
    assert patched != text, "the patch did not apply; the self-test's premise changed"
    broken.write_text(patched)

    proc = subprocess.run(
        [sys.executable, str(broken), "--self-test"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0, (
        "the self-test passed against a gate whose refusals were broken -- "
        "the self-test cannot fail"
    )
