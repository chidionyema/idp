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

Run it as a program for its own proof (LAW 45, bin/idp-script-compiles):

    bin/treewalk.py --self-test

which builds a throwaway git tree with an ignored directory and asserts the three answers
below, rather than printing ok.
"""

from __future__ import annotations

import functools
import glob
import os
import pathlib
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


def _nested_worktrees(root: str) -> frozenset[str] | None:
    """Every linked worktree of this repository that sits INSIDE `root`, as absolute paths.

    The fourth repeat of the incident this module exists for (2026-09-20). Sessions now check
    out their workspace at `.claude/worktrees/<agent>/`, and a linked worktree is NOT an
    untracked file: git registers it under `.git/worktrees/`, so it never appears in
    `git ls-files --others --ignored`, and `_ignored` has no entry to prune it by. Adding a
    `.gitignore` line for it therefore changes nothing -- measured, 2026-09-20: the pattern was
    added, `walk_tree` still descended into 999 directories of the copy, and `is_this_tree`
    still answered True. A gitignore line here is decoration, and LAW 28 names that.

    `git worktree list --porcelain` is the authority for the same reason git is the authority
    above: no naming convention, and no list a later session has to have read. A worktree of
    this repository at the conventional sibling path (`../idp-wt-*`) is already outside `root`
    and needs no special case; only a nested one is pruned.
    """
    if GIT is None:
        return None
    try:
        p = subprocess.run(  # noqa: S603 -- fixed argv, no shell; the only variable is cwd
            [GIT, "worktree", "list", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    nested = set()
    for line in p.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        # realpath, not abspath: git reports the canonical path, while `root` may be reached
        # through a symlink. Measured 2026-09-20 on macOS, where tempfile returns
        # /var/folders/... and git reports /private/var/folders/... -- abspath made the prefix
        # comparison miss, so this arm of the self-test failed for a reason that had nothing to
        # do with the predicate it exists to prove.
        path = os.path.realpath(line[len("worktree ") :])
        if path.startswith(root + os.sep):
            nested.add(path)
    return frozenset(nested)


def is_this_tree(
    path: os.PathLike | str, root: os.PathLike | str | None = None
) -> bool:
    """True when `path` belongs to this repository rather than a nested checkout of it.

    A path outside `root` is not a nested checkout of it -- a caller grading a fixture directory
    in /tmp must still be told yes -- and `root` itself is always this tree.
    """
    root = os.path.realpath(
        root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    target = os.path.realpath(path)
    if target == root:
        return True
    if not target.startswith(root + os.sep):
        return True
    if _ignored(root) is None:
        # git could not answer. Refuse to scan nothing silently; the caller's gate exits non-zero.
        return False
    nested = _nested_worktrees(root)
    if nested is None:
        return False
    if any(target == w or target.startswith(w + os.sep) for w in nested):
        return False
    return not _is_ignored(target, root)


def walk_tree(root: os.PathLike | str):
    """os.walk over THIS repository: ignored directories are pruned, never entered."""
    # realpath, so `root` and the paths `git worktree list` reports are compared in the same
    # form. abspath left the symlinked temp root (/var/folders/...) uncanonicalised while git
    # reported /private/var/folders/..., so the prune set never matched (measured 2026-09-20).
    root = os.path.realpath(root)
    if _ignored(root) is None:
        return
    nested = _nested_worktrees(root)
    if nested is None:
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # `.git` is pruned by name, not by gitignore: git never lists its own object store as
        # ignored, so `_is_ignored` answered "no" for it and every walker adopter descended
        # into the packed objects. Measured 2026-09-13 in the primary checkout: 34,523 of the
        # 37,862 files a `walk_tree` yielded were under `.git`, and bin/idp-rule-coverage --
        # which reads every file's bytes -- did not finish inside 50 seconds. This module's own
        # docstring records the number from 2026-09-10 (1683 directories in 1.9 seconds); that
        # was before the object store carried this many packs, and the walk has been paying for
        # it since, in every gate that adopted this walker. The nested-checkout arm is handled
        # by `_is_ignored` below; `.git` is the other thing a walk over a repository must never
        # enter, and it is named here once for all nine callers.
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d != ".git"
            and not _is_ignored(os.path.join(dirpath, d), root)
            and os.path.realpath(os.path.join(dirpath, d)) not in nested
        )
        yield dirpath, dirnames, filenames


def glob_tree(root: os.PathLike | str, *parts: str, recursive: bool = True):
    """glob.glob over THIS repository, dropping any hit inside a nested checkout."""
    root = os.path.abspath(root)
    for f in glob.glob(os.path.join(root, *parts), recursive=recursive):
        if ".git" in pathlib.PurePath(f).parts:
            continue
        if is_this_tree(f, root):
            yield f


def _self_test() -> int:
    """Prove this module RUNS and holds its two predicates, on a tree built here.

    LAW 45 (`bin/idp-script-compiles`): a script under bin/ that has never executed is not
    built. This module shipped 2026-09-10 carrying nine gates' worth of tree-walking logic
    with no way to prove it runs, and the pre-push gate refused the push that would have
    carried it for exactly that reason.

    The proof is not a print-and-exit-0. It builds a throwaway git repository with an
    ignored directory and an untracked file, and asserts the three answers this module
    exists to give: a plain file IS this tree, a gitignored path is NOT, and a path
    outside the root IS (the fixture case -- a caller grading /tmp must still be told yes).
    A self-test that only echoed its own name would be the decoration LAW 28 names.
    """
    import tempfile

    failures: list[str] = []

    def expect(condition: bool, what: str) -> None:
        if not condition:
            failures.append(what)

    # A tree with one tracked file and one gitignored directory containing a file.
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        (base / "kept").mkdir()
        (base / "kept" / "real.txt").write_text("tracked\n")
        (base / "nested").mkdir()
        (base / "nested" / "bad.yaml").write_text("a nested checkout's fixture\n")
        (base / ".gitignore").write_text("nested/\n")
        init = (
            subprocess.run(
                [GIT, "init", "-q"], cwd=tmp, capture_output=True, check=False
            )
            if GIT
            else None
        )
        if init is None or init.returncode != 0:
            # git is the authority; without it every caller fails closed, and this test
            # says so rather than reporting a green it did not measure.
            print(
                "SKIP treewalk --self-test: git is not available, callers fail closed"
            )
            return 0

        expect(
            is_this_tree(base / "kept" / "real.txt", base),
            "a tracked file must be this tree",
        )
        expect(
            not is_this_tree(base / "nested" / "bad.yaml", base),
            "an ignored path must NOT be this tree",
        )
        expect(
            is_this_tree(os.path.join(tempfile.gettempdir(), "some-fixture"), base),
            "a path outside the root must be this tree (fixtures in a temp dir)",
        )
        expect(is_this_tree(base, base), "the root itself must be this tree")

        # The walk must not enter the ignored directory, and must never enter .git.
        # walk_tree yields canonical paths (realpath), so the base is canonicalised to match.
        walked = [os.path.relpath(d, os.path.realpath(base)) for d, _, _ in walk_tree(base)]
        expect(
            "nested" not in walked,
            f"walk_tree entered an ignored directory: {sorted(walked)}",
        )
        expect(
            not any(
                part == ".git" for p in walked for part in pathlib.PurePath(p).parts
            ),
            f"walk_tree entered .git: {sorted(walked)}",
        )
        expect(
            "kept" in walked,
            f"walk_tree pruned the real directory too: {sorted(walked)}",
        )

        # A linked worktree INSIDE the tree. This is the 2026-09-20 case, and it is not an
        # untracked file: git registers it under .git/worktrees/, so no gitignore entry can
        # prune it. The predicate must be `git worktree list`, and it must be proved here or
        # the fourth repeat of this incident ships with a self-test claiming the third is fixed.
        subprocess.run(
            [GIT, "add", "-A"], cwd=tmp, capture_output=True, check=False
        )
        subprocess.run(  # noqa: S603
            [GIT, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "seed"],
            cwd=tmp,
            capture_output=True,
            check=False,
        )
        nested_wt = base / "nested-wt"
        add = subprocess.run(  # noqa: S603
            [GIT, "worktree", "add", "-q", "--detach", str(nested_wt)],
            cwd=tmp,
            capture_output=True,
            check=False,
        )
        if add.returncode != 0:
            failures.append(
                "could not create the nested worktree this arm exists to test: "
                + add.stderr.decode(errors="replace").strip()
            )
        else:
            (nested_wt / "bad.yaml").write_text("a nested worktree's fixture\n")
            expect(
                not is_this_tree(nested_wt / "bad.yaml", base),
                "a linked worktree inside the root must NOT be this tree",
            )
            walked_nested = [
                os.path.relpath(d, os.path.realpath(base))
                for d, _, _ in walk_tree(base)
                if os.path.relpath(d, os.path.realpath(base)).startswith("nested-wt")
            ]
            expect(
                not walked_nested,
                f"walk_tree entered a linked worktree: {walked_nested[:3]}",
            )

    if failures:
        for f in failures:
            print(f"FAIL treewalk --self-test: {f}")
        return 1
    print(
        "ok   treewalk --self-test: walk prunes ignored dirs and .git; "
        "is_this_tree says yes outside the root, no inside a nested checkout"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
