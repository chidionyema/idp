#!/usr/bin/env python3
"""Extract only still-needed, unchanged-base Meridian web deltas. No writes to Git.

Run in an existing authorised checkout with the reviewed objects fetched.
The stdout patch is not admission, signing, testing, or permission to deploy.
"""
import argparse
import re
import subprocess
import sys

BASE = "7b9e95520eb75b85b4b8b0e9a62c538d3c832bcd"
SOURCE = "f51343804d17e37c6ea47a51d34d52e83392b7b9"
SCOPE = (
    "web/app/investors/page.tsx",
    "web/app/merian.css",
    "web/app/products/chronos/page.tsx",
    "web/components/ChronosWalkthrough.tsx",
    "web/components/Nav.tsx",
)


class Refused(Exception):
    """The patch cannot be safely reconstructed from the supplied objects."""


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False,
    )
    if result.returncode:
        raise Refused(f"git {args[0]} failed ({result.returncode})")
    return result.stdout


def commit(repo, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Refused("use an exact 40-character commit SHA")
    if git(repo, "rev-parse", "--verify", sha + "^{commit}").decode().strip() != sha:
        raise Refused("object is not an exact commit")
    return sha


def entry(repo, sha, path):
    raw = git(repo, "ls-tree", "-z", sha, "--", path)
    if not raw:
        return None
    expected = re.fullmatch(rb"100644 blob ([0-9a-f]{40})\t([^\x00]+)\x00", raw)
    if expected is None or expected[2] != path.encode():
        raise Refused(f"non-regular or ambiguous tree entry: {path}")
    return expected[1]


def prepare(repo, base, source, target):
    base, source, target = (commit(repo, s) for s in (base, source, target))
    git(repo, "merge-base", "--is-ancestor", base, source)
    git(repo, "merge-base", "--is-ancestor", base, target)
    raw = git(repo, "diff", "--no-renames", "--name-only", "-z", base, source, "--")
    if set(raw.rstrip(b"\x00").split(b"\x00")) != {p.encode() for p in SCOPE}:
        raise Refused("reviewed source is not exactly the five-path public scope")
    pending = []
    for path in SCOPE:
        prior, proposed, current = (entry(repo, s, path) for s in (base, source, target))
        if proposed is None or prior == proposed:
            raise Refused(f"missing or unchanged candidate: {path}")
        if current == proposed:
            continue
        if current != prior:
            raise Refused(f"target has independent changes; reconcile, do not overwrite: {path}")
        pending.append(path)
    if not pending:
        return b"", ()
    patch = git(
        repo, "diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv",
        "--no-renames", "--no-color", base, source, "--", *pending,
    )
    if not patch:
        raise Refused("pending files without a patch")
    return patch, tuple(pending)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--target", required=True, help="exact admitted current main SHA")
    args = parser.parse_args()
    try:
        patch, pending = prepare(args.repo, BASE, SOURCE, args.target)
    except (Refused, OSError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"PATCH_PATHS={len(pending)}; source-only, no release authority", file=sys.stderr)
    sys.stdout.buffer.write(patch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
