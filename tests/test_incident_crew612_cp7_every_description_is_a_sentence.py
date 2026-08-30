"""crew#612 CP7, founder 2026-08-29: "it's too cryptic", "don't assume the user knows what you know".

Measured 2026-08-30 01:50Z on the generated catalogue: 38 of 438 entities carried a description
that was not a sentence. 28 database files said the one word "database" (the inventory's stub
`what`, printed verbatim), and 7 cluster rows and jobs carried a fragment such as
"Kubernetes Secrets." because the first-sentence extractor skipped line 1 of every file as if it
were a shebang, dropping the opening line of every YAML comment block. Two rules:

  1. a `what` under five words is a hint on a measured sentence, never the sentence;
  2. only a shebang line is skipped before the comment block is read.

The sweep at the end grades every entity the fixture produces: three words or more, never a
bare stub word.
"""

import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
FIX = ROOT / "tests" / "fixtures" / "inventory.json"
STUBS = {"database", "data", "file", "ledger"}


def _mod():
    loader = importlib.machinery.SourceFileLoader("catalog_gen", str(GEN))
    spec = importlib.util.spec_from_loader("catalog_gen", loader)
    mod = importlib.util.module_from_spec(spec)
    os.environ.setdefault("CATALOG_GEN_ROOT", str(ROOT))
    os.environ.setdefault("ESTATE_ENV", "dev")
    loader.exec_module(mod)
    return mod


def test_a_one_word_what_becomes_a_hint_on_a_measured_sentence():
    d = _mod().describe(
        {
            "kind": "data",
            "what": "database",
            "path": "~/.estate/temporal/dev.db",
            "mb": 0.84,
            "referenced": True,
        }
    )
    assert d.startswith(
        "Database file at ~/.estate/temporal/dev.db, 0.84 MB, read by something in the estate"
    ), d
    assert d != "database"
    led = _mod().describe(
        {
            "kind": "ledger",
            "what": "the board of record",
            "path": "~/x.jsonl",
            "rows": 3,
            "referenced": False,
        }
    )
    assert "referenced by nothing; the board of record." in led, led


def test_a_full_sentence_what_still_wins():
    d = _mod().describe(
        {
            "kind": "data",
            "what": "every session verbatim: his words, every tool call",
            "path": "~/.claude/projects",
            "mb": 6376.7,
            "referenced": True,
        }
    )
    assert d.startswith("every session verbatim"), d


def test_only_a_shebang_is_skipped_before_the_comment_block(tmp_path):
    y = tmp_path / "helmrelease.yaml"
    y.write_text(
        "# External Secrets: syncs the vault into\n# Kubernetes Secrets. Second sentence.\napiVersion: v1\n"
    )
    assert (
        _mod()._docline(str(y))
        == "External Secrets: syncs the vault into Kubernetes Secrets."
    )
    sh = tmp_path / "job.sh"
    sh.write_text(
        "#!/usr/bin/env bash\n# Sovereign Bus shim. Ensures the venv exists.\nexec true\n"
    )
    assert _mod()._docline(str(sh)) == "Sovereign Bus shim."
    lab = tmp_path / "kustomization.yaml"
    lab.write_text(
        "# Edge row. Gateway API and DNS for every public door.\nresources: []\n"
    )
    assert (
        _mod()._docline(str(lab))
        == "Edge row. Gateway API and DNS for every public door."
    )


def test_every_generated_description_is_a_sentence(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run(
        [sys.executable, str(GEN)],
        env={
            **os.environ,
            "INV": str(FIX),
            "OUT": str(out),
            "ESTATE_ENV": "dev",
            "CATALOG_GEN_ROOT": str(ROOT),
        },
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    docs = [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]
    bad = []
    for d in docs:
        md = d.get("metadata") or {}
        desc = (md.get("description") or "").strip()
        if (
            len(desc.split()) < 3
            or desc.lower().rstrip(".") in STUBS
            or desc.lower() == md.get("name", "").lower()
        ):
            bad.append((md.get("name"), desc))
    assert not bad, bad
