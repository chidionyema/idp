"""#8647: PNG, HTML, CSS and SVG are web assets, and the pre-push gate must parse them as such.

Pushing feat/chrome-extension-integration (2026-11-27) was refused on
chrome-extension/src/icons/icon128.png with "readable as neither shell nor Python": the gate
had no case for web assets, so a browser extension (icons, popup.html, quarantine.css) could
never be pushed. Same class as the plist (#7714) and TOML refusals.

The hook is founder-sealed, so the per-type parsers moved out of it into bin/idp-asset-check,
which the hook runs from origin/main's bytes: a new type is an ordinary lane, not a seal. Each
type gets a check that can fail (PNG signature plus IHDR CRC, JPEG/GIF/WEBP/ICO headers, strict
UTF-8 with no NUL for HTML and CSS, well-formed XML for SVG). With no judge on main, the hook
still refuses: the unknown bucket is unchanged.

    python3 tests/test_prepush_web_asset_classification.py --optimus
        -> optimus.prepush.web_asset_cases_failing=<n>   (main: 9, the fix: 0)
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-push"
JUDGE = ROOT / "bin" / "idp-asset-check"

STUB = "#!/bin/sh\nexit 0\n"


def png(width: int = 1, height: int = 1, corrupt_crc: bool = False) -> bytes:
    def chunk(kind: bytes, data: bytes, bad: bool = False) -> bytes:
        crc = zlib.crc32(kind + data) ^ (1 if bad else 0)
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"\x00" + b"\x00\x00\x00\x00" * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr, corrupt_crc)
        + chunk(b"IDAT", zlib.compress(raw * height))
        + chunk(b"IEND", b"")
    )


def git(cwd: Path, *a: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *a], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


def make_clone(tmp_path, judge: bool = True):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    git(work, "config", "user.email", "t@example.com")
    git(work, "config", "user.name", "t")
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
    if judge:
        shutil.copy(JUDGE, work / "bin" / "idp-asset-check")
        git(work, "add", "bin/idp-asset-check")
    git(work, "commit", "-q", "-m", "base")
    git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "fetch", "-q", "origin")
    return work


@pytest.fixture
def clone(tmp_path):
    return make_clone(tmp_path)


def commit(work: Path, name: str, content: bytes) -> None:
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    git(work, "add", name)
    git(work, "commit", "-q", "-m", name)


def push(work: Path, branch: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("IDP_CI_")}
    return git(work, "push", "origin", f"HEAD:{branch}", env=env, check=False)


@pytest.mark.parametrize(
    "name,content",
    [
        ("ext/icons/icon16.png", png(16, 16)),
        ("ext/popup.html", b"<!doctype html><html><body><p>ok</p></body></html>\n"),
        ("ext/quarantine.css", b".q { outline: 2px solid red; }\n"),
        (
            "ext/logo.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>\n',
        ),
    ],
)
def test_a_real_web_asset_is_accepted(clone, name, content):
    commit(clone, name, content)
    p = push(clone, "scratch/asset-ok")
    assert p.returncode == 0, p.stderr


@pytest.mark.parametrize(
    "name,content",
    [
        ("ext/icons/bad-crc.png", png(16, 16, corrupt_crc=True)),
        ("ext/icons/not-a.png", b"echo this is not an image\n"),
        ("ext/nul.html", b"<html>\x00</html>\n"),
        ("ext/latin1.css", b".q { content: '\xe9'; }\n"),
        ("ext/broken.svg", b"<svg><g></svg>\n"),
        ("ext/fake.jpg", b"echo not a jpeg\n"),
    ],
)
def test_a_file_that_only_borrows_the_extension_is_refused(clone, name, content):
    commit(clone, name, content)
    p = push(clone, "scratch/asset-bad")
    assert p.returncode != 0, p.stderr
    assert "is not a parseable web asset" in p.stderr, p.stderr


def test_with_no_judge_on_main_a_web_asset_is_still_refused(tmp_path):
    # Fail-closed: the judge is read from origin/main, never from the pushed branch, so a lane
    # cannot admit its own files by shipping a looser judge; with none on main, nothing changes.
    work = make_clone(tmp_path, judge=False)
    shutil.copy(JUDGE, work / "bin" / "idp-asset-check")
    commit(work, "ext/icons/icon16.png", png(16, 16))
    git(work, "add", "bin/idp-asset-check")
    git(work, "commit", "-q", "-m", "ship a judge in the branch")
    p = push(work, "scratch/no-judge")
    assert p.returncode != 0, p.stderr
    assert "readable as neither shell nor Python" in p.stderr, p.stderr


def test_a_file_no_parser_can_read_is_still_refused(clone):
    commit(clone, "payload.bin", b"\x00\x01\x02 not source code \xff\n")
    p = push(clone, "scratch/bin")
    assert p.returncode != 0, p.stderr
    assert "readable as neither shell nor Python" in p.stderr, p.stderr


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", __file__],
            capture_output=True,
            text=True,
            check=False,
        )
        m = re.search(r"(\d+) failed", r.stdout)
        failing = int(m.group(1)) if m else (0 if r.returncode == 0 else 1)
        print(f"optimus.prepush.web_asset_cases_failing={failing}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
