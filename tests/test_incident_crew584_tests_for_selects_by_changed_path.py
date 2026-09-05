"""crew#584: bin/idp-tests-for selects the test files that name a changed path, and runs the sovereign/
files from sovereign/ (its pytest.ini owns bdd_features_base_dir) and the root files from the root.

Incident: the first hook dry run passed a mixed argument list to one pytest; pytest picked the root
pyproject.toml, sovereign/pytest.ini was ignored and all 24 sovereign bdd files failed on feature paths.
The runs below are against a throwaway git repo with a fake python that records cwd and argv; no network.
"""
import os
import pathlib
import subprocess

IDP = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = IDP / "bin" / "idp-tests-for"


def _git(repo, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(repo)}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True, capture_output=True, env=env).stdout


def _repo(tmp_path):
    repo = tmp_path / "idp"
    (repo / "bin").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "sovereign" / "tests" / "bdd").mkdir(parents=True)
    (repo / "platform").mkdir()
    (repo / "bin" / "idp-tests-for").write_text(SCRIPT.read_text())
    (repo / "bin" / "idp-tests-for").chmod(0o755)
    (repo / "platform" / "router.yaml").write_text("a: 1\n")
    (repo / "tests" / "test_router.py").write_text('def test_x():\n    assert "platform/router.yaml"\n')
    (repo / "tests" / "test_other.py").write_text("def test_y():\n    assert True\n")
    (repo / "sovereign" / "tests" / "bdd" / "test_policy.py").write_text("def test_z():\n    assert True\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "bin", "tests", "sovereign", "platform")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _edit(repo):
    (repo / "platform" / "router.yaml").write_text("a: 2\n")  # a YAML edit: no Python coverage, testmon's blind spot
    (repo / "sovereign" / "tests" / "bdd" / "test_policy.py").write_text("def test_z():\n    assert 1\n")


def test_nothing_changed_is_ok_and_runs_nothing(tmp_path):
    repo = _repo(tmp_path)
    out = subprocess.run([str(repo / "bin/idp-tests-for"), "--list", "--base", "HEAD"], text=True, capture_output=True)
    assert out.returncode == 0 and "nothing changed" in out.stdout


def test_yaml_edit_selects_the_test_naming_it_and_a_changed_test_selects_itself(tmp_path):
    repo = _repo(tmp_path)
    _edit(repo)
    out = subprocess.run([str(repo / "bin/idp-tests-for"), "--list", "--base", "HEAD"], text=True, capture_output=True)
    assert out.returncode == 0, out.stderr
    sel = [l for l in out.stdout.splitlines() if l.startswith(("tests/", "sovereign/"))]
    assert sel == ["sovereign/tests/bdd/test_policy.py", "tests/test_router.py"], out.stdout


def test_sovereign_files_run_from_sovereign_and_root_files_from_root(tmp_path):
    repo = _repo(tmp_path)
    _edit(repo)
    log = tmp_path / "calls.log"
    fake = tmp_path / "fakepy"
    fake.write_text('#!/bin/sh\necho "$PWD $*" >> "%s"\n' % log)
    fake.chmod(0o755)
    out = subprocess.run([str(repo / "bin/idp-tests-for"), "--base", "HEAD"], text=True, capture_output=True,
                         env={**os.environ, "IDP_PY": str(fake)})
    assert out.returncode == 0, out.stderr
    assert log.read_text().splitlines() == [
        f"{repo} -m pytest -q tests/test_router.py",
        f"{repo}/sovereign -m pytest -q tests/bdd/test_policy.py",
    ]
