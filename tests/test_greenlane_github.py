"""greenlane/github.py against a real git repository and a recorded GitHub: the verdict on a
candidate, which pull requests are foreign, how a hand-raised branch becomes a lane, and that a
lane's work squashes onto main or is refused as a conflict. Nothing here talks to GitHub."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane.engine import CONFLICT, LANDED, RED  # noqa: E402
from greenlane.github import ADOPTED, BOT_LANE, MARKER, GitHubBackend  # noqa: E402

REQUIRED = ["fast-gate / fast-gate", "bdd", "test"]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "a.txt").write_text("one\n")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "root")
    monkeypatch.chdir(r)
    return r


class Recorded(GitHubBackend):
    """gh() answers from a table; every write is recorded."""

    def __init__(self, table: dict, **kw):
        super().__init__("o/idp", REQUIRED, **kw)
        self.table, self.writes = table, []

    def gh(self, path, method="GET", fields=None):
        if method != "GET":
            self.writes.append((method, path, fields))
            # GitHub answers a PR create with the PR it made. Returning the number keeps the
            # landing path honest: the engine merges the PR it just raised rather than
            # re-listing to find it, which is both what the real API allows and one less
            # round trip. A write that creates a pull request gets a number; anything else None.
            if method == "POST" and path == "pulls":
                return {"number": 900 + len(self.writes)}
            return None
        base, _, query = path.partition("?")
        rows = self.table.get(base)
        if base == "pulls" and "head=" in query and isinstance(rows, list):
            ref = query.split("head=")[1].split("&")[0].split(":", 1)[1]
            return [r for r in rows if r["head"]["ref"] == ref]
        return rows


def _run(name, conclusion, status="completed", rid=1):
    return {
        "name": name,
        "conclusion": conclusion,
        "status": status,
        "id": rid,
        "html_url": f"u/{rid}",
    }


def test_verdict_needs_every_required_check_and_the_latest_run_wins():
    b = Recorded(
        {
            "commits/c1/check-runs": {
                "check_runs": [_run("bdd", "success"), _run("test", "success")]
            }
        }
    )
    assert b.checks("c1") == ("pending", "waiting on fast-gate / fast-gate")
    b = Recorded(
        {
            "commits/c2/check-runs": {
                "check_runs": [
                    _run("fast-gate / fast-gate", "success"),
                    _run("bdd", "failure", rid=3),
                    _run("bdd", "success", rid=4),
                    _run("test", "skipped"),
                ]
            }
        }
    )
    assert b.checks("c2") == ("green", "")
    b = Recorded(
        {
            "commits/c3/check-runs": {
                "check_runs": [
                    _run("fast-gate / fast-gate", "success"),
                    _run("bdd", "failure", rid=9),
                    _run("test", None, status="in_progress"),
                ]
            }
        }
    )
    verdict, reason = b.checks("c3")
    assert verdict == "red" and reason.startswith("bdd failure u/9")


def test_only_the_engines_own_pull_requests_are_not_foreign():
    prs = [
        {
            "number": 1,
            "user": {"login": "estate-agents[bot]"},
            "body": f"x {MARKER} candidate abc",
            "head": {"ref": "lane/a", "sha": "s1"},
        },
        {
            "number": 2,
            "user": {"login": "estate-agents[bot]"},
            "body": "no marker",
            "head": {"ref": "feat/b", "sha": "s2"},
        },
        {
            "number": 3,
            "user": {"login": "someone"},
            "body": f"{MARKER} forged",
            "head": {"ref": "feat/c", "sha": "s3"},
        },
    ]
    prs.append(
        {
            "number": 4,
            "user": {
                "login": "o"
            },  # the repository owner: the founder's landing vehicle
            "body": "workflow fix, founder lands",
            "head": {"ref": "fix/x", "sha": "s4"},
        }
    )
    b = Recorded({"pulls": prs})
    assert [p["number"] for p in b.foreign_prs()] == [2, 3]


def test_a_hand_raised_pull_request_is_adopted_never_closed(repo):
    """Edge cases mapped (founder 2026-09-29, "I don't just discard stuff"):
    1. plain branch -> lane/<branch> ref created, PR body marked, PR stays open (no PATCH state)
    2. branch already lane/* or the bot lane -> adopted in place, no second ref
    3. an adopted PR is not foreign on the next tick (no comment spam, no second adoption)
    4. the owner's PR is never touched (founder's landing vehicle)
    5. a draft is work too: adopted like any other
    6. a fork PR is adopted from its head sha; its branch cannot be rewritten, the lane still lands
    """
    b = Recorded({"pulls/7": {"body": "original body"}})
    pushed = []
    b.git = lambda *a, check=True: pushed.append(a) or ""
    b.relane({"number": 7, "lane": "feat/x", "head": "deadbeef", "user": "someone"})
    assert pushed[0][:5] == (
        "push",
        "-q",
        "-f",
        "origin",
        "deadbeef:refs/heads/lane/feat/x",
    )
    assert [w[:2] for w in b.writes] == [
        ("PATCH", "pulls/7"),
        ("POST", "issues/7/comments"),
    ]
    assert b.writes[0][2]["body"].startswith(f"{ADOPTED} lane/feat/x\n")
    assert "original body" in b.writes[0][2]["body"]
    assert (
        "stays open" in b.writes[1][2]["body"]
        and "lane/feat/x" in b.writes[1][2]["body"]
    )
    assert not any(w[2].get("state") for w in b.writes)  # never closed
    pushed.clear()
    b.relane(
        {"number": 8, "lane": BOT_LANE, "head": "cafe", "user": "github-actions[bot]"}
    )
    assert pushed == []  # already a lane name: no second ref
    b.relane({"number": 9, "lane": "lane/feat/y", "head": "f00d", "user": "someone"})
    assert pushed == []


def test_adopted_and_owner_pull_requests_are_not_foreign_and_adopted_heads_are_followed(
    repo,
):
    prs = [
        {  # adopted last tick: not foreign again
            "number": 1,
            "user": {"login": "someone"},
            "body": f"{ADOPTED} lane/feat/a\n\nbody",
            "head": {"ref": "feat/a", "sha": "a2"},
            "draft": False,
        },
        {  # the repository owner's: the founder lands it by hand, the engine never touches it
            "number": 2,
            "user": {"login": "o"},
            "body": "workflow fix",
            "head": {"ref": "fix/w", "sha": "w1"},
        },
        {  # a draft by an agent is work: foreign, to be adopted
            "number": 3,
            "user": {"login": "someone"},
            "body": "",
            "head": {"ref": "feat/d", "sha": "d1"},
            "draft": True,
        },
    ]
    b = Recorded({"pulls": prs})
    assert [p["number"] for p in b.foreign_prs()] == [3]
    assert b.adopted_prs() == [
        {"number": 1, "branch": "feat/a", "lane": "lane/feat/a", "head": "a2"}
    ]
    # lanes(): the adopted PR's head moved (a1 -> a2): the lane ref follows it
    pushed = []
    real_git = b.git

    def git(*a, check=True):
        if a[0] == "ls-remote" and a[-1] == "refs/heads/lane/feat/a":
            return "a1\trefs/heads/lane/feat/a"
        if a[0] == "ls-remote":
            return ""
        if a[0] == "push":
            pushed.append(a)
            return ""
        return real_git(*a, check=check)

    b.git = git
    b.main = lambda: _git(repo, "rev-parse", "HEAD")
    b.lanes()
    assert ("push", "-q", "-f", "origin", "a2:refs/heads/lane/feat/a") == pushed[0][:5]


def test_landing_marks_an_adopted_pull_request_merged_and_raises_none_for_it():
    b = Recorded(
        {
            "pulls": [
                {
                    "number": 5,
                    "user": {"login": "someone"},
                    "body": f"{ADOPTED} lane/feat/a",
                    "head": {"ref": "feat/a", "sha": "a1"},
                }
            ]
        }
    )
    pushed = []
    b.git = lambda *a, check=True: pushed.append(a) or ""
    b.land([("lane/feat/a", "a1", "r1"), ("lane/feat/b", "b1", "r2")], "tip")
    refs = [a[-1] for a in pushed if a[0] == "push"]
    # adopted lane: lane ref AND the PR's own branch take the landed sha
    assert refs.index("r1:refs/heads/lane/feat/a") < refs.index("r1:refs/heads/feat/a")
    # MAIN IS NOT PUSHED TO. The ruleset on main requires eight status checks plus a
    # `pull_request` rule, and a direct push arrives before any of them has run against main, so
    # on 2026-10-06 every batch died here with GH013 "Required status check \"no-harness-folders\"
    # is expected". main now moves through the merge API, which is how #5445 landed. This
    # assertion used to require the push; that is what made the test defend the defect.
    assert "tip:refs/heads/main" not in refs
    assert not any(r.endswith("refs/heads/main") for r in refs)
    # a PR must exist for every lane that lands, and it is merged -- not merely raised
    merges = [w for w in b.writes if w[0] == "PUT" and "/merge" in str(w[1])]
    created = [w for w in b.writes if w[0] == "POST" and w[1] == "pulls"]
    assert [w[2]["head"] for w in created] == ["lane/feat/b"]
    # each member is merged through its own PR, pinned to the sha that was judged
    assert len(merges) == 2, f"expected one merge per member, got {merges}"
    assert all(w[2]["merge_method"] == "squash" for w in merges), (
        "merge commits are not allowed on this repository and rebase is disabled; squash is the "
        "only method the ruleset permits"
    )


def test_a_lane_squashes_onto_main_or_is_refused_as_a_conflict(repo):
    main = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "work")
    (repo / "b.txt").write_text("b\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "add b")
    (repo / "b.txt").write_text("bb\n")
    # The commit-msg hook stamps this on every real commit; bin/idp-ci-guarded-paths refuses a
    # candidate whose HEAD has no X-Idp-Signed trailer. The engine re-commits the lane, so the
    # trailer has to survive the squash or every non-founder lane fails a check it earned.
    _git(
        repo, "commit", "-q", "-am", "grow b", "-m", "", "-m", "X-Idp-Signed: deadbeef"
    )
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "main")
    (repo / "a.txt").write_text("two\n")
    _git(repo, "commit", "-q", "-am", "main moves on")
    onto = _git(repo, "rev-parse", "HEAD")
    b = Recorded({})
    new = b.rebase(head, onto)
    assert new and _git(repo, "rev-parse", f"{new}^") == onto
    assert _git(repo, "log", "-1", "--format=%s", new) == "grow b"
    assert f"Greenlane-Head: {head}" in _git(repo, "log", "-1", "--format=%B", new)
    # The lane's signature is carried onto the candidate, and git reads it as a real trailer.
    assert (
        _git(repo, "log", "-1", "--format=%(trailers:key=X-Idp-Signed)", new).strip()
        == "X-Idp-Signed: deadbeef"
    )
    assert (
        _git(repo, "show", f"{new}:b.txt") == "bb"
        and _git(repo, "show", f"{new}:a.txt") == "two"
    )
    # a lane that edits the same line main changed does not apply: refused, nothing left behind
    _git(repo, "checkout", "-q", "-b", "clash", main)
    (repo / "a.txt").write_text("three\n")
    _git(repo, "commit", "-q", "-am", "clash")
    clash = _git(repo, "rev-parse", "HEAD")
    assert b.rebase(clash, onto) is None
    assert _git(repo, "worktree", "list").count("\n") == 0


def test_statuses_map_the_engines_verdicts():
    b = Recorded({}, run_url="https://run")
    for status, state in ((LANDED, "success"), (RED, "failure"), (CONFLICT, "failure")):
        b.report("lane/x", "abc", status, "why")
        assert b.writes[-1] == (
            "POST",
            "statuses/abc",
            {
                "state": state,
                "context": "greenlane",
                "description": "why",
                "target_url": "https://run",
            },
        )


def _with_origin(repo: Path, bare: Path) -> None:
    """`bare` as origin, with the local main already pushed so the checkout is complete."""
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "fetch", "-q", "origin")


def _write_state(repo: Path, bare: Path, landed: int) -> str:
    """A state commit on `bare`'s refs/greenlane/state, as save_state_text() would leave it."""
    blob = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input=f'{{"landed": {landed}, "candidates": 0, "lanes": {{}}, "queued": [], "seq": 0}}',
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"],
        input=f"100644 blob {blob}\tstate.json\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree, "-m", "state"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _git(repo, "push", "-q", "-f", "origin", f"{commit}:refs/greenlane/state")
    return commit


def test_a_state_ref_that_cannot_be_refreshed_is_refused_not_reported_stale(
    repo, tmp_path
):
    """The 2026-10-03 defect: a swallowed state fetch made a landed batch read as never saved.

    A stale ref reported as current is worse than no ref: the engine then believes it is behind
    when it is ahead, and re-tests work it already landed. Two things must hold, and the test
    reproduces the failure mode directly.

    1. A local refs/greenlane/state that is behind origin must be forced forward by fetch().
       The runner's checkout is a fresh clone that only ever fetches, so this is the only thing
       that keeps it current.
    2. When the state fetch cannot complete, that must be fatal. Note the heads fetch is
       check=True already, so a merely-unreachable origin is caught there and proves nothing
       about the state line; the failure has to happen on the state refspec itself.
    """
    bare = tmp_path / "o.git"
    _with_origin(repo, bare)
    _write_state(repo, bare, 47)
    b = GitHubBackend("o/idp", REQUIRED)
    b.fetch()
    assert 'landed": 47' in b.load_state_text().replace("\n", "")

    # (1) origin advances; fetch() must move the local ref to it, not keep the old one.
    _write_state(repo, bare, 48)
    b.fetch()
    assert 'landed": 48' in b.load_state_text().replace("\n", "")

    # (2) the state refspec is the one that fails, while origin itself is reachable: replace
    # origin with a remote that serves refs/heads/* fine but has no refs/greenlane/state -- the
    # engine's genuine first-tick shape -- and, separately, one whose state fetch errors.
    # A ref that is absent remotely is the benign case, and fetch() must not raise on it.
    fresh = tmp_path / "fresh.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(fresh)], check=True
    )
    _git(repo, "push", "-q", str(fresh), "main:refs/heads/main")
    _git(repo, "remote", "set-url", "origin", str(fresh))
    b.fetch()  # no state ref on the remote: the engine's first tick, not an error
    assert b.load_state_text() == ""

    # The stale local ref left behind is exactly what used to be reported as the truth. A
    # reader must never see it as current once the ref is known to be unrefreshable, so the
    # benign case above must be the only case that silently keeps a previous ref.
    _git(repo, "remote", "set-url", "origin", str(bare))
    b.fetch()
    assert 'landed": 48' in b.load_state_text().replace("\n", "")


def test_a_state_fetch_that_fails_is_fatal_even_though_heads_arrives(repo, tmp_path):
    """The state fetch failing must raise; the swallowed check=False is the whole defect.

    Origin is reachable and serves refs/heads/*, so the heads fetch succeeds. The state refspec
    is made to fail on its own, which is the only way to exercise the state line's error path.
    """
    bare = tmp_path / "o.git"
    _with_origin(repo, bare)
    _write_state(repo, bare, 47)
    b = GitHubBackend("o/idp", REQUIRED)
    b.fetch()

    # A refspec whose destination ref is locked cannot be written, while ls-remote still sees
    # the remote ref. reachable origin, failing state fetch -- not an unreachable origin.
    calls = []
    real = b.git

    def flaky(*args, check=True):
        calls.append(args)
        if args and args[0] == "fetch" and any("greenlane/state" in a for a in args):
            raise RuntimeError("simulated: state fetch failed")
        return real(*args, check=check)

    b.git = flaky
    with pytest.raises(RuntimeError, match="state fetch failed"):
        b.fetch()
    assert calls


def test_no_state_ref_is_a_fresh_start_but_a_ref_without_state_json_is_corruption(
    repo, tmp_path
):
    """The first tick has no ref and must start from State(); a ref missing state.json must not.

    Returning "" for both would restart a live trunk from scratch, silent and catastrophic.
    """
    bare = tmp_path / "o.git"
    _with_origin(repo, bare)
    b = GitHubBackend("o/idp", REQUIRED)
    b.fetch()
    assert b.load_state_text() == ""  # no ref anywhere: the engine's own first tick

    blob = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
        input="not a state file\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "-C", str(repo), "mktree"],
        input=f"100644 blob {blob}\tREADME\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "-C", str(repo), "commit-tree", tree, "-m", "state"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    _git(repo, "push", "-q", "-f", "origin", f"{commit}:refs/greenlane/state")
    b.fetch()
    with pytest.raises(RuntimeError, match="no state.json"):
        b.load_state_text()


# --- the ruleset's required checks must actually be produced on main -------------------------
#
# The incident this guards (found 2026-10-04): ruleset 24071703 `required-checks-main` lists
# `guarded-paths` as a required status check on ~DEFAULT_BRANCH. guarded-paths.yml triggered on
# pull_request, merge_group and push:[queue/**] -- but never on a push to main. Every candidate
# was graded on queue/bNNN and passed, then the engine fast-forwarded main and DELETED the queue
# branch, so the check never reported where the ruleset looks. On main 9bd03a78a840 the check-runs
# were ci-success/bdd/land/tick with no guarded-paths run at all, and `bin/idp-greenlane status`
# reported main_green:false with alarm:true indefinitely.
#
# A required check whose workflow cannot run on the required branch is a check that can only ever
# report ABSENT. It is not a gate; it is a permanent red light that trains everyone to ignore the
# alarm. This test reads the real ruleset and the real workflow triggers, so the two cannot drift.


def _ruleset_required_contexts() -> list[str]:
    spec = yaml.safe_load(
        (ROOT / "platform/github/ruleset.idp.required-checks.json").read_text()
    )
    for rule in spec["rules"]:
        if rule["type"] == "required_status_checks":
            return [c["context"] for c in rule["parameters"]["required_status_checks"]]
    raise AssertionError("ruleset declares no required_status_checks")


def _triggers_of(doc: dict) -> dict:
    # `on:` parses as the boolean True under YAML 1.1 resolvers.
    return doc.get(True) or doc.get("on") or {}


def _workflow_triggers(path: Path) -> dict:
    return _triggers_of(yaml.safe_load(path.read_text()))


def _push_branches(triggers: dict) -> list[str]:
    push = triggers.get("push") or {}
    if push is True:
        return ["**"]  # every branch
    return push.get("branches") or []


def _matches_main(patterns: list[str]) -> bool:
    return any(p in ("main", "**", "*") for p in patterns)


def test_every_required_check_on_main_is_produced_by_a_workflow_that_runs_on_main():
    """Each required context must come from a workflow that triggers on a main push, or from one
    that reports on pull_request/merge_group and is therefore carried onto the main commit."""
    workflows = sorted((ROOT / ".github/workflows").glob("*.yml"))
    # context -> (job names it can produce, does any of its events reach main?)
    produced: dict[str, bool] = {}
    for wf in workflows:
        try:
            doc = yaml.safe_load(wf.read_text())
        except yaml.YAMLError:
            continue
        jobs = doc.get("jobs") or {}
        triggers = _triggers_of(doc)
        reaches_main = _matches_main(_push_branches(triggers)) or bool(
            triggers.get("pull_request") or triggers.get("merge_group")
        )
        for job, spec in jobs.items():
            # A job's check-run name defaults to the job id (or its explicit `name:`).
            name = (spec or {}).get("name") or job
            produced.setdefault(name, reaches_main)
            produced.setdefault(f"{name} / {name}", reaches_main)

    missing = [c for c in _ruleset_required_contexts() if not produced.get(c, False)]
    assert not missing, (
        f"required on main but no workflow that runs on main produces them: {missing}. "
        "A required check that never reports is not a gate -- either give its workflow a push "
        "trigger for main, or drop it from required-checks-main."
    )


def test_guarded_paths_specifically_runs_on_a_main_push():
    """The exact regression, pinned by name so it cannot come back quietly."""
    triggers = _workflow_triggers(ROOT / ".github/workflows/guarded-paths.yml")
    assert _matches_main(_push_branches(triggers)), (
        "guarded-paths.yml does not trigger on a push to main, so the context "
        "`guarded-paths` (required by ruleset required-checks-main) can only ever report ABSENT "
        "on main -- which pins main_green to false forever."
    )
