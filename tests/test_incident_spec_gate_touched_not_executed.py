"""Incident test (rung 4), crew#297, 2026-08-26: bin/spec-gate passed any PR that touched a
*.feature file, and 63 of 79 idp feature files were named by no test. Both ways in one run: a code
change with a feature a test names is ok; a code change whose only spec is a new feature nobody
names is FAIL; a modified unbound feature does not count; the unbound residual prints every run."""
import subprocess
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "bin" / "spec-gate"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def _commit(repo: Path, files: dict[str, str], msg: str) -> None:
    for name, body in files.items():
        p = repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(body)
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", msg)


def _gate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(GATE), "main"], cwd=repo, capture_output=True, text=True)


def _repo(tmp: Path) -> Path:
    repo = tmp / "r"; repo.mkdir(); _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {"app.py": "x=1\n", "features/old.feature": "Feature: old\n", "features/bound.feature": "Feature: b\n",
                   "tests/test_bound.py": 'scenarios("features/bound.feature")\n'}, "base")
    _git(repo, "checkout", "-q", "-b", "pr")
    return repo


def test_incident_touched_feature_is_not_an_executed_one(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {"app.py": "x=2\n", "features/bound.feature": "Feature: b2\n"}, "bound")
    ok = _gate(repo)
    assert ok.returncode == 0 and "ok    spec-gate 1 code file(s) changed with 1 spec" in ok.stdout, ok.stdout + ok.stderr
    assert "residual spec-gate 1 feature file(s) named by no test" in ok.stdout, ok.stdout

    _commit(repo, {"docs/prose/prose.feature": "Feature: prose, not a spec\n"}, "prose under docs")
    docs = _gate(repo)
    assert docs.returncode == 0 and "residual spec-gate 1 feature" in docs.stdout, docs.stdout

    _commit(repo, {"features/old.feature": "Feature: old, edited\n"}, "prose")
    still_ok = _gate(repo)
    assert still_ok.returncode == 0 and "do not count as executable spec" in still_ok.stdout and "features/old.feature" in still_ok.stdout, still_ok.stdout

    _commit(repo, {"features/new.feature": "Feature: nobody runs me\n"}, "new prose")
    fail = _gate(repo)
    assert fail.returncode == 1 and "FAIL  spec-gate new *.feature" in fail.stdout and "features/new.feature" in fail.stdout, fail.stdout


def test_code_change_with_only_an_unbound_feature_is_fail(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {"app.py": "x=3\n", "features/old.feature": "Feature: old, edited\n"}, "touched only")
    r = _gate(repo)
    assert r.returncode == 1 and "FAIL  spec-gate 1 code file(s) changed and no executable spec" in r.stdout, r.stdout
