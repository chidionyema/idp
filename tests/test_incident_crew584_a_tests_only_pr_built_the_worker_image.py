"""crew#584 CP-G: a tests-only pull request built the sovereign-worker image on both architectures.

`bin/dockerfiles` treated a Dockerfile whose context is the repo root (`.`) as
touched by every diff. sovereign-worker.Dockerfile copies six named paths, so a
diff outside them (tests/, docs/, .github/) reaches no image at all. touched()
now derives each image's source set from its COPY/ADD lines; a Dockerfile that
copies nothing still falls back to its whole context."""

import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "dockerfiles"


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        },
    )


def _repo(tmp_path):
    repo = tmp_path / "estate"
    for d in (
        "bin",
        "tests",
        "sovereign",
        "platform",
        "docs",
        "site/packages",
        "site/plugins",
    ):
        (repo / d).mkdir(parents=True)
    (repo / "bin" / "dockerfiles").write_bytes(SCRIPT.read_bytes())
    (repo / "bin" / "dockerfiles").chmod(0o755)
    (repo / "worker.Dockerfile").write_text(
        "FROM scratch\nCOPY sovereign/requirements.txt /app/sovereign/\nCOPY ./sovereign /app/sovereign\n"
        "COPY --from=deps /x /y\nCOPY bin platform /app/\n"
    )
    (repo / "site" / "Dockerfile").write_text(
        "FROM scratch\nCOPY --chown=node:node packages packages\nCOPY app-config*.yaml ./\n"
    )
    for f in (
        "tests/test_x.py",
        "sovereign/requirements.txt",
        "sovereign/main.py",
        "platform/a.yaml",
        "docs/a.md",
        "site/packages/a.ts",
        "site/plugins/b.ts",
        "site/app-config.yaml",
        "site/README.md",
    ):
        (repo / f).write_text("v1\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    return repo


def _names(repo, *args):
    out = subprocess.run(
        [str(repo / "bin" / "dockerfiles"), "--json", *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo,
    ).stdout
    return sorted(r["name"] for r in json.loads(out))


def _change(repo, *files):
    for f in files:
        (repo / f).write_text("v2\n")
    _git(repo, "commit", "-qam", "change " + " ".join(files))


def test_a_diff_outside_every_copy_source_builds_no_image(tmp_path):
    repo = _repo(tmp_path)
    _change(repo, "tests/test_x.py", "docs/a.md", "site/README.md")
    assert _names(repo, "--changed-since", "HEAD~1") == []


def test_a_root_context_image_is_built_only_when_a_copied_path_changes(tmp_path):
    repo = _repo(tmp_path)
    _change(repo, "sovereign/main.py")
    assert _names(repo, "--changed-since", "HEAD~1") == ["worker"]
    _change(repo, "platform/a.yaml")
    assert _names(repo, "--changed-since", "HEAD~1") == ["worker"]


def test_copy_flags_globs_and_stage_copies_are_read_correctly(tmp_path):
    repo = _repo(tmp_path)
    _change(repo, "site/packages/a.ts")
    assert _names(repo, "--changed-since", "HEAD~1") == ["site"]
    _change(repo, "site/app-config.yaml")
    assert _names(repo, "--changed-since", "HEAD~1") == ["site"]
    _change(repo, "site/plugins/b.ts")
    assert _names(repo, "--changed-since", "HEAD~1") == []


def test_the_dockerfile_itself_still_counts(tmp_path):
    repo = _repo(tmp_path)
    (repo / "worker.Dockerfile").write_text(
        (repo / "worker.Dockerfile").read_text() + "# bump\n"
    )
    _git(repo, "commit", "-qam", "dockerfile")
    assert _names(repo, "--changed-since", "HEAD~1") == ["worker"]
