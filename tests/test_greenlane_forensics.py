"""The forensic auditor must refuse to guess, and must still find real loss.

`greenlane/forensics.py` reports work nobody merged: how many lines survived, and who killed the
PR. Its whole value is that its numbers are measured, so the tests here are adversarial in a
specific way -- each one is a situation where the easy answer is a fabricated number, and the
assertion is that the auditor refuses it.

Named follow-up risk, if any of these go red: an agent reading `lost_work` and re-cutting work
that is already in main, which wastes the work twice -- once when it stranded, once when it is
duplicated.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from greenlane import forensics as F  # noqa: E402


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _repo_with_main(tmp_path):
    """A worktree with a real git repo and a real origin/main, so git answers honestly."""
    repo = str(tmp_path)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (tmp_path / "kept.txt").write_text("this line is in main\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    # A local ref named origin/main is what the auditor reads; a real remote is not required.
    _git(
        repo,
        "update-ref",
        "refs/remotes/origin/main",
        _git(repo, "rev-parse", "HEAD").strip(),
    )
    return repo


# ---------------------------------------------------------------- the classifier
def test_claim_gate_failure_is_never_called_mechanical():
    """#7895's real defect: "claim-gate" contains "claim", so 10 PRs were called auto-healable.

    Failing the claim gate means the change had no claim. A normalizer cannot fix that, and
    telling an agent to try is how a mechanical heal becomes a wasted cycle.
    """
    assert F._classify(["claim-gate", "ci-success"], True, True) == "GENUINE"


def test_dof_gate_failure_is_never_called_mechanical():
    """A downed critical service narrows every agent; that is not cosmetic either."""
    assert F._classify(["dof-gate", "ci-success"], True, True) == "GENUINE"


def test_a_cosmetic_failure_beside_a_substantive_one_is_genuine():
    """ruff AND claim-gate failing: the ruff is incidental, the claim is the problem."""
    assert F._classify(["ruff", "claim-gate"], True, True) == "GENUINE"


def test_only_cosmetic_checks_are_mechanical():
    assert F._classify(["ruff"], True, True) == "MECHANICAL"
    assert F._classify(["yamllint", "markdownlint"], True, True) == "MECHANICAL"


def test_an_unreadable_rollup_is_unknown_not_mechanical():
    """BLIND is an honest answer. Calling it mechanical sends an agent to fix nothing."""
    assert F._classify([], False, False) == "UNKNOWN"


def test_checks_that_all_passed_and_still_closed_are_genuine():
    """No failing check but the PR was closed: something real stopped it, not a linter."""
    assert F._classify([], True, True) == "GENUINE"


def test_no_check_ever_ran_is_unknown():
    assert F._classify([], True, False) == "UNKNOWN"


# ---------------------------------------------------------------- the verdict
def test_a_shallow_checkout_yields_unmeasured_and_never_lost():
    """The single most dangerous fabrication: truncated history answers "not an ancestor".

    A shallow clone does not error on `merge-base --is-ancestor`; it says NO to everything below
    the boundary. Measured before the guard: 39 PRs reported LOST at 0/5761 lines.
    """
    assert (
        F._verdict(added=100, surviving=0, in_main=False, shallow=True) == "UNMEASURED"
    )


def test_zero_survivors_of_real_work_is_lost():
    assert F._verdict(added=100, surviving=0, in_main=False) == "LOST"


def test_some_survivors_is_partial():
    assert F._verdict(added=100, surviving=40, in_main=False) == "PARTIAL"


def test_a_commit_in_main_landed_even_if_survival_looks_low():
    """Reachability outranks probe arithmetic: a squashed merge can rewrite every line."""
    assert F._verdict(added=100, surviving=0, in_main=True) == "LANDED"


def test_a_commit_that_added_nothing_is_empty_not_lost():
    assert F._verdict(added=0, surviving=0, in_main=False) == "EMPTY"


# ---------------------------------------------------------------- reachability
def test_an_empty_ancestor_set_is_a_finding_not_a_failure(tmp_path):
    """0 of 30 closed PR heads are ancestors of main. That is the expected answer.

    The first draft treated an empty set as "could not read main", printed "reachability
    unknown", and made a true superseded=0 look blind.
    """
    repo = _repo_with_main(tmp_path)
    in_main, ok = F._ancestor_set(["deadbeef" * 5], "origin/main", repo)
    assert ok is True, (
        "an empty answer from a readable main must still count as a valid read"
    )
    assert in_main == set()


def test_reachability_reports_failure_when_the_ref_is_unreadable(tmp_path):
    """An unreadable ref must be distinguishable from an empty answer -- this is the flag."""
    repo = _repo_with_main(tmp_path)
    _in_main, ok = F._ancestor_set(["deadbeef" * 5], "origin/does-not-exist", repo)
    assert ok is False


# ---------------------------------------------------------------- survival, scoped
def test_survival_finds_a_line_that_really_is_in_main(tmp_path):
    repo = _repo_with_main(tmp_path)
    hits = F._survival_in_paths(
        {"s": ["this line is in main"]}, {"s": ["kept.txt"]}, repo, ref="origin/main"
    )
    assert hits["this line is in main"] is True


def test_survival_does_not_find_a_line_that_is_absent(tmp_path):
    repo = _repo_with_main(tmp_path)
    hits = F._survival_in_paths(
        {"s": ["a line nobody ever wrote"]},
        {"s": ["kept.txt"]},
        repo,
        ref="origin/main",
    )
    assert hits["a line nobody ever wrote"] is False


def test_survival_reads_only_the_paths_it_was_given(tmp_path):
    """Scoping is the optimisation AND a correctness fix (#7402).

    A line that exists in main but in a file this commit never touched must NOT be credited as
    survival -- that is how generic JSON boilerplate made #7402 look 131/164 survived.
    """
    repo = _repo_with_main(tmp_path)
    hits = F._survival_in_paths(
        {"s": ["this line is in main"]},
        {"s": ["elsewhere.txt"]},
        repo,
        ref="origin/main",
    )
    assert hits == {}, (
        "a commit that touched no existing path has nothing to match against"
    )


def test_survival_is_blind_rather_than_zero_when_nothing_can_be_read(tmp_path):
    """Empty must mean BLIND at the caller; an empty dict here is the signal, not a false."""
    repo = _repo_with_main(tmp_path)
    assert (
        F._survival_in_paths(
            {"s": ["x"]}, {"s": ["absent.txt"]}, repo, ref="origin/main"
        )
        == {}
    )


# ---------------------------------------------------------------- added lines
def test_added_lines_ignores_context_and_whitespace_only_lines(tmp_path):
    """A context line 'surviving' says nothing about whether this change landed."""
    repo = _repo_with_main(tmp_path)
    (tmp_path / "kept.txt").write_text("this line is in main\nbrand new line\n   \n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add")
    sha = _git(repo, "rev-parse", "HEAD").strip()
    added = F._added_lines(sha, repo)
    assert "brand new line" in added
    assert "this line is in main" not in added, "a context line is not added work"
    assert all(line.strip() for line in added), "whitespace-only lines are not work"


# ---------------------------------------------------------------- the manifest
def test_the_manifest_is_written_with_its_schema(tmp_path, monkeypatch):
    """The manifest is the re-queue contract; without a schema it cannot be trusted."""
    out = tmp_path / "manifest.json"
    monkeypatch.setattr(F, "MANIFEST_PATH", str(out))
    monkeypatch.setattr(
        F, "audit_repo", lambda slug, path, limit: F.RepoAudit(slug, path)
    )
    monkeypatch.setattr(F, "render", lambda audits: "")
    assert F.main(["chidionyema/idp=/tmp/x"]) == 0
    data = json.loads(out.read_text())
    assert data["schema"] == "greenlane.salvage-manifest.v1"
    assert isinstance(data["repos"], list)


def test_a_repo_with_no_checkout_is_blind_not_clean(tmp_path):
    """ "Could not look" must never read as "nothing was lost"."""
    audit = F.audit_repo("chidionyema/idp", str(tmp_path / "does-not-exist"), limit=5)
    assert audit.blind, "an absent checkout must report BLIND"
    assert audit.stranded == []
