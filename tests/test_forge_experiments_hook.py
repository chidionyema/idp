# ruff: noqa: S101
"""bin/mkdocs_hooks/forge_experiments.py: every Forge experiment reaches TechDocs with a plain
English index (crew#885). Graded on the parsed table, not on prose."""

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    path = ROOT / "bin" / "mkdocs_hooks" / "forge_experiments.py"
    loader = importlib.machinery.SourceFileLoader("forge_experiments", str(path))
    spec = importlib.util.spec_from_loader("forge_experiments", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_hook_copies_every_experiment_and_indexes_it(tmp_path, monkeypatch):
    mod = load()
    src = tmp_path / "experiments"
    src.mkdir()
    (src / "README.md").write_text("# readme\n")
    (src / "0001-x-plan.md").write_text(
        "---\nexperiment: 0001-x-plan\ntask: x\nstatus: pre-registered\n---\n\n# P\n\n"
        "## In plain English\n\nA small model does x.\nStill x.\n\nMore.\n"
    )
    (src / "20260906T1200Z-x.md").write_text(
        "---\nexperiment: 20260906T1200Z-x\ntask: x\nverdict: shipped\nagreement: 0.97\n"
        "abstain_rate: 0.1\nusd: 0.42\n---\n\n# R\n"
    )
    monkeypatch.setattr(mod, "SRC", src)
    monkeypatch.setattr(mod, "OUT", tmp_path / "out")
    out = mod.write_pages()
    assert {p.name for p in out.glob("*.md")} == {
        "README.md",
        "0001-x-plan.md",
        "20260906T1200Z-x.md",
        "index.md",
    }
    rows = [
        [c.strip() for c in line.strip("|").split("|")]
        for line in (out / "index.md").read_text().splitlines()
        if line.startswith("| [")
    ]
    by_name = {r[0]: r for r in rows}
    assert (
        by_name["[0001-x-plan](0001-x-plan.md)"][2] == "A small model does x. Still x."
    )
    assert by_name["[20260906T1200Z-x](20260906T1200Z-x.md)"][3:] == [
        "97%",
        "10%",
        "0.42",
    ]


def test_hook_is_wired_and_its_output_ignored():
    import yaml

    cfg = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
    assert "bin/mkdocs_hooks/forge_experiments.py" in cfg["hooks"]
    nav = yaml.safe_dump(cfg["nav"])
    assert "reference/forge/index.md" in nav
    assert "docs/reference/forge/" in (ROOT / ".gitignore").read_text().splitlines()
