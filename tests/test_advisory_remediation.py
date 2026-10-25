"""idp#7080: bin/advisory-remediation turns a published advisory into a lane with the bumped pin.

The audits are stubs on PATH: the pip-audit stub reads the pin out of the requirements file it
was handed and reports it as vulnerable with a fix version; the npm stub reports one vulnerable
package and, asked to fix, rewrites the lock the way npm would. The remote is a local bare
repository, so the lane is pushed for real and can be inspected on it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "advisory-remediation"
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
                                       "vulns": [{"id": "CVE-2026-1111",
                                                  "fix_versions": ["9.9.9"]}]}]}))
else:
    print("demo 1.0.0 CVE-2026-1111 9.9.9")
sys.exit(1)
"""

NPM = r"""#!/usr/bin/env python3
import json, os, sys

if "fix" in sys.argv[1:]:
    path = os.path.join(os.getcwd(), "package-lock.json")
    doc = json.load(open(path))
    doc["packages"]["node_modules/zod"]["version"] = "4.6.6"
    json.dump(doc, open(path, "w"), indent=2)
    print("fixed 1 package")
    sys.exit(0)
if "--json" in sys.argv[1:]:
    print(json.dumps({"vulnerabilities": {"zod": {
        "severity": "high",
        "via": [{"severity": "high", "url": "https://github.com/advisories/GHSA-mrhx-c7xc-m3w5"}],
        "fixAvailable": {"name": "zod", "version": "4.6.6", "isSemVerMajor": False}}}}))
else:
    print("zod  high severity  https://github.com/advisories/GHSA-mrhx-c7xc-m3w5")
sys.exit(1)
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


def _repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    src = tmp_path / "src"
    src.mkdir()
    subprocess.run([*GIT, "init", "-q", "-b", "main"], cwd=src, check=True)
    (src / "requirements.txt").write_text("demo==1.0.0\n")
    (src / "package-lock.json").write_text(_lock("3.23.8"))
    (src / "README.md").write_text("demo\n")
    subprocess.run([*GIT, "add", "-A"], cwd=src, check=True)
    subprocess.run([*GIT, "commit", "-qm", "base"], cwd=src, check=True)
    subprocess.run([*GIT, "remote", "add", "origin", str(remote)], cwd=src, check=True)
    subprocess.run([*GIT, "push", "-q", "-u", "origin", "main"], cwd=src, check=True)
    return src


def _run(tmp_path: Path, src: Path, *args: str) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, body in (("pip-audit", PIP_AUDIT), ("npm", NPM)):
        stub = bin_dir / name
        stub.write_text(body)
        stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=src,
        capture_output=True,
        text=True,
        env=env,
    )


def test_the_plan_is_printed_and_nothing_is_touched(tmp_path):
    src = _repo(tmp_path)
    before = subprocess.run(
        [*GIT, "status", "--porcelain"], cwd=src, capture_output=True, text=True
    )
    p = _run(tmp_path, src)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "demo 1.0.0 -> 9.9.9" in p.stdout, p.stdout
    assert "CVE-2026-1111" in p.stdout, p.stdout
    after = subprocess.run(
        [*GIT, "status", "--porcelain"], cwd=src, capture_output=True, text=True
    )
    assert before.stdout == after.stdout == "", after.stdout
    branches = subprocess.run(
        ["git", "branch", "--list", "lane/*"], cwd=src, capture_output=True, text=True
    )
    assert branches.stdout.strip() == "", branches.stdout


def test_a_lane_is_pushed_with_the_bumped_pin(tmp_path):
    src = _repo(tmp_path)
    p = _run(tmp_path, src, "--push")
    assert p.returncode == 0, p.stdout + p.stderr
    lanes = subprocess.run(
        ["git", "ls-remote", "--heads", "origin"],
        cwd=src,
        capture_output=True,
        text=True,
    ).stdout
    assert "lane/advisory-demo-cve-2026-1111" in lanes, lanes
    assert "lane/advisory-zod-ghsa-mrhx-c7xc-m3w5" in lanes, lanes

    py = subprocess.run(
        ["git", "show", "origin/lane/advisory-demo-cve-2026-1111:requirements.txt"],
        cwd=src,
        capture_output=True,
        text=True,
    ).stdout
    assert py.strip() == "demo==9.9.9", py

    npm = json.loads(
        subprocess.run(
            [
                "git",
                "show",
                "origin/lane/advisory-zod-ghsa-mrhx-c7xc-m3w5:package-lock.json",
            ],
            cwd=src,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert npm["packages"]["node_modules/zod"]["version"] == "4.6.6", npm


def test_a_lane_that_already_exists_is_not_opened_twice(tmp_path):
    src = _repo(tmp_path)
    assert _run(tmp_path, src, "--push").returncode == 0
    p = _run(tmp_path, src, "--push")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "it already exists" in p.stdout, p.stdout


def test_a_dirty_tree_is_refused(tmp_path):
    src = _repo(tmp_path)
    (src / "requirements.txt").write_text("demo==2.0.0\n")
    p = _run(tmp_path, src, "--push")
    assert p.returncode == 1, p.stdout + p.stderr
    assert "not clean" in p.stdout, p.stdout
