"""#7714: a *.plist is a launchd job, and the pre-push gate must parse it as one.

The gate classifies every file in the pushed diff: shell by shebang, Python (py_compile),
TypeScript, JavaScript, and everything else in an unknown bucket that accepts a file only
when bash -n or py_compile can read it. A plist is XML, so it was refused:
"readable as neither shell nor Python" (measured 2026-11-05 pushing
lane/macos-estate-resources with infra/macos/tools/disk-sentinel/launchd/*.plist).

That refusal made the estate's own declaration layer unpushable: `bin/idp-inventory --plane
mac` marks a loaded job MANAGED only when a file named <label>.plist is tracked in a
repository, and every tracked launchd definition in this repo is a plist.

The repair gives plists a real parser -- plistlib -- and requires the two keys a launchd job
cannot work without. A malformed plist is refused, naming the plist. The unknown bucket is
unchanged: a file no parser can read is still refused.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-push"

STUB = """#!/bin/sh
exit 0
"""

VALID_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>dev.example.monitor</string>
<key>ProgramArguments</key><array><string>/bin/bash</string><string>${HOME}/.local/share/example/run.sh</string></array>
</dict></plist>
"""

NO_LABEL_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict><key>ProgramArguments</key><array><string>/bin/true</string></array></dict></plist>
"""

BROKEN_PLIST = """<plist version="1.0"><dict><key>Label</key><string>x</string>
"""

BINARY = "\x00\x01\x02 not source code \xff\n"


def git(cwd: Path, *a: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


@pytest.fixture
def clone(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
    # The hook is copied OUTSIDE the work tree so the clone's own diff never contains it:
    # the hook carries emoji, and the gate refuses non-ASCII bytes added to a pushed file.
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    shutil.copy(HOOK, hooks / "pre-push")
    git(work, "config", "core.hooksPath", str(hooks))
    (work / "bin").mkdir()
    ci = work / "bin" / "idp-ci"
    ci.write_text(STUB)
    ci.chmod(0o755)
    (work / "a.txt").write_text("a\n")
    git(work, "add", "a.txt", "bin/idp-ci")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    return work


def commit(work: Path, name: str, content: str) -> None:
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    git(work, "add", name)
    git(work, "commit", "-q", "-m", name)


def push(work: Path, branch: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IDP_CI_")}
    return git(work, "push", "origin", f"HEAD:{branch}", env=env, check=False)


def test_a_valid_launchd_plist_is_accepted(clone):
    commit(clone, "launchd/dev.example.monitor.plist", VALID_PLIST)
    p = push(clone, "scratch/plist-ok")
    assert p.returncode == 0, p.stderr


def test_a_templated_plist_is_accepted(clone):
    # The estate's own launchd/*.plist.tmpl files carry ${HOME} and ${IDP} inside string
    # values. A placeholder is a string to plistlib, so the template still parses -- and a
    # template the gate cannot read is the same refusal one file over.
    commit(clone, "launchd/dev.example.tick.plist.tmpl", VALID_PLIST)
    p = push(clone, "scratch/plist-tmpl")
    assert p.returncode == 0, p.stderr


def test_a_plist_with_no_label_is_refused(clone):
    commit(clone, "launchd/no-label.plist", NO_LABEL_PLIST)
    p = push(clone, "scratch/plist-nolabel")
    assert p.returncode != 0, p.stderr
    assert "is not a parseable launchd plist" in p.stderr, p.stderr


def test_a_malformed_plist_is_refused(clone):
    commit(clone, "launchd/broken.plist", BROKEN_PLIST)
    p = push(clone, "scratch/plist-broken")
    assert p.returncode != 0, p.stderr
    assert "is not a parseable launchd plist" in p.stderr, p.stderr


def test_a_file_no_parser_can_read_is_still_refused(clone):
    commit(clone, "payload.bin", BINARY)
    p = push(clone, "scratch/bin")
    assert p.returncode != 0, p.stderr
    assert "readable as neither shell nor Python" in p.stderr, p.stderr
