"""One agent session's scratch file is not a catalogue entity.

Founder, 2026-09-07, reading the portal's default namespace: "these cluade things here are
judt noise and obscuring whats inprtantt". Measured then: 292 of 617 entities were shards of
two ~/.claude ledgers that are written one file per agent session, and 200 entity names
spelled his home directory and worktree layout onto a public page (LAW 46).

These tests grade `fold_families` in bin/catalog-gen, which reads the `member_of` field the
inventory already collects, and they grade the generated catalogue itself so the noise cannot
come back by way of a new family.
"""

import functools
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "inventory.json"

# LAW 45: load the generator the way it is actually run -- by file path, not as a package.
_spec = importlib.util.spec_from_loader(
    "idp_catalog_gen",
    importlib.machinery.SourceFileLoader(
        "idp_catalog_gen", str(ROOT / "bin" / "catalog-gen")
    ),
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


@functools.lru_cache(maxsize=None)
def _catalogue_from(rows):
    """Run bin/catalog-gen the way bin/idp-ci does: INV and OUT pointed at a fixture.

    catalog/catalog-info.yaml itself is gitignored -- it is generated at deploy time from the
    machine's own inventory -- so grading the shipped file would be grading a file CI does not
    have. The generator over a fixture inventory is the same code on the same path.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    inv = json.loads(FIXTURE.read_text())
    inv["rows"] = (inv.get("rows") or []) + [json.loads(r) for r in rows]
    (tmp / "inv.json").write_text(json.dumps(inv))
    out = tmp / "out"
    env = {**os.environ, "INV": str(tmp / "inv.json"), "OUT": str(out)}
    r = subprocess.run(
        ["python3", str(ROOT / "bin" / "catalog-gen")],
        env=env,
        text=True,
        capture_output=True,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


# Hashable so the generated catalogue is built once for the whole module: the generator takes
# ~10 s a run and three tests read the same output.
SHARDS = tuple(
    json.dumps(r)
    for r in [
        {
            "id": f".claude/directives/-Users-someone-dev-code-.wt-{n}.jsonl",
            "path": f"/home/someone/.claude/directives/-Users-someone-dev-code-.wt-{n}.jsonl",
            "kind": "ledger",
            "root": "~/.claude",
            "member_of": "directives",
            "rows": 1,
            "coupling": "anthropic",
            "referenced": True,
        }
        for n in range(40)
    ]
)


def test_a_family_of_shards_becomes_one_row_carrying_the_whole_count():
    rows = [
        {
            "id": ".claude/directives/-a-b.jsonl",
            "path": "/h/.claude/directives/-a-b.jsonl",
            "kind": "ledger",
            "member_of": "directives",
            "rows": 3,
        },
        {
            "id": ".claude/directives/-c-d.jsonl",
            "path": "/h/.claude/directives/-c-d.jsonl",
            "kind": "ledger",
            "member_of": "directives",
            "rows": 4,
        },
    ]
    out = gen.fold_families(rows)
    assert len(out) == 1
    assert out[0]["id"] == ".claude/directives"
    assert out[0]["path"] == "/h/.claude/directives"
    assert out[0]["shards"] == 2
    assert out[0]["rows"] == 7  # summed, so folding never loses the measurement


def test_an_asset_that_is_not_a_shard_passes_through_untouched():
    row = {"id": "estate.db", "path": "/h/.estate/estate.db", "kind": "data", "mb": 12}
    assert gen.fold_families([row]) == [row]


def test_two_families_stay_two_entities():
    rows = [
        {
            "id": "a/one.jsonl",
            "path": "/h/a/one.jsonl",
            "kind": "ledger",
            "member_of": "directives",
            "rows": 1,
        },
        {
            "id": "b/two.jsonl",
            "path": "/h/b/two.jsonl",
            "kind": "ledger",
            "member_of": "prompt-ledger",
            "rows": 1,
        },
    ]
    assert sorted(r["id"] for r in gen.fold_families(rows)) == ["a", "b"]


def test_forty_session_shards_render_as_one_entity():
    entities = _catalogue_from(SHARDS)
    folded = [e for e in entities if e["metadata"].get("title") == ".claude/directives"]
    assert len(folded) == 1, "forty shards, one entity"
    assert "40 append-only directives files" in folded[0]["metadata"]["description"]


def test_no_entity_name_holds_a_path_from_the_machine_the_inventory_was_taken_on():
    """LAW 46 on the portal: an entity name is a URL, and each shard's was an absolute path."""
    names = {e["metadata"]["name"] for e in _catalogue_from(SHARDS)}
    assert not [n for n in names if "-wt-" in n and "-Users-" in n]


def test_a_family_renders_as_one_entity_however_many_sessions_wrote_to_it():
    """The shape of the defect, not the instance: whatever a family is called next time, the
    catalogue holds one entity for it and not one per file."""
    entities = _catalogue_from(SHARDS)
    directives = [
        e
        for e in entities
        if e["metadata"]
        .get("annotations", {})
        .get("estate/path", "")
        .endswith("/directives")
        and e["metadata"].get("annotations", {}).get("estate/kind") == "ledger"
    ]
    assert len(directives) == 1, [e["metadata"]["name"] for e in directives]
