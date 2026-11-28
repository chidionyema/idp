"""bin/estate-dag-gen renders the same graph whatever order the directory lists its files.

`tf_files = list(TF_ROOT.glob("*.tf"))` took the directory's own order. The Greenlane engine and the
`estate-dag-gen` workflow regenerate docs/diagrams/estate-dag.dot on different filesystems, so they
disagreed (a 38-line reorder, no content change). The workflow then pushed a second commit onto the
queue branch, the tip moved off the sha the required checks had been posted on, and the engine
refused the batch "still waiting on fast-gate, bdd, ... 600s after the push" (b6418, then b6417 was
requeued: idp#7387 sat pending 80 minutes).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import itertools
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "bin" / "estate-dag-gen"

FILES = {
    "a.tf": 'resource "oci_core_vcn" "main" {}\nresource "oci_core_subnet" "s" { vcn = oci_core_vcn.main }\n',
    "b.tf": 'resource "oci_vault_secret" "k" {}\n',
    "c.tf": 'module "net" { x = oci_vault_secret.k }\nresource "oci_core_instance" "i" { s = oci_core_subnet.s }\n',
}


class Listing:
    """Stands in for TF_ROOT: `glob` lists the files in the order a filesystem chose."""

    def __init__(self, root: Path, order: tuple[str, ...]):
        self.root, self.order = root, order

    def glob(self, pattern: str):
        assert pattern == "*.tf"
        return [self.root / name for name in self.order]


def load(source: Path = GEN):
    loader = importlib.machinery.SourceFileLoader("estate_dag_gen_order", str(source))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def renderings(module, root: Path) -> set[str]:
    """Every distinct estate-dag.dot the generator emits across all directory orders."""
    for name, text in FILES.items():
        (root / name).write_text(text)
    out = set()
    for order in itertools.permutations(FILES):
        module.TF_ROOT = Listing(root, order)
        resources, dependencies = module.parse_terraform_files()
        out.add(module.gen_dot_graph(resources, dependencies))
    return out


def test_every_directory_order_renders_one_graph(tmp_path):
    assert len(renderings(load(), tmp_path)) == 1


def test_the_graph_keeps_every_node_in_sorted_order(tmp_path):
    (dot,) = renderings(load(), tmp_path)
    nodes = [line.split('"')[1] for line in dot.splitlines() if "[label=" in line]
    assert nodes == [
        "oci_core_instance.i",
        "oci_core_subnet.s",
        "oci_core_vcn.main",
        "oci_vault_secret.k",
    ]


def test_falsifier_the_unsorted_generator_renders_more_than_one_graph(tmp_path):
    text = GEN.read_text()
    fixed = 'tf_files = sorted(TF_ROOT.glob("*.tf"))'
    assert fixed in text, "the sorted glob moved; update the falsifier"
    old = tmp_path / "estate-dag-gen-old"
    old.write_text(
        text.replace(fixed, 'tf_files = list(TF_ROOT.glob("*.tf"))')
        .replace("sorted(resources.items())", "resources.items()")
        .replace("sorted(dependencies.items())", "dependencies.items()")
    )
    work = tmp_path / "tf"
    work.mkdir()
    assert len(renderings(load(old), work)) > 1


if __name__ == "__main__":
    import tempfile

    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/estate/test_dag_gen_order_independent.py --optimus [--source PATH]"
        )
    src = (
        Path(sys.argv[sys.argv.index("--source") + 1])
        if "--source" in sys.argv
        else GEN
    )
    with tempfile.TemporaryDirectory() as d:
        print(
            f"optimus.estate.dag_gen_order_variants={len(renderings(load(src), Path(d))) - 1}"
        )
