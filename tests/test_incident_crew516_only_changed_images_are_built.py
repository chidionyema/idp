"""crew#516: a one-line YAML edit built every image on both architectures.

`bin/dockerfiles --changed-since <ref>` keeps only the images whose context or
Dockerfile the diff reaches, and falls back to every image when the ref is
unknown or when the build machinery itself changed. build-multiarch.yml calls it
with the pull request's base."""
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "dockerfiles"
WORKFLOW = ROOT / ".github" / "workflows" / "build-multiarch.yml"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})


def _repo(tmp_path):
    repo = tmp_path / "estate"
    (repo / "bin").mkdir(parents=True)
    (repo / "bin" / "dockerfiles").write_bytes(SCRIPT.read_bytes())
    (repo / "bin" / "dockerfiles").chmod(0o755)
    for name in ("alpha", "beta"):
        (repo / name).mkdir()
        (repo / name / "Dockerfile").write_text("FROM scratch\n")
        (repo / name / "app.txt").write_text("v1\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    return repo


def _names(repo, *args):
    out = subprocess.run([str(repo / "bin" / "dockerfiles"), "--json", *args], check=True,
                         capture_output=True, text=True, cwd=repo).stdout
    return sorted(r["name"] for r in json.loads(out))


def test_only_the_touched_context_is_listed(tmp_path):
    repo = _repo(tmp_path)
    (repo / "beta" / "app.txt").write_text("v2\n")
    _git(repo, "commit", "-qam", "beta changes")
    assert _names(repo, "--changed-since", "HEAD~1") == ["beta"]
    assert _names(repo) == ["alpha", "beta"]


def test_unknown_ref_and_build_machinery_changes_build_everything(tmp_path):
    repo = _repo(tmp_path)
    assert _names(repo, "--changed-since", "0000000000000000000000000000000000000000") == ["alpha", "beta"]
    (repo / "bin" / "dockerfiles").write_text((repo / "bin" / "dockerfiles").read_text() + "# touched\n")
    _git(repo, "commit", "-qam", "script changes")
    assert _names(repo, "--changed-since", "HEAD~1") == ["alpha", "beta"]


def test_workflow_discovers_against_the_base():
    text = WORKFLOW.read_text()
    assert re.search(r"bin/dockerfiles --json --changed-since", text)
    assert re.search(r"fetch-depth:\s*0", text)
    assert "origin/${{ github.base_ref }}" in text and "${{ github.event.before }}" in text
