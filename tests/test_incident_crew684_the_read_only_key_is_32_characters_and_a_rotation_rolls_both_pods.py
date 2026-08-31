"""crew#684, 2026-08-30 07:31Z (oke-check 33299061377, playbook healthchecks-door): the portal and
Healthchecks held the same key, enrol had saved it, and every read still answered 401
`missing api key`. Healthchecks v4.3 refuses any key whose length is not 32 before it touches
the database (hc/api/decorators.py:79). The vault minted a 36-character UUID.

Second half: a rotated key reaches neither pod by itself. enrol runs at Healthchecks start and
the portal reads `$file` once at start, and Reloader watched only the llm namespace, so the
annotations that were meant to roll the pods (idp#955 included) were inert.

That second half is no longer graded here. It was graded by naming these two workloads and the
Secret each one lists, which is the rot the fix deleted; it is now
tests/test_incident_crew684_every_workload_restarts_when_its_config_changes.py, over every workload
in the estate, with no name in it."""

import re
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "platform" / "oci" / "healthchecks.tf"
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
