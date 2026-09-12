#!/usr/bin/env python3
"""idp-treewalk: enumerate the files of THIS repository, never a nested copy of it.

Incident 2026-09-10. `.gitignore` already recorded the class on 2026-08-29: sessions work in
linked worktrees of this same repository, and an untracked, unignored nested checkout makes every
root-level gate read a copy of itself, so a clean branch goes red for another session's
work-in-progress ("another session's work-in-progress refusing this session's push, and a red
that says nothing about either branch"). The remedy recorded then was the naming convention
`/.wt-*/`, and a convention is only as good as the naming: later checkouts were made as
`scratchpad/`, `idp/` and `wt-mum286-sessions/`, so the pattern missed them and the incident
repeated.

What the failures were (measured in the primary checkout, 2026-09-10). Each of these gates globbed
or walked from the repository root, reached a nested checkout's own fixtures -- deliberately-bad
`tests/fixtures/.../bad.yaml`, or a `Dockerfile` the nested copy's list does not build -- and
reported those bytes as a defect in the branch under test:

    idp-flux-subst-gate           6 shell expansions from a nested copy's own bad fixture
    idp-clickhouse-system-log-ttl nested manifests
    idp-crd-then-cr               a nested copy's clusters/ Kustomizations
    idp-priority-class-exists     nested workloads
    estate-zone-gate              129 zone literals, all in generated/ignored files
    port-gate                     probes in a nested copy's bin/
    multiarch-gate                15 findings, all 15 in nested checkouts
    bin/dockerfiles               187 of 199 rows from nested checkouts, which is why
                                  sovereign/tests/bdd's cp0b image-list step failed

git is the authority (the same reasoning as bin/idp-repo-root, LAW 46 -- no file names where the
checkout lives). A path git ignores is not part of this tree. This module is the one
implementation of that predicate, so nine gates cannot hold nine opinions of it.

Usage:
    from treewalk import walk_tree, glob_tree, is_this_tree

    for dirpath, dirnames, filenames in walk_tree(ROOT):   # dirnames is already pruned
        ...
    for path in glob_tree(ROOT, "clusters", "**", "*.yaml"):
        ...
    if is_this_tree(path):
        ...
"""

from __future__ import annotations

import functools
import glob
import os
import shutil
import subprocess

# S607: an absolute path, never a partial one. Resolved once at import; a machine without git on
# PATH gets None and every caller then fails closed rather than treating the tree as clean.
GIT = shutil.which("git")


@functools.lru_cache(maxsize=8)
def _ignored(root: str) -> frozenset[str] | None:
    """Every path git ignores under `root`, as repo-relative paths, in ONE git call.

    `git ls-files --others --ignored --exclude-standard --directory` prints the ignored
    directories themselves rather than every file beneath them, so the whole answer for a tree
    this size is one round trip.

    A per-directory `git check-ignore` is correct and unusably slow: it made
    bin/idp-priority-class-exists exceed 600 seconds on this repository. Measured after this
    change: 1683 directories walked in 1.9 seconds.

    Returns None when git cannot answer, and every caller then treats the tree as ungradable
    rather than as clean: a fail-closed FAIL, never a pass.
    """
    if GIT is None:
        return None
    try:
        # check=False on purpose: a non-zero exit from git here means "could not answer", which
        # this function reports as None so every caller fails closed rather than passing.
        p = subprocess.run(  # noqa: S603 -- fixed argv, no shell; the only variable is cwd, this checkout
            [
                GIT,
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "--directory",
                "--no-empty-directory",
                "-z",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    out = set()
    for entry in p.stdout.split("\0"):
        if entry:
            out.add(entry.rstrip("/"))
    return frozenset(out)


def _is_ignored(path: os.PathLike | str, root: str) -> bool:
    """True when `path` or any ancestor between it and `root` is gitignored."""
    target = os.path.abspath(path)
    if not (target == root or target.startswith(root + os.sep)):
        return False
    ign = _ignored(root)
    if ign is None:
        return False
    parts = os.path.relpath(target, root).split(os.sep)
    # Ask about the path and every ancestor: `catalog/` is not ignored while
    # `catalog/catalog-info.yaml` is, and `idp/` being ignored covers everything beneath it.
    for i in range(1, len(parts) + 1):
        if os.sep.join(parts[:i]) in ign:
            return True
    return False


def is_this_tree(
    path: os.PathLike | str, root: os.PathLike | str | None = None
) -> bool:
    """True when `path` belongs to this repository rather than a nested checkout of it.

    A path outside `root` is not a nested checkout of it -- a caller grading a fixture directory
    in /tmp must still be told yes -- and `root` itself is always this tree.
    """
    root = os.path.abspath(
        root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    target = os.path.abspath(path)
    if target == root:
        return True
    if not target.startswith(root + os.sep):
        return True
    if _ignored(root) is None:
        # git could not answer. Refuse to scan nothing silently; the caller's gate exits non-zero.
        return False
    return not _is_ignored(target, root)


def walk_tree(root: os.PathLike | str):
    """os.walk over THIS repository: ignored directories are pruned, never entered."""
    root = os.path.abspath(root)
    if _ignored(root) is None:
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if not _is_ignored(os.path.join(dirpath, d), root)
        )
        yield dirpath, dirnames, filenames


def glob_tree(root: os.PathLike | str, *parts: str, recursive: bool = True):
    """glob.glob over THIS repository, dropping any hit inside a nested checkout."""
    root = os.path.abspath(root)
    for f in glob.glob(os.path.join(root, *parts), recursive=recursive):
        if is_this_tree(f, root):
            yield f
