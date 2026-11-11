"""DBG-033's falsifier: a pack pointing at a test that exists in no ref cannot fire.

The incident: a `git reset --hard` in a shared checkout destroyed five scripts and seven
tests that existed only in the working tree. Among the casualties was
`tests/test_edge_cutover.py`, which DBG-001 names as its falsifier. DBG-001 then sat in the
catalogue looking like a closed defect while the test meant to prove it existed nowhere --
a pack graded by a file that is not in the repository.

This test reads `docs/debugging-packs.json` and, for every pack whose falsifier names a test
path, asserts that path is recoverable from disk or from at least one ref. It does not demand
that every pack be provable today -- a pack may name a test that is planned. It demands that
the pack SAY so, because a pack claiming `fixed` on a falsifier nobody can locate is the
defect this test closes.

A missing test is therefore reported twice over: `status: fixed` plus an unlocatable path.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKS = REPO / "docs" / "debugging-packs.json"

# A falsifier may describe its test in prose and name it in a path-like token.
TEST_PATH = re.compile(r"\b((?:tests|platform|bin)/[\w./-]+\.(?:py|sh|js|mjs))\b")
REQUIRED = ("id", "title", "symptom", "cause", "falsifier", "remedy", "status", "law")


def _packs() -> list[dict]:
    if not PACKS.exists():
        raise AssertionError(f"BLIND: {PACKS} does not exist, so no pack was graded")
    return json.loads(PACKS.read_text())["packs"]


def _refs() -> list[str]:
    out = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.split()
    return ["HEAD", *out]


def test_the_repository_still_has_history_to_check_against():
    """A guard whose own failure mode is 'found nothing' must prove it could look."""
    assert _paths_in_all_refs(), (
        "BLIND: no paths found in any ref, so nothing was graded"
    )


def _paths_in_all_refs() -> set[str]:
    """Every pack's falsifier path is either on disk or has history in SOME ref.

    This checkout carries 1309 refs and the host runs at load ~200. One `git ls-tree` per ref
    is 1309 spawns; a full `git log --all --name-only` walks the entire object graph. Both
    time out. The question is bounded, so the query is bounded: ask `git log --all` only
    about the paths named by packs, in ONE process.
    """
    wanted = sorted(
        {p for pack in _packs() for p in TEST_PATH.findall(pack.get("falsifier", ""))}
    )
    if not wanted:
        return set()
    out = subprocess.run(
        ["git", "log", "--all", "--pretty=format:", "--name-only", "--", *wanted],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=110,
    ).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def test_no_pack_claims_fixed_on_a_falsifier_that_exists_nowhere():
    in_refs = _paths_in_all_refs()
    offenders = []
    for pack in _packs():
        if pack.get("status") != "fixed":
            continue
        for path in TEST_PATH.findall(pack.get("falsifier", "")):
            if not (REPO / path).exists() and path not in in_refs:
                offenders.append((pack["id"], path))

    assert not offenders, (
        "DBG-033 FIRES: these packs claim `fixed` but their falsifier exists in no ref and "
        "on no disk, so nobody can ever run the proof they rely on:\n"
        + "\n".join(f"  {pid} -> {p}" for pid, p in offenders)
        + "\nRestore the test, or mark the pack `unrecoverable` and say why."
    )


def test_every_pack_carries_the_full_contract():
    for pack in _packs():
        missing = [k for k in REQUIRED if not pack.get(k)]
        assert not missing, f"{pack.get('id')} is missing {missing}"


def test_pack_ids_are_unique_and_ordered():
    ids = [p["id"] for p in _packs()]
    assert len(ids) == len(set(ids)), f"duplicate pack ids: {ids}"
    assert ids == sorted(ids), "pack ids must stay ordered"
