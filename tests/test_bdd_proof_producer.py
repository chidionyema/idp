"""Falsifier for the producer's citation: the block the producer builds must be ACCEPTED
by the real gate against the real check-run payload, and the blocks that name something
that did not run or ran red must be REFUSED.

Everything here runs the REAL gate (bin/idp-bdd-proof-gate) as a subprocess. Nothing is
re-implemented: the gate is the only grader, so a test that agreed with itself would
prove nothing.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-bdd-proof-gate"
SHA = "615785e4145c16a52afb79dea8e79b90f6045fbe"
PAYLOAD = Path("/tmp/dr-front/proof/checkruns-615785e.json")
STUBBIN = Path("/tmp/dr-front/proof/stubbin")

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


def _gate(pr_json, use_stub=True):
    env = dict(os.environ)
    if use_stub:
        env["PATH"] = f"{STUBBIN}:{env.get('PATH', '')}"
    tmp = Path("/tmp/dr-front/proof/_gate_case.json")
    tmp.write_text(json.dumps(pr_json))
    p = subprocess.run(
        [sys.executable, str(GATE), str(tmp)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    return p.returncode, (p.stdout + p.stderr).strip()


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
        assert latest["conclusion"] in ("success", "neutral", "skipped"), (
            f"{name} cited but concluded {latest['conclusion']}"
        )


def test_producer_block_is_accepted_by_the_real_gate():
    """The block the producer writes must pass the real gate against the real payload."""
    payload = json.loads(PAYLOAD.read_text())
    gg = _backend(payload)
    block = gg._proof_block(SHA)
    assert "greenlane" not in block, "the block names the absent check"
    code, out = _gate({"number": 0, "title": "t", "headRefOid": SHA, "body": block})
    assert code == 0, f"the real gate refused the producer's own block: {out}"
    assert "8 cited check(s) green" in out, f"unexpected gate output: {out}"


def test_a_citation_naming_the_absent_greenlane_is_refused():
    """The shape the producer used to emit must still be refused -- the falsifier."""
    block = (
        f"BDD-PROOF\nhead: {SHA}\nchecks: {SHA} "
        + ", ".join(REQUIRED)
        + "\nEND-BDD-PROOF\n"
    )
    code, out = _gate({"number": 0, "title": "t", "headRefOid": SHA, "body": block})
    assert code == 1, f"a citation naming an absent check was accepted: {out}"
    assert "greenlane" in out, f"the refusal did not name the absent check: {out}"


def test_a_citation_naming_a_red_check_is_refused():
    """A red check on the cited commit must be refused, not accepted."""
    payload = json.loads(PAYLOAD.read_text())
    red = next(
        (
            r["name"]
            for r in payload["check_runs"]
            if r["conclusion"] not in ("success", "neutral", "skipped")
            and r["name"] in REQUIRED
        ),
        None,
    )
    if red is None:
        return  # no red required check on this commit: nothing to falsify
    block = f"BDD-PROOF\nhead: {SHA}\nchecks: {SHA} {red}\nEND-BDD-PROOF\n"
    code, out = _gate({"number": 0, "title": "t", "headRefOid": SHA, "body": block})
    assert code == 1, f"a red check was accepted: {out}"


def test_an_unreadable_check_run_is_blind_not_a_pass():
    """A check-run answer that cannot be read -> the gate is BLIND (exit 2), never a pass.

    The failure is FORCED with a stub gh that refuses, so this case does not depend on the
    network's mood. A gate that answered "ok" when it could not read the ground truth
    would be a fail-open gate -- the defect this whole change exists to close.
    """
    payload = json.loads(PAYLOAD.read_text())
    gg = _backend(payload)
    block = gg._proof_block(SHA)
    refuse_bin = Path("/tmp/dr-front/proof/refusebin")
    refuse_bin.mkdir(parents=True, exist_ok=True)
    refuse = refuse_bin / "gh"
    refuse.write_text(
        "#!/usr/bin/env bash\n"
        'echo "gh: stub refuses to read the check runs" >&2\n'
        "exit 1\n"
    )
    refuse.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{refuse_bin}:{env.get('PATH', '')}"
    tmp = Path("/tmp/dr-front/proof/_gate_refuse_case.json")
    tmp.write_text(
        json.dumps({"number": 0, "title": "t", "headRefOid": SHA, "body": block})
    )
    p = subprocess.run(
        [sys.executable, str(GATE), str(tmp)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    out = (p.stdout + p.stderr).strip()
    assert p.returncode == 2, f"an unreadable check-run answer was not BLIND: {out}"
    assert "cannot read the check runs" in out, (
        f"the BLIND message named the wrong reason: {out}"
    )
