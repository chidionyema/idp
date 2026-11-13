"""The BDD proof gate grades ONE pull request, with ONE predicate, and says so when it cannot look.

Issue #7467 (P0, 2026-11-11). Two defects, both falsifiable:

  1. `bin/idp-bdd-proof-gate --live` passed when it found ANY `BDD-PROOF` block -- even one
     naming a different commit, or naming no run at all -- and its `live_pr()` fell back to
     the NEWEST pull request on the repository when the event and the branch did not resolve
     to the pull request being graded.
  2. `bin/idp-ci` suppressed the gate's failures with `|| true`, so a blind or unrelated
     proof was reported as a successful admission.

The gate is exercised here as a PROCESS, with a fake `gh` on PATH and a fake event payload,
because the defects were in what it did with the outside world -- not in a helper. Every
case below is a case the old gate got wrong, and the exit codes are the contract:

    0  PROVED          the pull request carries proof on its own head commit
    1  REFUSED         no block, no passing run, or the run is not on this head
    2  BLIND           the pull request could not be read (no token, gh failed, bad payload)
    3  NOT APPLICABLE  there is no pull request under test; nothing was graded
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
GATE = IDP / "bin" / "idp-bdd-proof-gate"

HEAD = "a" * 40
OTHER = "c" * 40


# -- helpers --------------------------------------------------------------------------------


def clean_env(**extra: str) -> dict[str, str]:
    """An environment with no GitHub state in it.

    The suite runs inside a GitHub runner, where GITHUB_EVENT_PATH and GITHUB_HEAD_REF are
    set for the run itself. A test that inherits them grades the runner's pull request
    instead of its own case, which is how a test suite that cannot fail gets written.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_", "GH_"))}
    env["PATH"] = env.get("PATH", "/usr/bin:/bin")
    env.update(extra)
    return env


def run_gate(
    args: list[str], env: dict[str, str], stdin: str = ""
) -> tuple[int, str, str]:
    p = subprocess.run(  # noqa: S603 -- fixed argv
        [sys.executable, str(GATE), *args],
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return p.returncode, p.stdout, p.stderr


def said(text: str, word: str) -> bool:
    """Whether `text` says `word`. A helper, so no assert pins a long sentence."""
    return word in text


def fake_gh(tmp_path: Path, out: str = "", listing: str = "", rc: int = 0) -> Path:
    """A `gh` on PATH that records every call and answers with the given bytes."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    out_file = tmp_path / "gh-out.json"
    out_file.write_text(out)
    list_file = tmp_path / "gh-list.json"
    list_file.write_text(listing)
    script = bindir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$FAKE_GH_LOG"\n'
        'case "$*" in\n'
        '  *"pr list"*) f="$FAKE_GH_LIST" ;;\n'
        '  *) f="$FAKE_GH_OUT" ;;\n'
        "esac\n"
        '[ -n "$f" ] && [ -f "$f" ] && cat "$f"\n'
        'exit "${FAKE_GH_RC:-0}"\n'.replace("${FAKE_GH_RC:-0}", str(rc))
    )
    script.chmod(0o755)
    return bindir


def event_file(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "event.json"
    p.write_text(json.dumps(payload))
    return p


def pr_payload(number: int, body: str, head: str = HEAD) -> dict:
    return {
        "number": number,
        "title": "the pull request under test",
        "body": body,
        "headRefOid": head,
        "headRefName": "lane/demo",
    }


def proof_body(head: str = HEAD, evidence: str = "31 scenarios (31 passed)") -> str:
    return f"BDD-PROOF\nhead: {head}\ncommand: npm run bdd\n{evidence}\nEND-BDD-PROOF\n"


# -- the JSON mode: one predicate, both directions ------------------------------------------


def test_json_mode_accepts_a_proof_on_the_exact_head() -> None:
    rc, out, err = run_gate(
        [],
        clean_env(),
        stdin=json.dumps({"title": "t", "headRefOid": HEAD, "body": proof_body(HEAD)}),
    )
    assert rc == 0, f"rc={rc} out={out} err={err}"


def test_json_mode_refuses_a_proof_on_another_commit() -> None:
    rc, _out, err = run_gate(
        [],
        clean_env(),
        stdin=json.dumps({"title": "t", "headRefOid": HEAD, "body": proof_body(OTHER)}),
    )
    assert rc == 1, err


def test_json_mode_refuses_a_body_with_no_block() -> None:
    rc, _out, err = run_gate(
        [],
        clean_env(),
        stdin=json.dumps(
            {"title": "t", "headRefOid": HEAD, "body": "I ran the suite and it passed."}
        ),
    )
    assert rc == 1, err


def test_json_mode_refuses_a_block_that_only_asserts_in_prose() -> None:
    prose = (
        "BDD-PROOF\nhead: " + HEAD + "\ni ran the tests and they passed\nEND-BDD-PROOF"
    )
    rc, _out, err = run_gate(
        [],
        clean_env(),
        stdin=json.dumps({"title": "t", "headRefOid": HEAD, "body": prose}),
    )
    assert rc == 1, err


def test_json_mode_refuses_a_block_that_names_no_head() -> None:
    body = "BDD-PROOF\n31 scenarios (31 passed)\nEND-BDD-PROOF"
    rc, _out, err = run_gate(
        [],
        clean_env(),
        stdin=json.dumps({"title": "t", "headRefOid": HEAD, "body": body}),
    )
    assert rc == 1, err


def test_json_mode_is_blind_when_the_input_is_not_json() -> None:
    rc, _out, _err = run_gate([], clean_env(), stdin="not json at all")
    assert rc == 2


# -- the live mode: the event's pull request, and only that ----------------------------------


def test_live_mode_grades_the_pull_request_the_event_names(tmp_path: Path) -> None:
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": proof_body(HEAD),
                "head": {"sha": HEAD},
            }
        },
    )
    rc, out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
    assert rc == 0, f"rc={rc} out={out} err={err}"


def test_live_mode_refuses_a_block_that_names_another_commit(tmp_path: Path) -> None:
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": proof_body(OTHER),
                "head": {"sha": HEAD},
            }
        },
    )
    rc, _out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
    assert rc == 1, err


def test_live_mode_refuses_a_block_that_only_asserts_in_prose(tmp_path: Path) -> None:
    prose = "BDD-PROOF\nhead: " + HEAD + "\nall green\nEND-BDD-PROOF"
    ev = event_file(
        tmp_path,
        {"pull_request": {"number": 4242, "body": prose, "head": {"sha": HEAD}}},
    )
    rc, _out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
    assert rc == 1, err


def test_live_mode_refuses_a_pull_request_with_no_block_at_all(tmp_path: Path) -> None:
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": "no proof here",
                "head": {"sha": HEAD},
            }
        },
    )
    rc, _out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
    assert rc == 1, err


def test_live_mode_never_grades_the_newest_unrelated_pull_request(
    tmp_path: Path,
) -> None:
    """The defect that made `--live` a gate on somebody else's work.

    The pull request under test (4242) carries no proof. Somewhere else on the repository
    there is a pull request that does carry one. The old gate fell back to the newest
    pull request on the repository and passed. The gate must refuse 4242, and it must not
    even ask gh for a newest-pull-request listing.
    """
    unrelated = pr_payload(9999, proof_body(HEAD), head=HEAD)
    bindir = fake_gh(
        tmp_path,
        out=json.dumps(unrelated),
        listing=json.dumps([unrelated]),
    )
    log = tmp_path / "gh.log"
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": "this one carries no proof",
                "head": {"sha": HEAD},
            }
        },
    )
    env = clean_env(
        GITHUB_EVENT_PATH=str(ev),
        FAKE_GH_LOG=str(log),
        FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        FAKE_GH_LIST=str(tmp_path / "gh-list.json"),
    )
    env["PATH"] = f"{bindir}:{env['PATH']}"
    rc, _out, err = run_gate(["--live"], env)
    assert rc == 1, f"the gate passed an unproved pull request: {err}"
    calls = log.read_text().splitlines() if log.exists() else []
    for call in calls:
        assert not (said(call, "pr list") and not said(call, "--head")), (
            f"the gate fell back to a newest-pull-request listing: {call}"
        )


def test_live_mode_is_blind_when_the_event_payload_is_stale(tmp_path: Path) -> None:
    missing = tmp_path / "not-there.json"
    rc, _out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(missing)))
    assert rc == 2, err


def test_live_mode_is_blind_when_the_event_payload_is_not_json(tmp_path: Path) -> None:
    broken = tmp_path / "event.json"
    broken.write_text("{not json")
    rc, _out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(broken)))
    assert rc == 2, err


def test_live_mode_says_not_applicable_for_a_push_with_no_pull_request() -> None:
    rc, out, err = run_gate(["--live"], clean_env())
    assert rc == 3, f"rc={rc} out={out} err={err}"
    assert said(err, "no pull request under test"), err


def test_live_mode_says_not_applicable_for_the_greenlane_candidate(
    tmp_path: Path,
) -> None:
    """The candidate branch is a branch under test, not a pull request.

    The old gate answered this case by grading whatever pull request was newest on the
    repository -- a foreign pull request -- which is how a correct candidate was refused
    for another session's missing proof.
    """
    bindir = fake_gh(tmp_path, out="{}", listing="[]")
    log = tmp_path / "gh.log"
    env = clean_env(
        GITHUB_REF="refs/heads/queue/b4242",
        GITHUB_REPOSITORY="chidionyema/idp",
        GITHUB_REPOSITORY_OWNER="chidionyema",
        FAKE_GH_LOG=str(log),
        FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        FAKE_GH_LIST=str(tmp_path / "gh-list.json"),
    )
    env["PATH"] = f"{bindir}:{env['PATH']}"
    rc, _out, err = run_gate(["--live"], env)
    assert rc == 3, err
    assert not log.exists() or log.read_text().strip() == "", (
        "gh was called for a branch"
    )


def test_live_mode_is_not_applicable_for_a_push_to_the_default_branch(
    tmp_path: Path,
) -> None:
    ev = event_file(
        tmp_path,
        {
            "repository": {"default_branch": "main"},
            "after": HEAD,
        },
    )
    rc, _out, err = run_gate(
        ["--live"],
        clean_env(GITHUB_EVENT_PATH=str(ev), GITHUB_REF="refs/heads/main"),
    )
    assert rc == 3, err


# -- the live mode over gh: the branch, the merge group, and the blind ----------------------


def test_live_mode_grades_the_pull_request_with_the_named_head_branch(
    tmp_path: Path,
) -> None:
    pr = pr_payload(4242, proof_body(HEAD), head=HEAD)
    bindir = fake_gh(tmp_path, out=json.dumps(pr), listing=json.dumps([pr]))
    log = tmp_path / "gh.log"
    env = clean_env(
        GITHUB_HEAD_REF="lane/demo",
        GITHUB_REPOSITORY="chidionyema/idp",
        GITHUB_REPOSITORY_OWNER="chidionyema",
        FAKE_GH_LOG=str(log),
        FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        FAKE_GH_LIST=str(tmp_path / "gh-list.json"),
    )
    env["PATH"] = f"{bindir}:{env['PATH']}"
    rc, _out, err = run_gate(["--live"], env)
    assert rc == 0, f"rc={rc} err={err}"
    assert said(log.read_text(), "--head"), "the branch was not used to find the PR"


def test_live_mode_is_not_applicable_when_the_head_branch_has_no_pull_request(
    tmp_path: Path,
) -> None:
    bindir = fake_gh(tmp_path, out="{}", listing="[]")
    env = clean_env(
        GITHUB_HEAD_REF="lane/demo",
        GITHUB_REPOSITORY="chidionyema/idp",
        GITHUB_REPOSITORY_OWNER="chidionyema",
        FAKE_GH_LOG=str(tmp_path / "gh.log"),
        FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        FAKE_GH_LIST=str(tmp_path / "gh-list.json"),
    )
    env["PATH"] = f"{bindir}:{env['PATH']}"
    rc, _out, err = run_gate(["--live"], env)
    assert rc == 3, err


def test_live_mode_is_blind_when_gh_cannot_authenticate(tmp_path: Path) -> None:
    """No token: `gh` answers with its own refusal, and the gate must be BLIND.

    BLIND is not a pass and it is not a refusal of the work: it is the gate saying it
    could not look. `bin/idp-ci` turns it into a failure, because a proof nobody read is
    not a proof.
    """
    bindir = fake_gh(tmp_path, out="", listing="", rc=4)
    ev = event_file(
        tmp_path,
        {
            "merge_group": {
                "head_ref": "refs/heads/gh-readonly-queue/main/pr-4242-abc1234"
            }
        },
    )
    env = clean_env(
        GITHUB_EVENT_PATH=str(ev),
        GITHUB_REPOSITORY="chidionyema/idp",
        FAKE_GH_LOG=str(tmp_path / "gh.log"),
        FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        FAKE_GH_LIST=str(tmp_path / "gh-list.json"),
    )
    env["PATH"] = f"{bindir}:{env['PATH']}"
    rc, _out, err = run_gate(["--live"], env)
    assert rc == 2, f"rc={rc} err={err}"


def test_live_mode_reads_the_pull_request_a_merge_group_carries(tmp_path: Path) -> None:
    """When the merge-group payload carries the pull request, it is graded without a token."""
    ev = event_file(
        tmp_path,
        {
            "merge_group": {
                "head_ref": "refs/heads/gh-readonly-queue/main/pr-4242-abc1234"
            },
            "pull_requests": [
                {"number": 4242, "body": proof_body(OTHER), "head": {"sha": HEAD}}
            ],
        },
    )
    rc, _out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
    assert rc == 1, f"the merge-group pull request was not the one graded: {err}"


def test_live_mode_reads_the_pull_request_a_merge_group_names(tmp_path: Path) -> None:
    """The merge queue names its pull request in the head ref: pr-<n>-<sha>."""
    wrong_head = pr_payload(4242, proof_body(OTHER), head=HEAD)
    bindir = fake_gh(tmp_path, out=json.dumps(wrong_head), listing="[]")
    ev = event_file(
        tmp_path,
        {
            "merge_group": {
                "head_ref": "refs/heads/gh-readonly-queue/main/pr-4242-abc1234"
            }
        },
    )
    env = clean_env(
        GITHUB_EVENT_PATH=str(ev),
        GITHUB_REPOSITORY="chidionyema/idp",
        FAKE_GH_LOG=str(tmp_path / "gh.log"),
        FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        FAKE_GH_LIST=str(tmp_path / "gh-list.json"),
    )
    env["PATH"] = f"{bindir}:{env['PATH']}"
    rc, _out, err = run_gate(["--live"], env)
    assert rc == 1, f"the merge-group pull request was not the one graded: {err}"


def test_the_live_mode_and_the_json_mode_refuse_the_same_pull_request(
    tmp_path: Path,
) -> None:
    """One predicate, two modes: the same body gets the same verdict either way.

    The old gate graded the JSON mode properly and the live mode loosely, so a pull
    request could fail one and pass the other. Every case below is graded twice -- once
    through stdin, once through a pull_request event -- and the two verdicts must match.
    """
    cases = [
        ("exact head", proof_body(HEAD), 0),
        ("wrong head", proof_body(OTHER), 1),
        ("no block", "just a description", 1),
        (
            "prose only",
            "BDD-PROOF\nhead: "
            + HEAD
            + "\ni ran the tests and they passed\nEND-BDD-PROOF",
            1,
        ),
        ("no head named", "BDD-PROOF\n31 scenarios (31 passed)\nEND-BDD-PROOF", 1),
    ]
    for name, body, expected in cases:
        json_rc, _o, _e = run_gate(
            [],
            clean_env(),
            stdin=json.dumps({"title": name, "headRefOid": HEAD, "body": body}),
        )
        ev = event_file(
            tmp_path,
            {"pull_request": {"number": 7, "body": body, "head": {"sha": HEAD}}},
        )
        live_rc, _o2, _e2 = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
        assert json_rc == expected, f"{name}: json mode said {json_rc}"
        assert live_rc == expected, f"{name}: live mode said {live_rc}"


def test_the_exit_codes_are_the_documented_ones() -> None:
    """The four verdicts, by number: a caller that reads them must not guess."""
    import importlib.machinery
    import importlib.util

    loader = importlib.machinery.SourceFileLoader("bdd_proof_gate", str(GATE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.EXIT_PROVED == 0
    assert mod.EXIT_REFUSED == 1
    assert mod.EXIT_BLIND == 2
    assert mod.EXIT_NOT_APPLICABLE == 3


def test_zero_executed_bdd_evidence_is_refused_in_json_and_live(tmp_path: Path) -> None:
    """A zero-failure report is not evidence that any test executed."""
    zero_runs = (
        "0 failed",
        "0 passed, 0 failed",
        "0 scenarios (0 passed)",
        "0 features (0 passed)",
        "Tests: 0 passed, 0 total",
        "0 passed in 0.01s",
    )
    for evidence in zero_runs:
        body = proof_body(HEAD, evidence)
        rc, out, err = run_gate(
            [],
            clean_env(),
            stdin=json.dumps(
                {"title": "zero-test negative", "headRefOid": HEAD, "body": body}
            ),
        )
        assert rc == 1, f"JSON admitted {evidence!r}: rc={rc} out={out} err={err}"
        ev = event_file(
            tmp_path,
            {"pull_request": {"number": 4242, "body": body, "head": {"sha": HEAD}}},
        )
        rc, out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
        assert rc == 1, f"LIVE admitted {evidence!r}: rc={rc} out={out} err={err}"


def test_nonzero_bdd_evidence_remains_proved_in_json_and_live(tmp_path: Path) -> None:
    """Fail closed on zero execution without rejecting real nonzero counts."""
    positive_runs = (
        "31 scenarios (31 passed), 0 failed",
        "Tests: 1 passed, 1 total",
        "1 passed in 0.01s",
        "--- PASS: TestBDDGateway (0.02s)",
    )
    for evidence in positive_runs:
        body = proof_body(HEAD, evidence)
        rc, out, err = run_gate(
            [],
            clean_env(),
            stdin=json.dumps(
                {"title": "nonzero positive", "headRefOid": HEAD, "body": body}
            ),
        )
        assert rc == 0, f"JSON refused {evidence!r}: rc={rc} out={out} err={err}"
        ev = event_file(
            tmp_path,
            {"pull_request": {"number": 4242, "body": body, "head": {"sha": HEAD}}},
        )
        rc, out, err = run_gate(["--live"], clean_env(GITHUB_EVENT_PATH=str(ev)))
        assert rc == 0, f"LIVE refused {evidence!r}: rc={rc} out={out} err={err}"


def test_live_rerun_recovers_same_head_proof_corrected_after_event(
    tmp_path: Path,
) -> None:
    """GitHub Actions reruns replay the old event body, but the PR can be fixed."""
    number = 4242
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": number,
                "body": proof_body(OTHER),
                "head": {"sha": HEAD},
            }
        },
    )
    live = pr_payload(number, proof_body(HEAD), HEAD)
    bindir = fake_gh(tmp_path, out=json.dumps(live))
    log = tmp_path / "gh.log"
    rc, out, err = run_gate(
        ["--live"],
        clean_env(
            GITHUB_EVENT_PATH=str(ev),
            GH_TOKEN="read-only-test-token",
            PATH=f"{bindir}:{os.environ.get('PATH', '')}",
            FAKE_GH_LOG=str(log),
            FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        ),
    )
    assert rc == 0, f"{out} {err}"
    assert log.read_text().count("pr view 4242") == 1


def test_live_rerun_never_accepts_changed_head_from_same_pr(tmp_path: Path) -> None:
    """A newer commit needs its OWN event and proof; a fresh body is not enough."""
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": proof_body(OTHER),
                "head": {"sha": HEAD},
            }
        },
    )
    live = pr_payload(4242, proof_body(OTHER), OTHER)
    bindir = fake_gh(tmp_path, out=json.dumps(live))
    rc, _out, err = run_gate(
        ["--live"],
        clean_env(
            GITHUB_EVENT_PATH=str(ev),
            GH_TOKEN="read-only-test-token",
            PATH=f"{bindir}:{os.environ.get('PATH', '')}",
            FAKE_GH_LOG=str(tmp_path / "gh.log"),
            FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        ),
    )
    assert rc == 1, err


def test_live_rerun_never_accepts_foreign_pr_proof(tmp_path: Path) -> None:
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": "no proof",
                "head": {"sha": HEAD},
            }
        },
    )
    foreign = pr_payload(9999, proof_body(HEAD), HEAD)
    bindir = fake_gh(tmp_path, out=json.dumps(foreign))
    rc, _out, err = run_gate(
        ["--live"],
        clean_env(
            GITHUB_EVENT_PATH=str(ev),
            GH_TOKEN="read-only-test-token",
            PATH=f"{bindir}:{os.environ.get('PATH', '')}",
            FAKE_GH_LOG=str(tmp_path / "gh.log"),
            FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        ),
    )
    assert rc == 1, err


def test_live_rerun_github_lookup_failure_keeps_original_refusal(
    tmp_path: Path,
) -> None:
    ev = event_file(
        tmp_path,
        {
            "pull_request": {
                "number": 4242,
                "body": "no proof",
                "head": {"sha": HEAD},
            }
        },
    )
    bindir = fake_gh(tmp_path, out="", rc=1)
    rc, _out, err = run_gate(
        ["--live"],
        clean_env(
            GITHUB_EVENT_PATH=str(ev),
            GH_TOKEN="read-only-test-token",
            PATH=f"{bindir}:{os.environ.get('PATH', '')}",
            FAKE_GH_LOG=str(tmp_path / "gh.log"),
            FAKE_GH_OUT=str(tmp_path / "gh-out.json"),
        ),
    )
    assert rc == 1, err
