"""The falsifier for idp#8788 -- a diff-scoped gate that cannot name its base widens, never narrows.

Measured 2026-11-28. ci.yml's only pytest gate on a candidate is

    bin/idp-tests-for --base origin/main   (TESTS_FOR_ALL: "0")

and for two different commits an hour apart it printed the same three files and "30 passed"
(run 46150172966 job 140995357196 on queue/b6501, and run 46144445092 job 140977445226 on main).
The candidate's own tests/test_legion_admit.py holds 54 collected node ids, so it was not among
them: the change would have landed with its own tests never executed.

The selector did that because of one line:

    changed=$( { git diff "$base"...HEAD; git diff HEAD; git ls-files --others; } | sort -u )

`set -e` never reaches inside that assignment (its status is sort's), so an unresolvable base
contributed nothing -- and the job then graded the files earlier STEPS had written into the tree,
which are identical on every commit. actions/checkout hands a job a shallow clone, so origin/main
does not exist there: the log's own `fatal: bad revision 'origin/main...HEAD'` is the proof.

These tests are two-sided on purpose, because the fix must widen a blind gate without narrowing a
sighted one:

  - BLIND: a base neither the explicit flag nor bin/idp-ci-base can resolve runs every cheap file;
  - SIGHTED: a base that does resolve still selects only the tests that read the changed file, and
    the untracked files the job wrote never enter the change set;
  - the laptop keeps its own view: an author's uncommitted edit is still graded;
  - BLIND with no cheap set is exit 3, a refusal, never a green.

Every repository here is thrown away by the test; the estate's own repository is never touched.
The fixture's test files are stubs on purpose: the selector greps their SOURCE for a path, so a
stub is the honest shape of "a test that names this file".
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-tests-for"
RESOLVER = ROOT / "bin" / "idp-ci-base"
ZEROS = "0" * 40

GIT_LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _env(**extra: str) -> dict[str, str]:
    """A clean environment: no git redirection, no CI that leaks in from the runner, and no
    host git configuration.

    The last one is MEASURED, not defensive taste (2026-11-28): this machine's ~/.gitconfig sets
    `core.hooksPath = ~/.estate/hooks`, so a throwaway repo made here inherits the estate's
    pre-commit door -- and `git commit` in the fixture exited `ESTATE GATE: proof status FAIL`,
    which made the registered Optimus measure unreadable for a reason that has nothing to do with
    the selector. A fixture that grades one command must not be judged by another door, and on a
    fresh runner there is no user config to inherit.
    """
    env = dict(os.environ)
    for name in (*GIT_LOCATION_VARS, "CI", "TESTS_FOR_ALL", "TESTS_FOR_RUN"):
        env.pop(name, None)
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    for name in ("GITHUB_REF", "GITHUB_EVENT_NAME", "GITHUB_BASE_REF", "GITHUB_SHA"):
        env.pop(name, None)
    for name in (
        "ESTATE_CI_EVENT_NAME",
        "ESTATE_CI_REF",
        "ESTATE_CI_BASE_REF",
        "ESTATE_CI_BEFORE",
        "ESTATE_CI_PR_BASE_SHA",
        "ESTATE_CI_MERGE_GROUP_BASE",
    ):
        env.pop(name, None)
    env.update(
        GIT_AUTHOR_NAME="test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    env.update(extra)
    return env


def _git(repo: Path, *argv: str) -> str:
    p = subprocess.run(
        ["git", *argv],
        cwd=repo,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0, f"git {' '.join(argv)} failed: {p.stderr}"
    return p.stdout.strip()


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    """A throwaway checkout shaped like a CI job: one commit of history, and a base sha."""
    return _fixture(tmp_path)


def _fixture(root: Path) -> tuple[Path, str]:
    """The one fixture, shared by the tests and by the registered Optimus measure.

    bin/idp-tests-for and bin/idp-ci-base are copied in because the selector computes its root
    from its own location -- so the copy under test is the copy that runs.
    """
    r = root / "repo"
    (r / "bin").mkdir(parents=True)
    for script in (TOOL, RESOLVER):
        shutil.copyfile(script, r / "bin" / script.name)
        (r / "bin" / script.name).chmod(0o755)
    _write(r, "tests/slow-files.txt", "# nothing in this fixture is slow\n")
    _write(r, "bin/thing.sh", "echo thing\n")
    _write(r, "bin/other.sh", "echo other\n")
    _write(r, "platform/other.yaml", "a: 1\n")
    _write(
        r,
        "tests/test_alpha.py",
        '"""a test that reads the file this branch changed"""\n\n\n'
        "def test_alpha():\n"
        '    assert "bin/thing.sh"\n',
    )
    _write(
        r,
        "tests/test_beta.py",
        '"""a test that reads a file this branch did not change"""\n\n\n'
        "def test_beta():\n"
        '    assert "bin/other.sh"\n',
    )
    _write(
        r,
        "tests/test_gamma.py",
        '"""a test that reads a file the JOB writes, not the commit"""\n\n\n'
        "def test_gamma():\n"
        '    assert "generated/report.json"\n',
    )
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=r, env=_env(), check=True)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "base")
    parent = _git(r, "rev-parse", "HEAD")
    _write(r, "bin/thing.sh", "echo thing changed\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "change thing")

    # What an earlier step in the same job writes into the tree after the commit. It is identical
    # on every commit, which is why grading it made the selection constant.
    _write(r, "generated/report.json", "{}\n")
    return r, parent


def _run(
    repo: Path, *argv: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo / "bin" / "idp-tests-for"), "--list", *argv],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _listed(p: subprocess.CompletedProcess[str]) -> set[str]:
    return {
        line.strip()
        for line in p.stdout.splitlines()
        if line.startswith("tests/") or line.startswith("sovereign/")
    }


ALL_CHEAP = {"tests/test_alpha.py", "tests/test_beta.py", "tests/test_gamma.py"}


def test_the_invocation_ci_uses_runs_every_cheap_file_when_origin_main_is_absent(
    repo: tuple[Path, str],
):
    """The measured failure, replayed: `--base origin/main` on a checkout that never fetched it.

    Before the fix this printed "nothing changed against origin/main" and exited 0 -- and in the
    real job the untouched assignment let the untracked artefacts in, which is how a candidate got
    a green on three files it never wrote.
    """
    r, _ = repo
    p = _run(r, "--base", "origin/main", env=_env(CI="1", TESTS_FOR_ALL="0"))
    assert p.returncode == 0, p.stderr
    assert "BLIND" in p.stderr, p.stderr
    assert _listed(p) == ALL_CHEAP, p.stdout


def test_the_base_is_named_by_the_one_resolver_not_a_fifth_copy_of_the_rule(
    repo: tuple[Path, str],
):
    """With no --base, CI asks bin/idp-ci-base. A Greenlane candidate is a fresh queue ref whose
    before is forty zeros, so the resolver answers origin/main -- still absent here, so BLIND."""
    r, _ = repo
    p = _run(
        r,
        env=_env(
            CI="1",
            TESTS_FOR_ALL="0",
            ESTATE_CI_EVENT_NAME="push",
            ESTATE_CI_REF="refs/heads/queue/b6501",
            ESTATE_CI_BEFORE=ZEROS,
        ),
    )
    assert p.returncode == 0, p.stderr
    assert "BLIND" in p.stderr, p.stderr
    assert _listed(p) == ALL_CHEAP, p.stdout


def test_a_base_that_resolves_still_selects_only_the_changed_files_test(
    repo: tuple[Path, str],
):
    """The known-GOOD fixture, and the guard against a fix that just runs everything: a sighted
    base selects the one test that reads the changed file, and NOT the untracked artefact's."""
    r, parent = repo
    p = _run(r, "--base", parent, env=_env(CI="1", TESTS_FOR_ALL="0"))
    assert p.returncode == 0, p.stderr
    assert "BLIND" not in p.stderr, p.stderr
    assert _listed(p) == {"tests/test_alpha.py"}, p.stdout


def test_the_files_the_job_wrote_never_enter_a_ci_change_set(repo: tuple[Path, str]):
    """idp#8788's second defect, isolated: generated/report.json is untracked, a test names it, and
    it is still not part of what the commit changed."""
    r, parent = repo
    p = _run(r, "--base", parent, env=_env(CI="1", TESTS_FOR_ALL="0"))
    assert "tests/test_gamma.py" not in _listed(p), p.stdout


def test_the_laptop_author_still_sees_their_own_uncommitted_change(
    repo: tuple[Path, str],
):
    """Outside CI the author's working tree IS their change: an unstaged edit is still graded."""
    r, parent = repo
    _write(r, "bin/other.sh", "echo other edited\n")
    p = _run(r, "--base", parent, env=_env())
    assert p.returncode == 0, p.stderr
    assert "tests/test_beta.py" in _listed(p), p.stdout


def test_blind_with_no_cheap_set_refuses_instead_of_reporting_a_green(
    repo: tuple[Path, str],
):
    """A gate that cannot judge must not pass (AGENTS.md section 9, R1). Without slow-files.txt the
    cheap set cannot be named, so the answer is a loud exit 3, never "nothing to run"."""
    r, _ = repo
    (r / "tests" / "slow-files.txt").unlink()
    p = _run(r, "--base", "origin/main", env=_env(CI="1", TESTS_FOR_ALL="0"))
    assert p.returncode == 3, (p.returncode, p.stdout, p.stderr)
    assert "refusing to report a green" in p.stderr, p.stderr


def test_a_file_that_eats_its_bound_is_named_instead_of_being_cancelled_anonymously(
    repo: tuple[Path, str],
):
    """MEASURED 2026-11-28, twice: lane runs 46153235459 and 46160054003 ran this same 34-file
    selection, printed progress to 17%, and were each cancelled by the job's own timeout-minutes.
    Twenty minutes went by inside one selected file and the cancellation step never ran, so the
    author was told nothing at all -- no test, no node id, no annotation. `-vv` cannot reach a thin
    client (log text needs auth); a check-run annotation can. This is that bound, and the name.
    """
    r, _ = repo
    _write(
        r,
        "tests/test_stuck.py",
        '"""a test that reads the file this branch changed, and never returns"""\n\n\n'
        "import time\n\n\n"
        "def test_stuck():\n"
        '    assert "bin/thing.sh"\n'
        "    time.sleep(20)\n",
    )
    # Committed, not left untracked: CI never has uncommitted work, and the cheap set is
    # `git ls-files`, so an uncommitted file is invisible to the very selection under test.
    _git(r, "add", "tests/test_stuck.py")
    _git(r, "commit", "-q", "-m", "a new cheap test that never returns")
    p = subprocess.run(
        [str(r / "bin" / "idp-tests-for"), "--base", "origin/main"],
        cwd=r,
        env=_env(CI="1", TESTS_FOR_ALL="0", TESTS_FOR_FILE_BUDGET="2"),
        capture_output=True,
        text=True,
        check=False,
    )
    out = p.stdout + p.stderr
    assert p.returncode != 0, out
    assert "title=pytest-timeout" in out, out
    assert "tests/test_stuck.py" in out, out


def _blind_base_unserved_files() -> int:
    """The registered Optimus reading: cheap files a BLIND base leaves unselected.

    MEASURED 2026-11-28 on this fixture, both sides: main's selector (blob 64ba03c8) answers 2 --
    it runs tests/test_gamma.py, the test that reads the artefact the JOB wrote, and never the two
    tests the commit changed -- while this fix answers 0. The reading is taken by running the same
    instrument, not by reading a promise in the diff.
    """
    with tempfile.TemporaryDirectory() as d:
        r, _ = _fixture(Path(d))
        p = _run(r, "--base", "origin/main", env=_env(CI="1", TESTS_FOR_ALL="0"))
        if p.returncode != 0:
            return len(ALL_CHEAP)  # a refusal names no files at all: nothing is served
        return len(ALL_CHEAP - _listed(p))


if __name__ == "__main__":
    # `python3 tests/<this file> --optimus` prints the one line Greenlane reads from main
    # (catalog/optimus-metrics.json). It runs the selector, never pytest, so a thin client can
    # measure it. The same mode is how every registered measure is shaped.
    if "--optimus" in sys.argv[1:]:
        print(f"optimus.tests_for.blind_base_unserved_files={_blind_base_unserved_files()}")
        raise SystemExit(0)
    raise SystemExit("usage: --optimus (this file is a pytest module and a registered measure)")
