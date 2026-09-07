"""2026-09-07: two vendor Resources never reached the catalogue because of one character.

Backstage validates a tag against a narrower grammar than a name: sequences of [a-z0-9+#]
joined by single dashes. bin/catalog-gen emitted tags through slug(), whose character class
keeps `_` and `.` because a *name* may hold them. Every vendor Resource carries a
`coupling-<key>` tag built from the key in platform/vendors/consoles.yaml, so the two keys
with an underscore -- apprise_telegram and google_oauth -- produced

    "tags.1" is not valid; expected a string that is sequences of [a-z0-9+#] separated by [-]

and were refused at ingestion. Neither vendor was in the portal at all.

These tests grade the generated documents, not the source: run the generator over the fixture
inventory and read every tag it wrote back out of the parsed YAML.
"""

# ruff: noqa: S101, S603

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"

# github.com/backstage/backstage packages/catalog-model/src/entity/validation/Entity.schema.json
TAG = re.compile(r"^[a-z0-9+#]+(-[a-z0-9+#]+)*$")


def _catalog_gen():
    """bin/catalog-gen as a module; it has no .py suffix and guards its own main()."""
    spec = importlib.util.spec_from_loader(
        "catalog_gen", importlib.machinery.SourceFileLoader("catalog_gen", str(GEN))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _generated(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    p = subprocess.run(
        [str(GEN)],
        env={
            **os.environ,
            "INV": str(ROOT / "tests" / "fixtures" / "inventory.json"),
            "OUT": str(out),
            "ESTATE_ENV": "dev",
            "CATALOG_GEN_ROOT": str(ROOT),
            "CATALOG_GEN_PROBE": "0",
        },
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


def test_every_generated_tag_is_one_backstage_would_accept(tmp_path):
    bad = [
        (d["metadata"]["name"], t)
        for d in _generated(tmp_path)
        for t in (d.get("metadata", {}).get("tags") or [])
        if not TAG.match(t)
    ]
    assert bad == [], f"tags Backstage refuses at ingestion: {bad}"


def test_the_generator_writes_a_tag_at_least_one_entity_can_be_found_by(tmp_path):
    """A grammar test passes trivially on an empty set; prove tags are actually emitted."""
    tagged = [d for d in _generated(tmp_path) if d.get("metadata", {}).get("tags")]
    assert len(tagged) > 10


def test_an_underscore_in_a_vendor_key_becomes_a_dash_not_a_rejection():
    """The two keys that were refused, and the shape of the class they belong to."""
    tag_slug = _catalog_gen().tag_slug
    assert tag_slug("coupling-apprise_telegram") == "coupling-apprise-telegram"
    assert tag_slug("coupling-google_oauth") == "coupling-google-oauth"
    for raw in ("A.B", "x__y", "-lead", "trail-", "sp ace", "c++", "c#"):
        assert TAG.match(tag_slug(raw)), raw


def test_a_name_may_still_hold_an_underscore(tmp_path):
    """tag_slug is for tags only: entity names keep the wider grammar slug() gives them."""
    mod = _catalog_gen()
    assert mod.slug("apprise_telegram") == "apprise_telegram"
