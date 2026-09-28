#!/usr/bin/env python3
"""Verify a patch is safe: apply to tmp copy, bash -n, shellcheck."""

import sys, json, subprocess, tempfile, shutil, os

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <file> <patch>", file=sys.stderr)
    sys.exit(1)

src_file = os.path.abspath(sys.argv[1])
patch_file = sys.argv[2]

# Copy to temp dir preserving relative path from repo root
# e.g. /Users/roseonyema/Documents/code/idp/bin/idp-ci → tmp/bin/idp-ci
workdir = tempfile.mkdtemp()
rel = os.path.relpath(src_file, os.path.expanduser("~/Documents/code/idp"))
if rel.startswith("../"):
    # Not under idp/, just use basename
    target = os.path.join(workdir, os.path.basename(src_file))
else:
    target = os.path.join(workdir, rel)
os.makedirs(os.path.dirname(target), exist_ok=True)
shutil.copy2(src_file, target)

# Apply patch
r = subprocess.run(
    ["patch", "-p1", "--dry-run"],
    stdin=open(patch_file),
    cwd=workdir,
    capture_output=True,
    text=True,
)
if r.returncode != 0:
    print(f"patch FAILED:\n{r.stderr}", file=sys.stderr)
    shutil.rmtree(workdir)
    sys.exit(1)

r = subprocess.run(
    ["patch", "-p1"],
    stdin=open(patch_file),
    cwd=workdir,
    capture_output=True,
    text=True,
)
if r.returncode != 0:
    print(f"patch apply FAILED:\n{r.stderr}", file=sys.stderr)
    shutil.rmtree(workdir)
    sys.exit(1)
print("patch applied OK")

# bash -n
r = subprocess.run(["bash", "-n", target], capture_output=True, text=True)
if r.returncode != 0:
    print(f"bash -n FAILED:\n{r.stderr}", file=sys.stderr)
    shutil.rmtree(workdir)
    sys.exit(1)
print("bash -n PASS")

# shellcheck
r = subprocess.run(["shellcheck", "-f", "json", target], capture_output=True, text=True)
try:
    errors = json.loads(r.stdout) if r.stdout else []
except json.JSONDecodeError:
    errors = []

real_errors = [e for e in errors if e.get("level") != "info"]
if real_errors:
    for e in real_errors:
        print(
            f"shellcheck line {e['line']}: {e['code']} — {e['message']}",
            file=sys.stderr,
        )
    shutil.rmtree(workdir)
    sys.exit(1)

print("ALL PASS")
shutil.rmtree(workdir)
