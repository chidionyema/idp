"""One agent session's scratch file is not a catalogue entity.

Founder, 2026-09-07, reading the portal's default namespace: "these cluade things here are
judt noise and obscuring whats inprtantt". Measured then: 292 of 617 entities were shards of
two ~/.claude ledgers that are written one file per agent session, and 200 entity names
spelled his home directory and worktree layout onto a public page (LAW 46).

These tests grade `fold_families` in bin/catalog-gen, which reads the `member_of` field the
inventory already collects, and they grade the generated catalogue itself so the noise cannot
come back by way of a new family.
"""

import importlib.machinery
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "catalog" / "catalog-info.yaml"

# LAW 45: load the generator the way it is actually run -- by file path, not as a package.
_spec = importlib.util.spec_from_loader(
    "idp_catalog_gen",
    importlib.machinery.SourceFileLoader(
        "idp_catalog_gen", str(ROOT / "bin" / "catalog-gen")
    ),
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _entities():
    return [d for d in yaml.safe_load_all(CATALOGUE.read_text()) if d]


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


def test_no_catalogue_entity_names_a_path_on_this_machine():
    """LAW 46 on the portal: an entity name is a URL, and these were mangled absolute paths."""
    bad = [
        e["metadata"]["name"]
        for e in _entities()
        if "-Users-" in e["metadata"]["name"]
        or "-private-tmp-" in e["metadata"]["name"]
    ]
    assert bad == []


def test_no_single_family_dominates_the_catalogue():
    """The shape of the defect, not the instance: any prefix holding more than a fifth of the
    entities is a shard family that escaped the fold, whatever it is called next time."""
    names = [e["metadata"]["name"] for e in _entities()]
    prefixes = {}
    for n in names:
        prefixes.setdefault("-".join(n.split("-")[:2]), 0)
        prefixes["-".join(n.split("-")[:2])] += 1
    worst, count = max(prefixes.items(), key=lambda kv: kv[1])
    assert count <= len(names) // 5, (
        f"{count} of {len(names)} entities start with {worst!r}"
    )
