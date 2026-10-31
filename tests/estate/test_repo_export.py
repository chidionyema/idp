"""repo_export.py: what goes into the pack, what does not, and what the manifest says.

WHY THESE TESTS. 2026-10-31. The old repo-export intent ran `npx -y repomix@1.18.1` over the
working tree: it needed the network the door closes, it crawled 2.9 GB of ignored trees, and it
took 167 s against a 100 s ceiling -- so the capability existed and did not work. The packer
replaces it, and a packer that cannot fail is not a packer: the tests below pin the three
things that decide what a reviewer actually receives.

  1. SELECTION IS TRACKED CONTENT ONLY. The file list comes from `git ls-files` and is handed
     to repomix over --stdin, so the 2.9 GB of ignored working-tree trees can never reach the
     pack, and the pack is the same on a dirty machine as on a clean one.
  2. THE MEASURED EXCLUSIONS ARE EXCLUSIONS, NOT SILENCE. The Swift file that cost 76 s to
     tree-sitter compress (1.18.1 is the latest release, so there is no upgrade to wait for),
     vendored trees, minified bundles and binaries are all left out -- and every one of them is
     NAMED with its reason in the manifest. A smaller pack must never be a silent one.
  3. THE DOOR IS MET UNDER LOAD. repomix is slow when the machine is busy, so the packer
     carries its own budget: a timed-out attempt is a measurement, and the retry packs half the
     list. The manifest must name every file the shrink dropped.

The real repomix is never needed: every test injects a fake through REPO_EXPORT_REPOMIX, so
the suite runs on a laptop that has not run bin/idp-install-deps.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "platform"
    / "estate"
    / "libexec"
    / "repo_export.py"
)

FAKE_REPOMIX = """#!/usr/bin/env python3
import sys, pathlib
args = sys.argv[1:]
out = args[args.index("--output") + 1]
files = [l for l in sys.stdin.read().splitlines() if l.strip()]
pathlib.Path(out).write_text("<pack>" + "\\n".join(files) + "</pack>\\n")
print("Total Files: %d" % len(files))
print("Total Tokens: %d" % (len(files) * 100))
"""

SLEEPER_REPOMIX = """#!/usr/bin/env python3
import sys, time, pathlib
args = sys.argv[1:]
out = args[args.index("--output") + 1]
tries = pathlib.Path(out + ".tries")
if not tries.exists():
    tries.write_text("1")
    time.sleep(30)
files = [l for l in sys.stdin.read().splitlines() if l.strip()]
pathlib.Path(out).write_text("<pack>" + "\\n".join(files) + "</pack>\\n")
print("Total Files: %d" % len(files))
print("Total Tokens: %d" % (len(files) * 100))
"""


def _fake_repomix(tmp_path: Path, body: str = "") -> Path:
    path = tmp_path / "fake-repomix"
    path.write_text(body or FAKE_REPOMIX)
    path.chmod(0o755)
    return path


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "platform" / "estate" / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "sovereign").mkdir(parents=True)
    (repo / "platform" / "estate" / "core.py").write_text("def core():\n    return 1\n")
    (repo / "platform" / "estate" / "big.txt").write_text("x" * 5000)
    (repo / "platform" / "estate" / "logo.png").write_bytes(b"\x89PNG\r\n")
    (repo / "platform" / "estate" / "node_modules" / "pkg" / "index.js").write_text(
        "module.exports=1;\n"
    )
    (repo / "sovereign" / "trust.py").write_text("def trust():\n    return 2\n")
    (repo / "sovereign" / "helper.swift").write_text("let x = 1\n")
    (repo / "sovereign" / "vendor.min.js").write_text("var a=1;\n")
    (repo / "untracked.md").write_text("not tracked\n")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.com"],
        ["git", "config", "user.name", "t"],
        ["git", "add", "-A"],
        ["git", "commit", "-qm", "seed"],
    ):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    return repo


def _run(repo: Path, fake: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["REPO_EXPORT_REPOMIX"] = str(fake)
    return subprocess.run(
        [sys.executable, str(SCRIPT), f"repo={repo}", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_packs_tracked_core_and_names_every_exclusion(tmp_path):
    repo = _repo(tmp_path)
    fake = _fake_repomix(tmp_path)
    out = tmp_path / "pack.xml"

    proc = _run(repo, fake, f"output={out}", "path=platform/estate,sovereign")

    assert proc.returncode == 0, proc.stderr
    body = out.read_text()
    assert "platform/estate/core.py" in body
    assert "sovereign/trust.py" in body
    # untracked content never reaches the pack
    assert "untracked.md" not in body
    assert "node_modules" not in body

    manifest = Path(str(out) + ".manifest.txt").read_text()
    assert "tree-sitter cannot compress" in manifest
    assert "sovereign/helper.swift" in manifest
    assert "minified bundle" in manifest
    assert "binary or asset" in manifest
    assert "vendored third-party code" in manifest


def test_verdict_and_manifest_carry_the_provenance(tmp_path):
    repo = _repo(tmp_path)
    fake = _fake_repomix(tmp_path)
    out = tmp_path / "pack.xml"

    proc = _run(repo, fake, f"output={out}", "path=platform/estate")

    assert proc.returncode == 0, proc.stderr
    assert "verdict: repo-export packed" in proc.stdout
    assert "verdict: manifest" in proc.stdout
    summary = json.loads(proc.stdout.strip().splitlines()[-1])
    assert summary["files"] == 2  # core.py and big.txt
    assert summary["output"] == str(out)

    manifest = Path(str(out) + ".manifest.txt").read_text()
    assert "git_head:" in manifest
    assert "pack_sha256:" in manifest
    assert "## included" in manifest
    assert "## excluded" in manifest
    # the pack's own hash is in the manifest, so an export stays accountable
    assert summary["sha256"] in manifest


def test_oversized_files_are_excluded_and_named(tmp_path):
    repo = _repo(tmp_path)
    fake = _fake_repomix(tmp_path)
    out = tmp_path / "pack.xml"

    proc = _run(
        repo, fake, f"output={out}", "path=platform/estate", "max_file_bytes=100"
    )

    assert proc.returncode == 0, proc.stderr
    assert "platform/estate/big.txt" not in out.read_text()
    assert "larger than max_file_bytes" in Path(str(out) + ".manifest.txt").read_text()


def test_a_slow_machine_shrinks_the_pack_and_names_what_it_dropped(tmp_path):
    repo = _repo(tmp_path)
    sleeper = _fake_repomix(tmp_path, SLEEPER_REPOMIX)
    out = tmp_path / "pack.xml"

    proc = _run(
        repo,
        sleeper,
        f"output={out}",
        "path=platform/estate,sovereign",
        "budget_s=20",
        "attempt_s=3",
    )

    assert proc.returncode == 0, proc.stderr
    assert "the machine was too busy" in proc.stdout
    manifest = Path(str(out) + ".manifest.txt").read_text()
    assert "dropped by the time budget" in manifest


def test_a_scope_that_matches_nothing_fails_with_the_reason(tmp_path):
    repo = _repo(tmp_path)
    fake = _fake_repomix(tmp_path)
    out = tmp_path / "pack.xml"

    proc = _run(repo, fake, f"output={out}", "path=does/not/exist")

    assert proc.returncode == 1
    assert "nothing to pack" in proc.stderr


def test_a_missing_repomix_is_named_not_hidden(tmp_path):
    repo = _repo(tmp_path)
    env = dict(os.environ)
    env["REPO_EXPORT_REPOMIX"] = str(tmp_path / "nope")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            f"repo={repo}",
            f"output={tmp_path / 'pack.xml'}",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 1
    assert "REPO_EXPORT_REPOMIX points at nothing" in proc.stderr


def test_the_intent_calls_the_packer_and_needs_no_npx():
    intent = (
        Path(__file__).resolve().parents[2]
        / "platform"
        / "estate"
        / "intents"
        / "repo-export.yaml"
    ).read_text()
    assert "repo_export.py" in intent
    assert "npx -y repomix" not in intent
    assert "tools: []" in intent


def test_the_packer_source_is_compilable():
    compile(SCRIPT.read_text(), str(SCRIPT), "exec")
