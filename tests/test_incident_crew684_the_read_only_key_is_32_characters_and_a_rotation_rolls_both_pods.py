"""crew#684, 2026-08-30 07:31Z (oke-check 33299061377, playbook healthchecks-door): the portal and
Healthchecks held the same key, enrol had saved it, and every read still answered 401
`missing api key`. Healthchecks v4.3 refuses any key whose length is not 32 before it touches
the database (hc/api/decorators.py:79). The vault minted a 36-character UUID.

Second half: a rotated key reaches neither pod by itself. enrol runs at Healthchecks start and
the portal reads `$file` once at start, and Reloader watched only the llm namespace, so the
annotations that were meant to roll the pods (idp#955 included) were inert."""

import re
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "platform" / "oci" / "healthchecks.tf"
HC = ROOT / "platform" / "healthchecks" / "healthchecks.yaml"
CATALOGUE = ROOT / "platform" / "backstage" / "base" / "catalogue.yaml"
RELOADER = ROOT / "platform" / "reloader" / "reloader.yaml"
ES = [
    ROOT / "platform" / "healthchecks" / "external-secret.yaml",
    ROOT
    / "platform"
    / "backstage"
    / "overlays"
    / "oke"
    / "healthchecks-ro-external-secret.yaml",
]

VENDOR_KEY_LENGTH = 32  # hc/api/decorators.py:79 `if len(api_key) != 32: return error("missing api key", 401)`


def test_the_read_only_key_the_vault_mints_is_exactly_32_characters():
    m = re.search(r'"healthchecks-ro-key"\s*=\s*(.+)', TF.read_text())
    assert m, "the vault entry is gone"
    expr = m.group(1).strip()
    assert expr == 'replace(random_uuid.healthchecks_ro_key.result, "-", "")', expr
    # what that expression yields for any uuid
    assert len(str(uuid.uuid4()).replace("-", "")) == VENDOR_KEY_LENGTH


def _deployment(path: Path, name: str) -> dict:
    for doc in yaml.safe_load_all(path.read_text()):
        if doc and doc.get("kind") == "Deployment" and doc["metadata"]["name"] == name:
            return doc
    raise AssertionError(f"no Deployment {name} in {path}")


def test_a_rotated_key_rolls_both_pods():
    hc = _deployment(HC, "healthchecks")["metadata"]["annotations"][
        "secret.reloader.stakater.com/reload"
    ]
    assert "healthchecks" in hc.split(",")
    cat = _deployment(CATALOGUE, "catalogue")["metadata"]["annotations"][
        "secret.reloader.stakater.com/reload"
    ]
    assert "healthchecks-ro" in cat.split(",")
    values = None
    for doc in yaml.safe_load_all(RELOADER.read_text()):
        if doc and doc.get("kind") == "HelmRelease":
            values = doc["spec"]["values"]
    assert values is not None
    watched = values["reloader"]["namespaces"]
    assert values["reloader"]["watchGlobally"] is False
    for ns in ("healthchecks", "backstage", "hermes-agent", "llm"):
        assert ns in watched, f"Reloader does not watch {ns}; its annotations are inert"


def test_the_key_reaches_the_cluster_within_one_tile_refresh():
    for f in ES:
        docs = [d for d in yaml.safe_load_all(f.read_text()) if d]
        keyed = [
            d
            for d in docs
            if d["metadata"]["name"] in ("healthchecks", "healthchecks-ro")
        ]
        assert keyed, f
        for d in keyed:
            assert d["spec"]["refreshInterval"] == "10m", f
