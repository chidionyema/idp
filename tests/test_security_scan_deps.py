"""idp#7080: ESTATE_DEPS_BASE judges a dependency advisory against the ref the change is
measured from, so a pre-existing advisory stops holding a change that did not bring it.

The judgement compares pins, not advice. The same package at the same version on the base
and on HEAD is the same code, so it is the same advisory, and the diff did not bring it: it
is reported and deferred. A pin the change moved, or a package the base never pinned, is
this change's own and fails exactly as it did before.

Without the var -- or with a base that does not resolve -- every advisory gates, as before.
A base that does not resolve widens the judgement, it never narrows it.

`pip-audit` and `npm` are stubs on PATH: each reports the advisory it is told to report,
and the pip-audit stub reads the pin out of the requirements file it was handed, so the
finding it names is the pin the tree actually carries.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCAN = Path(__file__).resolve().parents[1] / "bin" / "estate-security-scan"
GIT = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]

PIP_AUDIT = r"""#!/usr/bin/env python3
import json, sys

args = sys.argv[1:]
name = version = None
for i, a in enumerate(args):
    if a == "-r" and i + 1 < len(args):
        for line in open(args[i + 1]):
            line = line.split("#", 1)[0].strip()
            if line.startswith("demo=="):
                name, version = "demo", line.split("==", 1)[1].strip()
if name is None:
    name, version = "demo", "1.0.0"
if "--format=json" in args:
    print(json.dumps({"dependencies": [{"name": name, "version": version,
                                       "vulns": [{"id": "CVE-2026-1111"}]}]}))
else:
    print("Name    Version    ID              Fix Versions")
    print("%s   %s   CVE-2026-1111   9.9.9" % (name, version))
sys.exit(1)
"""

NPM = r"""#!/usr/bin/env python3
import json, sys

if "--json" in sys.argv[1:]:
    print(json.dumps({"vulnerabilities": {"zod": {"via": [
        {"severity": "high", "url": "https://github.com/advisories/GHSA-mrhx-c7xc-m3w5"}]}}}))
else:
    print("# npm audit report")
    print("zod  high severity  https://github.com/advisories/GHSA-mrhx-c7xc-m3w5")
sys.exit(1)
"""

GITLEAKS = """#!/bin/sh
[ "$1" = version ] && { echo 8.30.1; exit 0; }
exit 0
"""

TRIVY = """#!/bin/sh
printf '{"Results":[]}\\n'
"""


def _lock(zod: str) -> str:
    return json.dumps(
        {
            "name": "demo",
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "demo", "dependencies": {"zod": zod}},
                "node_modules/zod": {"version": zod},
            },
        },
        indent=2,
    )


def _repo(tmp_path: Path, base_req: str, head_req: str, head_zod: str) -> Path:
    """A repository with a base commit and a head commit, one commit apart."""
    src = tmp_path / "src"
    src.mkdir()
    subprocess.run([*GIT, "init", "-q", "-b", "main"], cwd=src, check=True)
    (src / "requirements.txt").write_text(base_req)
    (src / "package-lock.json").write_text(_lock("3.23.8"))
    subprocess.run([*GIT, "add", "-A"], cwd=src, check=True)
    subprocess.run([*GIT, "commit", "-qm", "base"], cwd=src, check=True)
    subprocess.run([*GIT, "branch", "base"], cwd=src, check=True)
    (src / "requirements.txt").write_text(head_req)
    (src / "package-lock.json").write_text(_lock(head_zod))
    (src / "README.md").write_text(f"head {head_req} {head_zod}\n")
    subprocess.run([*GIT, "add", "-A"], cwd=src, check=True)
    subprocess.run([*GIT, "commit", "-qm", "head"], cwd=src, check=True)
    return src


def _scan(tmp_path: Path, src: Path, base: str | None) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in (
        ("pip-audit", PIP_AUDIT),
        ("npm", NPM),
        ("gitleaks", GITLEAKS),
        ("trivy", TRIVY),
    ):
        stub = bin_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    env.pop("ESTATE_DEPS_BASE", None)
    if base is not None:
        env["ESTATE_DEPS_BASE"] = base
    return subprocess.run(
        [str(SCAN), "--source", str(src)], capture_output=True, text=True, env=env
    )


def _lines(out: str, needle: str) -> list[str]:
    return [l for l in out.splitlines() if needle in l]


def test_a_pin_the_change_did_not_move_is_deferred(tmp_path):
    src = _repo(tmp_path, "demo==1.0.0\n", "demo==1.0.0\n", "3.23.8")
    p = _scan(tmp_path, src, "base")
    out = p.stdout
    assert p.returncode == 0, out
    deps = _lines(out, " deps ")
    assert any("deferred" in l for l in deps), deps
    assert any("CVE-2026-1111" in l for l in out.splitlines()), out
    assert not _lines(out, "FAIL"), out
    npm = _lines(out, " npm ")
    assert any("deferred" in l for l in npm), npm
    assert any("GHSA-mrhx-c7xc-m3w5" in l for l in out.splitlines()), out


def test_a_pin_the_change_moved_onto_fails(tmp_path):
    src = _repo(tmp_path, "demo==1.0.0\n", "demo==2.0.0\n", "3.23.8")
    p = _scan(tmp_path, src, "base")
    out = p.stdout
    assert p.returncode == 1, out
    assert _lines(out, "FAIL  deps"), out
    assert any("not pre-existing on base" in l for l in out.splitlines()), out


def test_a_package_the_base_never_pinned_fails(tmp_path):
    src = _repo(tmp_path, "other==1.0.0\n", "demo==1.0.0\n", "3.23.8")
    p = _scan(tmp_path, src, "base")
    out = p.stdout
    assert p.returncode == 1, out
    assert _lines(out, "FAIL  deps"), out


def test_a_lock_pin_the_change_moved_fails(tmp_path):
    src = _repo(tmp_path, "demo==1.0.0\n", "demo==1.0.0\n", "4.6.6")
    p = _scan(tmp_path, src, "base")
    out = p.stdout
    assert p.returncode == 1, out
    assert _lines(out, "FAIL  npm"), out
    assert any("not pre-existing on base" in l for l in out.splitlines()), out


def test_without_a_base_every_advisory_gates(tmp_path):
    src = _repo(tmp_path, "demo==1.0.0\n", "demo==1.0.0\n", "3.23.8")
    p = _scan(tmp_path, src, None)
    out = p.stdout
    assert p.returncode == 1, out
    assert _lines(out, "FAIL  deps"), out
    assert _lines(out, "FAIL  npm"), out


def test_a_base_that_does_not_resolve_widens_to_every_advisory_gating(tmp_path):
    src = _repo(tmp_path, "demo==1.0.0\n", "demo==1.0.0\n", "3.23.8")
    p = _scan(tmp_path, src, "origin/does-not-exist")
    out = p.stdout
    assert p.returncode == 1, out
    assert any("does not resolve" in l for l in out.splitlines()), out
    assert _lines(out, "FAIL  deps"), out
