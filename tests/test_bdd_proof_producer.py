"""Falsifier for the producer's citation: the block the producer builds must be ACCEPTED
by the real gate against the real check-run payload, and the blocks that name something
that did not run or ran red must be REFUSED.

Everything here runs the REAL gate (bin/idp-bdd-proof-gate) as a subprocess. Nothing is
re-implemented: the gate is the only grader, so a test that agreed with itself would
prove nothing.

THE PAYLOAD IS A COMMITTED FIXTURE, NOT A LIVE CALL. `tests/fixtures/bdd-proof/
checkruns-615785e.json` is the verbatim check-runs answer GitHub returned for commit
615785e4145c16a52afb79dea8e79b90f6045fbe (total_count 52, 52 check runs), captured
2026-10-29. A test that called the network would prove whatever the network felt like
that minute; a test that called itself would prove nothing. The fixture pins the ground
truth the citation is verified against, so the falsifier is the same on every machine.

The `gh` the gate shells out to is STUBBED to serve that fixture, so the gate's own
verification path -- read the check runs for the cited commit, refuse a missing or red
one -- is the code under test.
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-bdd-proof-gate"
SHA = "615785e4145c16a52afb79dea8e79b90f6045fbe"
PAYLOAD = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "bdd-proof"
    / "checkruns-615785e.json"
)

sys.path.insert(0, str(ROOT))
from greenlane.github import GitHubBackend  # noqa: E402

REQUIRED = [
    "fast-gate / fast-gate",
    "bdd",
    "guarded-paths",
    "test",
    "executes-gate",
    "feature-request-plan",
    "ci-success",
    "portal-app",
    "greenlane",
]

GREEN = ("success", "neutral", "skipped")


def _backend(payload):
    gg = GitHubBackend.__new__(GitHubBackend)
    gg.required = REQUIRED
    gg.repo = "chidionyema/idp"
    gg.run_url = "https://example.invalid/run"

    def fake_gh(path, method="GET", fields=None):
        if path.startswith("commits/"):
            return payload
        raise AssertionError(f"unexpected gh call: {path}")

    gg.gh = fake_gh
    return gg


def _stub_gh(tmp_path, payload=None, refuse=False):
    """A `gh` on PATH that answers the gate's check-runs call, or refuses.

    `payload=None` and `refuse=True` makes it fail, which is how the BLIND case is
    FORCED rather than waited for: a test that depends on the network's mood is a
    test that will one day report a green gate as a pass.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    gh = bindir / "gh"
    if refuse:
        gh.write_text(
            '#!/usr/bin/env bash\necho "gh: stub refuses to read the check runs" >&2\nexit 1\n'
        )
    else:
        gh.write_text(f'#!/usr/bin/env bash\ncat "{PAYLOAD}"\n')
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bindir


def _gate(tmp_path, pr_json, refuse=False):
    env = dict(os.environ)
    env["PATH"] = f"{_stub_gh(tmp_path, refuse=refuse)}:{env.get('PATH', '')}"
    tmp = tmp_path / "case.json"
    tmp.write_text(json.dumps(pr_json))
    p = subprocess.run(
        [sys.executable, str(GATE), str(tmp)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def test_the_fixture_is_the_measured_ground_truth():
    """The fixture must be the real answer, not a hand-written shape.

    A falsifier built on a payload the author invented would refuse exactly what it
    was written to refuse and prove nothing about the real one. The numbers below are
    the ones measured on 2026-10-29 for this commit.
    """
    payload = json.loads(PAYLOAD.read_text())
    assert payload.get("total_count") == 52, (
        f"unexpected total_count: {payload.get('total_count')}"
    )
    runs = payload.get("check_runs") or []
    assert len(runs) == 52, f"expected 52 check runs, got {len(runs)}"
    names = {r["name"] for r in runs}
    assert "greenlane" not in names, "the fixture must NOT contain the landing check"


def test_producer_cites_only_checks_that_actually_ran_green():
    """The absent `greenlane` check must NOT be cited; the 8 real green ones must be."""
    payload = json.loads(PAYLOAD.read_text())
    gg = _backend(payload)
    green = gg._green_required(SHA)
    assert "greenlane" not in green, f"cited a check that did not run: {green}"
    assert len(green) == 8, f"expected the 8 measured green checks, got {green}"
    for name in green:
        runs = [r for r in payload["check_runs"] if r["name"] == name]
        assert runs, f"{name} cited but absent from the payload"
        latest = max(runs, key=lambda r: r["id"])
        assert latest["status"] == "completed", f"{name} cited but not completed"
        assert latest["conclusion"] in GREEN, (
            f"{name} cited but concluded {latest['conclusion']}"
        )


def test_producer_block_is_accepted_by_the_real_gate(tmp_path):
    """The block the producer writes must pass the real gate against the real payload."""
    payload = json.loads(PAYLOAD.read_text())
    gg = _backend(payload)
    block = gg._proof_block(SHA)
    assert "greenlane" not in block, "the block names the absent check"
    code, out = _gate(
        tmp_path, {"number": 0, "title": "t", "headRefOid": SHA, "body": block}
    )
    assert code == 0, f"the real gate refused the producer's own block: {out}"
    assert "8 cited check(s) green" in out, f"unexpected gate output: {out}"


def test_a_citation_naming_the_absent_greenlane_is_refused(tmp_path):
    """The shape the producer used to emit must still be refused -- the falsifier."""
    block = (
        f"BDD-PROOF\nhead: {SHA}\nchecks: {SHA} "
        + ", ".join(REQUIRED)
        + "\nEND-BDD-PROOF\n"
    )
    code, out = _gate(
        tmp_path, {"number": 0, "title": "t", "headRefOid": SHA, "body": block}
    )
    assert code == 1, f"a citation naming an absent check was accepted: {out}"
    assert "greenlane" in out, f"the refusal did not name the absent check: {out}"


def test_a_citation_naming_a_red_check_is_refused(tmp_path):
    """A red check on the cited commit must be refused, not accepted."""
    payload = json.loads(PAYLOAD.read_text())
    red = next(
        (
            r["name"]
            for r in payload["check_runs"]
            if r["conclusion"] not in GREEN and r["name"] in REQUIRED
        ),
        None,
    )
    if red is None:
        return  # no red required check on this commit: nothing to falsify
    block = f"BDD-PROOF\nhead: {SHA}\nchecks: {SHA} {red}\nEND-BDD-PROOF\n"
    code, out = _gate(
        tmp_path, {"number": 0, "title": "t", "headRefOid": SHA, "body": block}
    )
    assert code == 1, f"a red check was accepted: {out}"


def test_an_unreadable_check_run_is_blind_not_a_pass(tmp_path):
    """A check-run answer that cannot be read -> the gate is BLIND (exit 2), never a pass.

    The failure is FORCED with a stub gh that refuses, so this case does not depend on the
    network's mood. A gate that answered "ok" when it could not read the ground truth
    would be a fail-open gate -- the defect this whole change exists to close.
    """
    payload = json.loads(PAYLOAD.read_text())
    gg = _backend(payload)
    block = gg._proof_block(SHA)
    code, out = _gate(
        tmp_path,
        {"number": 0, "title": "t", "headRefOid": SHA, "body": block},
        refuse=True,
    )
    assert code == 2, f"an unreadable check-run answer was not BLIND: {out}"
    assert "cannot read the check runs" in out, (
        f"the BLIND message named the wrong reason: {out}"
    )
