"""Incident 2026-08-28 (crew#412, oke-check catalogue-roll 33173246339): the founder location
was mounted at /estate/founder/catalog-info.yaml and Backstage refused the whole file:
`YAMLParseError: Map keys must be unique` — so not one founder surface reached the portal.
Commit 4bda9f3 (#352) appended the founder-mcp-gateway Component without its `spec`, `---`
and `metadata:` header, so its keys landed inside founder-showcase's metadata as duplicates.
Nothing caught it because every test loads the catalogue with PyYAML, which silently keeps
the last duplicate key; Backstage's parser (eemeli/yaml) refuses the document.
Rule: every catalog file is parsed with a loader that refuses duplicate keys, and every
entity in it carries the spec Backstage needs."""

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class _StrictLoader(yaml.SafeLoader):
    """PyYAML's SafeLoader lets a later duplicate key overwrite the earlier one; Backstage does not."""


def _no_duplicate_keys(loader, node):
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"duplicate map key {key!r} at line {key_node.start_mark.line + 1}"
                f" (first at line {seen[key]})",
                key_node.start_mark,
            )
        seen[key] = key_node.start_mark.line + 1
    return loader.construct_mapping(node, deep=True)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def _catalog_files():
    out = subprocess.run(
        ["git", "ls-files", "--", "*catalog-info.yaml", "*/catalog-info.yaml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    files = sorted({ROOT / f for f in out})
    assert (ROOT / "backstage/founder/catalog-info.yaml") in files
    return files


def strict_docs(path: Path):
    return [d for d in yaml.load_all(path.read_text(), Loader=_StrictLoader) if d]


@pytest.mark.parametrize(
    "path", _catalog_files(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_catalog_file_has_no_duplicate_keys(path: Path) -> None:
    strict_docs(path)  # raises with the line numbers of both keys


def test_strict_loader_refuses_the_incident_shape() -> None:
    text = (
        "apiVersion: v1\nkind: Component\nmetadata:\n  name: a\n  tags: []\n  name: b\n"
    )
    with pytest.raises(
        yaml.constructor.ConstructorError, match="duplicate map key 'name'"
    ):
        list(yaml.load_all(text, Loader=_StrictLoader))
