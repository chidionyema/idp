"""Incident, 2026-08-25 (idp#125): the first Backstage image build was red on
Trivy CRITICAL CVE-2026-59873 in three copies of node-tar 6.2.1: two under the
app's node_modules (cacache, node-gyp) and npm's own copy in the base image.

Rung 4, incident test. The rule, not the code: every `tar` the lockfile
resolves is a fixed version, the runtime stage removes npm, and bin/dockerfiles
discovers backstage/Dockerfile while skipping its .dockerignore twin.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED = (7, 5, 19)


def _version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def test_every_resolved_tar_is_at_or_past_the_fix():
    lock = (ROOT / "backstage" / "yarn.lock").read_text()
    versions = re.findall(r'^"tar@[^"]*":\n  version: ([0-9.]+)', lock, re.M)
    assert versions, "no tar entry found in yarn.lock"
    bad = [v for v in versions if _version(v) < FIXED]
    assert not bad, f"tar below {FIXED}: {bad}"
    resolutions = json.loads((ROOT / "backstage" / "package.json").read_text())["resolutions"]
    assert "tar" in resolutions, "resolutions.tar missing: the pin would drift on the next install"


def test_runtime_stage_removes_npm():
    text = (ROOT / "backstage" / "Dockerfile").read_text()
    runtime = text.split("# --- stage 4")[1]
    assert "rm -rf /usr/local/lib/node_modules/npm" in runtime


def test_dockerfiles_discovers_backstage_and_skips_its_dockerignore():
    out = subprocess.run([str(ROOT / "bin" / "dockerfiles"), "--json"], check=True,
                         capture_output=True, text=True, cwd=ROOT).stdout
    files = {d["dockerfile"] for d in json.loads(out)}
    assert "backstage/Dockerfile" in files
    assert not any(f.endswith(".dockerignore") for f in files), files
