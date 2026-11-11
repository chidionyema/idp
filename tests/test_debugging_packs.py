"""The pack index is a contract, and this is its falsifier.

Founder instruction, 2026-11-10: every edge case and every reached failure mode must be addressed
and usable as a debugging pack for any future issue. A pack that is prose in a doc is not usable at
3am; a pack that names a test is. So the index (docs/debugging-packs.json) is data, and this test
holds it to three promises:

  1. every pack names a falsifier that EXISTS (a path, or a file::test node that really is there);
  2. every falsifier in tests/ that this estate wrote for a cutover defect is claimed by exactly
     one pack -- one defect, one home, so a fix can never ship without its pack;
  3. every pack states its status honestly: `fixed` only with a falsifier, `external` only with a
     reference to where the defect actually lives.

A pack whose falsifier was deleted is the silent-gap failure AGENTS.md section 3a names: it would
look like coverage and be none. That is why rule 1 is checked against the filesystem, not trusted.
"""

import json
import re
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
INDEX = IDP / "docs" / "debugging-packs.json"

# Every falsifier in these files is claimed by a pack -- that is rule 2. The files are listed
# EXHAUSTIVELY on purpose: they exist only because of the defects in the index, so every test in
# them guards a named failure mode. Sweeping all of tests/ instead would demand a pack for a decade
# of unrelated work and the index would be abandoned inside a week.
CUTOVER_FALSIFIERS = [
    "tests/test_edge_cutover.py",
    "tests/test_thin_client.py",
    "tests/test_debugging_packs.py",
    "tests/test_claim_contract.py",
    "tests/test_claim_gate.py",
    "tests/test_claim_open_worktree.py",
    "tests/test_estate_context_claims.py",
    "tests/test_founder_prompt_collector.py",
    "tests/test_instruction_claim_failure_matrix.py",
    "tests/test_instruction_tracker.py",
    "tests/test_operationalise_reminder.py",
]


@pytest.fixture(scope="module")
def packs():
    assert INDEX.exists(), f"the debugging-pack index is missing: {INDEX}"
    data = json.loads(INDEX.read_text())
    assert data.get("packs"), "the index exists but carries no packs"
    return data["packs"]


def _falsifier_exists(spec: str) -> bool:
    """`path` or `path::test_name`, or a headed block of `path#Section heading`.

    Three shapes, because a defect is caught by a group of tests as often as by one, and a pack
    that is forced to name a single node starts describing a phantom. A `#` section names the
    block of the file that holds the falsifier(s); the heading must really be there.
    """
    path_part, sep, node = spec.partition("::")
    if not sep and "#" in spec:
        path_part, _, node = spec.partition("#")
    path = IDP / path_part
    if not path.exists():
        return False
    if not node:
        return True
    body = path.read_text()
    if re.search(rf"^def {re.escape(node)}\b", body, re.MULTILINE):
        return True
    # a section heading, matched against a comment line
    return any(
        re.search(rf"\b{re.escape(node)}\b", line)
        for line in body.splitlines()
        if line.lstrip().startswith("#")
    )


def test_no_falsifier_file_is_emptied_behind_the_index(packs):
    """The inverse of rule 2: a claimed file that lost all its tests is a pack with no mechanism.
    This is the deletion the file-grain rule alone would miss."""
    for rel in CUTOVER_FALSIFIERS:
        path = IDP / rel
        assert path.exists(), f"a listed falsifier file is gone: {rel}"
        assert re.search(r"^def test_\w+", path.read_text(), re.MULTILINE), (
            f"{rel} is claimed by a pack but holds no test -- the falsifier was deleted"
        )
    required = {
        "id",
        "title",
        "symptom",
        "cause",
        "falsifier",
        "remedy",
        "status",
        "law",
    }
    for p in packs:
        missing = required - set(p)
        assert not missing, f"{p.get('id')} is incomplete: missing {sorted(missing)}"


def test_pack_ids_are_unique(packs):
    ids = [p["id"] for p in packs]
    assert len(ids) == len(set(ids)), f"duplicate pack id in {ids}"


def test_every_pack_falsifier_really_exists(packs):
    """Rule 1: a deleted falsifier must fail the index, not silently shrink coverage."""
    dead = [p["id"] for p in packs if not _falsifier_exists(p["falsifier"])]
    assert not dead, f"packs naming a falsifier that does not exist: {dead}"


def test_no_two_packs_claim_the_same_falsifier(packs):
    """One defect, one home. Two packs on one test means one of them is describing a phantom."""
    seen = {}
    for p in packs:
        seen.setdefault(p["falsifier"], []).append(p["id"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"falsifiers claimed by more than one pack: {dupes}"


def _has_section(body: str, heading: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(heading)}", line)
        for line in body.splitlines()
        if line.lstrip().startswith("#")
    )


def test_every_cutover_falsifier_file_is_represented_by_a_pack(packs):
    """Rule 2, at the right grain.

    A pack covers a BEHAVIOUR, and a behaviour is often held by several tests: "a spent lane is
    skipped" needs both the chooser test and the accept-the-good-half test, and demanding one pack
    per test node would manufacture ten packs that each restate the same defect. The rule that has
    teeth is at the file grain -- every file this cutover created to hold falsifiers is claimed by
    at least one pack -- plus rule 1, which proves each named falsifier really exists. Together they
    make it impossible to delete the falsifiers and keep the index: an emptied file fails rule 2.
    """
    claimed_files = {p["falsifier"].split("::")[0].split("#")[0] for p in packs}
    orphaned = [rel for rel in CUTOVER_FALSIFIERS if rel not in claimed_files]
    assert not orphaned, (
        "these falsifier files are named by no debugging pack, so the defects they guard are\n"
        "remembered nowhere: " + ", ".join(orphaned)
    )


def test_a_fixed_pack_names_a_runnable_falsifier(packs):
    """`fixed` is a claim, and a claim needs its proof (AGENTS.md section 3)."""
    for p in packs:
        if p["status"] == "fixed":
            assert p["falsifier"], f"{p['id']} says fixed with no falsifier"


def test_an_external_pack_names_where_the_defect_lives(packs):
    """An external defect must not be quietly absorbed as 'ours, fixed'."""
    for p in packs:
        if p["status"] == "external":
            assert p.get("external_ref"), (
                f"{p['id']} is external with no reference to the tracker"
            )


def test_no_pack_carries_a_secret_value(packs):
    """A remedy names an env var and a door. It never carries a value (AGENTS.md section 4)."""
    # A 32+ character run with no whitespace is the shape of a token, not of prose.
    tokenish = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
    for p in packs:
        for field in ("remedy", "cause", "symptom"):
            for m in tokenish.finditer(p.get(field, "")):
                # long identifiers are legitimate; a known-prefix token is not
                assert not re.match(r"^(sk-|ghp_|gho_|xox|AKIA|eyJ)", m.group(0)), (
                    f"{p['id']}.{field} appears to carry a secret: {m.group(0)[:6]}..."
                )


def test_the_index_covers_the_defects_that_cost_this_cutover_its_time(packs):
    """The founder's list, pinned: dropping one of these re-opens a spent day."""
    must = {"DBG-001", "DBG-002", "DBG-003", "DBG-006", "DBG-010", "DBG-012"}
    have = {p["id"] for p in packs}
    assert must <= have, f"packs dropped from the index: {sorted(must - have)}"
