"""bin/lane-preflight judges a lane by Greenlane's pre-CI rules before it is pushed.

Nothing is stubbed that decides a verdict: a real bare origin and clone, the real
bin/language-gate, the real pinned ruff, and git's own merge machinery. The pin Greenlane trusts
is read from greenlane/ferrari.py on origin/main, so the fixture writes that file with the
version of the ruff this machine has -- and one case writes a pin no machine has, to prove an
unjudgeable rule refuses instead of passing.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101, S603, S607
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFLIGHT = ROOT / "bin" / "lane-preflight"
HOOK = ROOT / ".githooks" / "pre-push"
FORMATTED = "def add(a, b):\n    return a + b\n"
UNFORMATTED = "def add( a,b ):\n  return a+b\n"
OPENS_ANY_URL = (
    "import urllib.request\n\n\ndef get(url):\n    return urllib.request.urlopen(url)\n"
)
OPENS_ANY_URL_JUSTIFIED = (
    "import urllib.request\n\n\ndef get(url):\n"
    "    return urllib.request.urlopen(url)  # noqa: S310 -- https enforced by caller\n"
)


# The fixture repos live in tmp and never reach a remote: they must not inherit this machine's
# global git config (its estate commit hooks guard real work, not a throwaway fixture).
ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.test",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.test",
}


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _ruff_version() -> str:
    ruff = shutil.which("ruff")
    assert ruff, "ruff is not installed: this proof never skips the formatter"
    match = re.search(
        r"ruff (\d+\.\d+\.\d+)",
        subprocess.run(
            [ruff, "--version"], capture_output=True, text=True, check=True
        ).stdout,
    )
    assert match
    return match.group(1)


def _metrics(names: list[str], unit: str = "bool") -> str:
    rows = [{"name": n, "unit": unit} for n in names]
    return json.dumps({"version": 1, "metrics": rows}, indent=2) + "\n"


def _repo(tmp_path: Path, pin: str | None = None) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(origin)], env=ENV, check=True
    )
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], env=ENV, check=True)
    _git(work, "checkout", "-q", "-b", "main")
    (work / "bin").mkdir()
    shutil.copy(ROOT / "bin" / "language-gate", work / "bin" / "language-gate")
    (work / "greenlane").mkdir()
    (work / "greenlane" / "ferrari.py").write_text(
        f'TRUSTED_RUFF_VERSION = "{pin or _ruff_version()}"\n'
    )
    (work / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    (work / "shared.txt").write_text("one\ntwo\nthree\n")
    # main's keyed-catalog rule and driver, the real files: the merge trial must use them.
    shutil.copy(ROOT / "bin" / "catalog-merge", work / "bin" / "catalog-merge")
    shutil.copy(ROOT / ".gitattributes", work / ".gitattributes")
    (work / "catalog").mkdir()
    (work / "catalog" / "optimus-metrics.json").write_text(_metrics(["seed.metric"]))
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "seed")
    _git(work, "push", "-q", "origin", "main")
    return work


def _lane(
    work: Path, files: dict[str, str], message: str = "work", claim: bool = True
) -> str:
    if claim:
        message += "\n\nClaim: chidionyema/idp#1\nAgent: t"
    _git(work, "checkout", "-q", "-B", "lane/x", "origin/main")
    for rel, text in files.items():
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", message)
    return _git(work, "rev-parse", "HEAD")


def _run(work: Path, sha: str = "HEAD"):
    return subprocess.run(
        ["bash", str(PREFLIGHT), sha],
        cwd=work,
        env=ENV,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _said(proc) -> str:
    return proc.stdout + proc.stderr


def test_a_clean_lane_passes_every_rule(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"docs/note.md": "hello\n"})
    proc = _run(work)
    assert proc.returncode == 0, _said(proc)
    assert (
        "passes language-gate, ruff format, the merge trial and the claim lines"
        in proc.stdout
    )


def test_a_new_python_file_without_the_trailer_is_refused_naming_the_file(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"bin/tool.py": FORMATTED})
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "bin/tool.py" in _said(proc)
    assert "Language-Exception" in _said(proc)


def test_the_same_file_with_the_trailer_passes(tmp_path):
    work = _repo(tmp_path)
    _lane(
        work,
        {"bin/tool.py": FORMATTED},
        "add tool\n\nLanguage-Exception: bin/tool.py -- needs the stdlib json parser\n",
    )
    proc = _run(work)
    assert proc.returncode == 0, _said(proc)


def test_a_colocated_test_file_is_judged_like_any_new_python(tmp_path):
    # The 2026-11-28 root cause: sovereign/engine/test_*.py is NOT under tests/, so it is not
    # exempt, and an API push skipped the hook that would have said so.
    work = _repo(tmp_path)
    _lane(work, {"sovereign/engine/test_thing.py": FORMATTED})
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "sovereign/engine/test_thing.py" in _said(proc)


def test_a_test_under_tests_is_exempt(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"tests/test_thing.py": FORMATTED})
    proc = _run(work)
    assert proc.returncode == 0, _said(proc)


def test_unformatted_python_is_refused_naming_the_file(tmp_path):
    work = _repo(tmp_path)
    _lane(
        work,
        {"tests/test_fmt.py": UNFORMATTED},
    )
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "ruff format" in _said(proc)
    assert "tests/test_fmt.py" in _said(proc)


def test_formatting_is_judged_on_the_commit_not_the_worktree(tmp_path):
    work = _repo(tmp_path)
    sha = _lane(work, {"tests/test_fmt.py": UNFORMATTED})
    (work / "tests" / "test_fmt.py").write_text(
        FORMATTED
    )  # dirty worktree, pushed bytes unchanged
    proc = _run(work, sha)
    assert proc.returncode == 1, _said(proc)


def test_a_security_finding_python_strict_refuses_is_named_before_the_push(tmp_path):
    # 2026-11-28, measured: lane 76dd398e passed ruff format and went red on fast-gate's py-strict
    # rung (S310 urlopen, S104, F401). Nothing here is stubbed: the real pinned ruff judges it.
    work = _repo(tmp_path)
    _lane(work, {"tests/net_probe.py": OPENS_ANY_URL})
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "python-strict" in _said(proc)
    assert "tests/net_probe.py" in _said(proc)
    assert "S310" in _said(proc)


def test_the_same_finding_with_a_justified_noqa_passes_python_strict(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"tests/net_probe.py": OPENS_ANY_URL_JUSTIFIED})
    proc = _run(work)
    assert proc.returncode == 0, _said(proc)
    assert "python-strict" in proc.stdout


def test_an_unused_import_is_a_python_strict_refusal(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"tests/unused.py": "import os\n"})
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "F401" in _said(proc)


def test_pytest_asserts_are_exempt_under_tests_like_the_estate_standard(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"tests/test_ok.py": "def test_ok():\n    assert 1 + 1 == 2\n"})
    proc = _run(work)
    assert proc.returncode == 0, _said(proc)


def test_a_file_already_off_standard_at_the_merge_base_is_a_note_not_a_refusal(
    tmp_path,
):
    # The estate hook's ratchet (LAW 38): only a regression is refused.
    work = _repo(tmp_path)
    (work / "tests").mkdir(exist_ok=True)
    (work / "tests" / "old.py").write_text(OPENS_ANY_URL)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "legacy file already off-standard")
    _git(work, "push", "-q", "origin", "main")
    _lane(work, {"tests/old.py": OPENS_ANY_URL + "\n\nX = 1\n"})
    proc = _run(work)
    assert proc.returncode == 0, _said(proc)
    assert "already off-standard" in _said(proc)


def test_a_lane_that_does_not_merge_onto_main_is_refused_with_the_conflict(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"shared.txt": "one\nLANE\nthree\n"})
    _git(work, "checkout", "-q", "main")
    (work / "shared.txt").write_text("one\nMAIN\nthree\n")
    _git(work, "commit", "-q", "-am", "main moves")
    _git(work, "push", "-q", "origin", "main")
    proc = _run(work, "lane/x")
    assert proc.returncode == 1, _said(proc)
    assert "does not merge onto origin/main" in _said(proc)
    assert "shared.txt" in _said(proc)


def test_two_lanes_that_each_append_a_catalog_entry_merge_by_key(tmp_path):
    # Every shipping lane appends one metric to the same list; git's line merge calls two such
    # lanes a conflict, main's driver calls them two entries (idp#8615). The preflight must agree
    # with the Greenlane, or it refuses lanes the Greenlane would land.
    work = _repo(tmp_path)
    _lane(work, {"catalog/optimus-metrics.json": _metrics(["seed.metric", "mine"])})
    _git(work, "checkout", "-q", "main")
    (work / "catalog" / "optimus-metrics.json").write_text(
        _metrics(["seed.metric", "theirs"])
    )
    _git(work, "commit", "-q", "-am", "another lane lands its metric")
    _git(work, "push", "-q", "origin", "main")
    proc = _run(work, "lane/x")
    assert proc.returncode == 0, _said(proc)


def test_two_lanes_that_disagree_on_one_catalog_key_still_conflict(tmp_path):
    work = _repo(tmp_path)
    _lane(work, {"catalog/optimus-metrics.json": _metrics(["seed.metric"], "ms")})
    _git(work, "checkout", "-q", "main")
    (work / "catalog" / "optimus-metrics.json").write_text(
        _metrics(["seed.metric"], "bytes")
    )
    _git(work, "commit", "-q", "-am", "main changes the same key")
    _git(work, "push", "-q", "origin", "main")
    proc = _run(work, "lane/x")
    assert proc.returncode == 1, _said(proc)
    assert "does not merge onto origin/main" in _said(proc)


def test_a_lane_cannot_supply_its_own_catalog_driver(tmp_path):
    # The driver is read from origin/main, never the lane: a lane that ships a driver which
    # swallows every conflict must not be judged by it.
    work = _repo(tmp_path)
    _lane(
        work,
        {
            "catalog/optimus-metrics.json": _metrics(["seed.metric"], "ms"),
            "bin/catalog-merge": "import sys\nsys.exit(0)\n",
        },
        "x\n\nLanguage-Exception: bin/catalog-merge -- test\n",
    )
    _git(work, "checkout", "-q", "main")
    (work / "catalog" / "optimus-metrics.json").write_text(
        _metrics(["seed.metric"], "bytes")
    )
    _git(work, "commit", "-q", "-am", "main changes the same key")
    _git(work, "push", "-q", "origin", "main")
    proc = _run(work, "lane/x")
    assert proc.returncode == 1, _said(proc)


def test_a_ruff_pin_nobody_has_is_blind_not_a_pass(tmp_path):
    work = _repo(tmp_path, pin="0.0.1")
    _lane(work, {"tests/test_fmt.py": FORMATTED})
    proc = _run(work)
    assert proc.returncode == 2, _said(proc)
    assert "BLIND" in _said(proc)
    assert "0.0.1" in _said(proc)


def test_judging_never_moves_the_pushers_checkout(tmp_path):
    work = _repo(tmp_path)
    sha = _lane(work, {"bin/tool.py": FORMATTED})
    _git(work, "checkout", "-q", "main")
    before = (_git(work, "rev-parse", "HEAD"), _git(work, "status", "--porcelain"))
    proc = _run(work, sha)
    assert proc.returncode == 1, _said(proc)
    assert (
        _git(work, "rev-parse", "HEAD"),
        _git(work, "status", "--porcelain"),
    ) == before
    assert _git(work, "rev-parse", "--abbrev-ref", "HEAD") == "main"


def test_the_hook_runs_the_preflight_before_the_disk_floor_exits():
    hook = HOOK.read_text()
    call = hook.index("if ! _preflight_guard; then")
    floor = hook.index("_free_mb=$(/bin/df -m")
    assert call < floor, (
        "the disk floor exits the hook first: the preflight never runs under it"
    )
    assert "bin/lane-preflight" in hook


def test_a_lane_with_no_claim_line_is_refused_with_the_line_to_add(tmp_path):
    """Measured 2026-11-28: lane 6fff504e was red at Greenlane for `no Claim: line`."""
    work = _repo(tmp_path)
    _lane(work, {"docs/note.md": "hello\n"}, claim=False)
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "Claim: owner/repo#N" in _said(proc)


def test_a_claim_without_an_agent_line_is_refused(tmp_path):
    work = _repo(tmp_path)
    _lane(
        work,
        {"docs/note.md": "hello\n"},
        message="work\n\nClaim: chidionyema/idp#1",
        claim=False,
    )
    proc = _run(work)
    assert proc.returncode == 1, _said(proc)
    assert "Agent: <name>" in _said(proc)
