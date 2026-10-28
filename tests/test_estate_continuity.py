"""The continuity rescue: what it copies, what it refuses to touch, and what it reports.

The rescue is the estate's answer to a dead session: work that exists only on this machine is
copied to origin as a salvage branch, so the work outlives the machine. These tests pin the three
properties that make it safe to run unattended:

  - it only ever ADDS branches under backup/preserve-*: no push to main, no force, no delete;
  - it never touches the owner of a dirty worktree: the capture goes through a temporary index, so
    that worktree's own index, files and HEAD are exactly as it was;
  - it never reports a rescue it did not measure: a push that fails is FAILED, and a run that
    cannot read the repository is BLIND (exit 2), never clean.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESCUE = ROOT / "platform/estate/libexec/estate-rescue.py"


def load_rescue():
    spec = importlib.util.spec_from_file_location("estate_rescue", RESCUE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    out = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


@pytest.fixture()
def repo(tmp_path):
    """A repository with a bare origin, one commit on main, and a branch only on origin."""
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", str(origin)], check=True, capture_output=True
    )
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-b", "main")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    (work / "README.md").write_text("hello\n")
    git(work, "add", "README.md")
    git(work, "commit", "-m", "first")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "origin", "main")
    git(work, "checkout", "-b", "lane/kept")
    (work / "kept.txt").write_text("kept\n")
    git(work, "add", "kept.txt")
    git(work, "commit", "-m", "kept")
    git(work, "push", "origin", "lane/kept")
    git(work, "checkout", "main")
    git(work, "checkout", "-b", "lane/lost")
    (work / "lost.txt").write_text("lost\n")
    git(work, "add", "lost.txt")
    git(work, "commit", "-m", "lost")
    return work


def test_slug_is_a_readable_salvage_branch_name():
    module = load_rescue()
    name = module.slug("lane/the-imported-instruments")
    assert name.startswith("backup/preserve-")
    assert name.endswith("lane-the-imported-instruments")
    assert " " not in name


def test_plan_rescues_only_what_is_on_no_remote(repo):
    module = load_rescue()
    refs, err = module.origin_heads(repo)
    assert err is None
    rows, err = module.plan(refs, repo)
    assert err is None
    names = [r["name"] for r in rows]
    assert "lane/lost" in names
    assert "lane/kept" not in names  # origin already holds it
    assert "main" not in names  # it is on main: nothing is at risk
    assert all(r["target"].startswith("backup/preserve-") for r in rows)


def test_capture_takes_the_dirty_files_without_touching_the_worktree(repo):
    module = load_rescue()
    (repo / "dirty.txt").write_text("work in progress\n")
    before = git(repo, "status", "--porcelain")
    commit, err = module.capture_tree(str(repo))
    assert err is None
    assert commit
    after = git(repo, "status", "--porcelain")
    assert before == after  # the owner's index and files are untouched
    shown = git(repo, "show", "{}:dirty.txt".format(commit))
    assert "work in progress" in shown
    assert git(repo, "rev-parse", "HEAD").strip() != commit  # HEAD did not move


def test_rescue_pushes_and_reads_the_ref_back(repo):
    module = load_rescue()
    refs, _ = module.origin_heads(repo)
    rows, _ = module.plan(refs, repo)
    judged = module.rescue(rows, 25, repo)
    rescued = [r for r in judged if r["verdict"] == "RESCUED"]
    assert [r["name"] for r in rescued] == ["lane/lost"]
    target = rescued[0]["target"]
    assert target.startswith("backup/preserve-")
    on_origin = git(repo, "ls-remote", "--heads", "origin", target)
    assert target in on_origin  # the rescue was measured, not asserted


def test_rescue_defers_when_the_budget_is_spent(repo):
    module = load_rescue()
    refs, _ = module.origin_heads(repo)
    rows, _ = module.plan(refs, repo)
    judged = module.rescue(rows, 0, repo)
    assert all(r["verdict"] == "DEFERRED" for r in judged)


def test_a_failed_push_is_failed_not_rescued(tmp_path):
    module = load_rescue()
    work = tmp_path / "noremote"
    work.mkdir()
    git(work, "init", "-b", "main")
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-m", "first")
    rows = [
        {
            "kind": "branch",
            "name": "lane/lost",
            "sha": git(work, "rev-parse", "HEAD").strip(),
            "target": "backup/preserve-20260101-lane-lost",
            "verdict": "PLANNED",
            "why": "",
        }
    ]
    judged = module.rescue(rows, 25, work)
    assert judged[0]["verdict"] == "FAILED"
    assert "push failed" in judged[0]["why"]


def test_the_census_names_the_claim_that_holds_the_work(tmp_path):
    module = load_rescue()
    ledger = tmp_path / "latest.json"
    ledger.write_text(
        '{"items": [{"name": "lane/lost", "claim": "idp#7142", "live": false},'
        ' {"name": "lane/other", "claim": "idp#7311", "live": true}]}'
    )
    census = module.load_census(ledger)
    assert census["lane/lost"] == {"claim": "idp#7142", "live": False}
    assert census["lane/other"]["live"] is True


def test_the_work_of_a_dead_headless_session_goes_first():
    module = load_rescue()
    rows = [
        {"name": "lane/alive", "kind": "branch", "verdict": "PLANNED"},
        {"name": "lane/dead", "kind": "branch", "verdict": "PLANNED"},
        {"name": "lane/unclaimed", "kind": "branch", "verdict": "PLANNED"},
    ]
    census = {
        "lane/alive": {"claim": "idp#7311", "live": True},
        "lane/dead": {"claim": "idp#7142", "live": False},
    }
    order = [r["name"] for r in module.prioritize(rows, census)]
    assert order == ["lane/dead", "lane/unclaimed", "lane/alive"]


def test_blind_is_not_clean(tmp_path, capsys):
    module = load_rescue()
    code = module.main(["--repo", str(tmp_path / "nowhere")])
    assert code == 2
    assert "BLIND" in capsys.readouterr().out


def test_a_dry_run_pushes_nothing(repo, capsys):
    module = load_rescue()
    module.main(["--repo", str(repo), "--dry-run"])
    text = capsys.readouterr().out
    assert "WOULD-RESCUE" in text
    assert "backup/preserve-" in text
    heads = git(repo, "ls-remote", "--heads", "origin")
    assert "backup/preserve-" not in heads
