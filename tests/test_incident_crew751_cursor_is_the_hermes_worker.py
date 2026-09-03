"""crew#751: Cursor is Hermes's WORK runtime. Architect stays on the router.

Cursor is an agent harness, not a LiteLLM completions lane. WORK dispatch must name
`cursor` as the live runtime, reach the Mac only through `cursor-agent` (which execs
`mac-run`), and never put the API key in git or in argv. The key is a vendor root
(SEED_CURSOR_API_KEY) proved and vaulted by bin/idp-bootstrap-vendors.
"""

# ruff: noqa: S101, S105, S603

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "platform" / "hermes-agent"
GATEWAY = HERMES / "gateway.yaml"
ESTATE = HERMES / "estate.yaml"
REG = ROOT / "platform/vendors/consoles.yaml"
WF = ROOT / ".github/workflows/oke-check.yml"
WRAPPER = HERMES / "cursor-agent.tpl"
FOUNDER = ROOT / "backstage/founder/catalog-info.yaml"
GEN = ROOT / "bin/catalog-gen"
FIX = ROOT / "tests/fixtures/inventory.json"


def _estate():
    cfg = yaml.safe_load(ESTATE.read_text())
    return yaml.safe_load(cfg["data"]["estate.yaml"])


def _gateway():
    for doc in yaml.safe_load_all(GATEWAY.read_text()):
        if doc and doc.get("kind") == "Deployment":
            return doc
    raise AssertionError("no Deployment in gateway.yaml")


def test_work_dispatch_runtime_is_cursor_through_the_wrapper():
    doc = _estate()
    assert doc["dispatch"]["runtime"] == "cursor"
    argv = doc["dispatch"]["runtimes"]["cursor"]
    assert argv[0] == "cursor-agent"
    assert "{prompt}" in argv
    assert "CURSOR_API_KEY" not in argv
    joined = " ".join(argv)
    assert "sk-" not in joined and "key_" not in joined


def test_cursor_agent_wrapper_refuses_the_mac_login_without_a_vault_key():
    text = WRAPPER.read_text()
    assert "mac-run" in text and "exec mac-run" in text
    assert "exec agent" in text
    assert "\ncp " not in text and " cp " not in text
    assert "key_" not in text and "crsr_" not in text
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert "--api-key" not in code
    assert "env CURSOR_API_KEY=" not in code
    assert "no CURSOR_API_KEY" in text
    assert "refusing the Mac login" in text
    assert "exit 2" in text


def test_the_cluster_estate_is_the_only_live_dispatch_file():
    text = ESTATE.read_text()
    assert "LIVE estate the cluster runs" in text
    assert "hermes-v2/estate.yaml is the Mac ancestor" in text
    doc = _estate()
    assert doc["dispatch"]["runtime"] == "cursor"
    assert "claude" in doc["dispatch"]["runtimes"]


def test_cursor_agent_is_a_subpath_on_the_hashed_configmap():
    gw = next(
        c
        for c in _gateway()["spec"]["template"]["spec"]["containers"]
        if c["name"] == "gateway"
    )
    mounts = [m for m in gw["volumeMounts"] if m["name"] == "mac-run"]
    by_path = {m["mountPath"]: m["subPath"] for m in mounts}
    assert by_path["/usr/local/bin/mac-run"] == "mac-run"
    assert by_path["/usr/local/bin/cursor-agent"] == "cursor-agent"


def test_cursor_is_a_named_vendor_root_mapped_into_apply():
    vendors = yaml.safe_load(REG.read_text())["vendors"]
    row = vendors["cursor"]
    assert row["secret"] == "SEED_CURSOR_API_KEY"
    assert row["targets"] == [{"entry": "hermes-agent-env", "field": "CURSOR_API_KEY"}]
    assert "SEED_CURSOR_API_KEY: ${{ secrets.SEED_CURSOR_API_KEY }}" in WF.read_text()
    assert "bin/idp-bootstrap-vendors" in WF.read_text()


def _founder():
    return [d for d in yaml.safe_load_all(FOUNDER.read_text()) if d]


def test_cursor_is_a_founder_surface_that_opens_the_catalogue_resource():
    docs = {d["metadata"]["name"]: d for d in _founder()}
    card = docs["founder-cursor"]
    assert card["spec"]["type"] == "founder-surface"
    assert "resource:default/vendor-cursor" in card["spec"]["dependsOn"]
    urls = {l["url"] for l in card["metadata"]["links"]}
    assert (
        "https://catalogue.${ESTATE_ZONE}/catalog/default/resource/vendor-cursor"
        in urls
    )
    assert "https://cursor.com/dashboard/integrations" in urls
    assert "https://github.com/chidionyema/crew/issues/751" in urls
    otto = docs["founder-otto"]
    assert "resource:default/vendor-cursor" in otto["spec"]["dependsOn"]
    assert "founder-cursor" in otto["metadata"]["description"]
    ours = {l["url"] for l in card["metadata"]["links"]}
    others = {
        l["url"]
        for d in docs.values()
        if d is not card
        for l in d["metadata"].get("links") or []
    }
    assert not ours & others, ours & others


def test_catalog_gen_emits_vendor_cursor_from_the_registry(tmp_path):
    """Cursor has no inventory coupling today; the registry row is the source (STANDARDS row 6)."""
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run(
        [str(GEN)],
        env={
            **os.environ,
            "INV": str(FIX),
            "OUT": str(out),
            "ESTATE_ENV": "dev",
            "CATALOG_GEN_ROOT": str(ROOT),
            "CATALOG_GEN_PROBE": "0",
        },
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    docs = {
        d["metadata"]["name"]: d
        for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text())
        if d
    }
    vendors = yaml.safe_load(REG.read_text())["vendors"]
    for name, row in vendors.items():
        entity = docs[f"vendor-{name}"]
        assert entity["kind"] == "Resource"
        assert entity["spec"]["type"] == "vendor"
        if row.get("page"):
            assert row["page"] in {l["url"] for l in entity["metadata"]["links"]}
    cursor = docs["vendor-cursor"]
    assert (
        cursor["metadata"]["annotations"]["estate/registry"]
        == "platform/vendors/consoles.yaml"
    )
    assert "https://cursor.com/dashboard/integrations" in {
        l["url"] for l in cursor["metadata"]["links"]
    }
