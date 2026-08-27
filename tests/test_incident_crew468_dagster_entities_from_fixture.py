"""crew#468: every Dagster asset, job and schedule becomes a catalogue entity through a Backstage
EntityProvider, never a hand-written catalog-info.yaml. The mapping (Dagster GraphQL JSON ->
Backstage entities) is pure TypeScript, proved against a recorded fixture with no network in
backstage/plugins/catalog-backend-module-dagster-entity-provider/src/mapping.test.ts -- that is
the rung-4 test; jest, not pytest, runs it (LAW: cheapest rung, and Python cannot type-check a
Backstage EntityProvider). This file is the half a rung-4 test that pytest actually can hold:
the fixture and the module exist, and app-config declares the provider with a poll schedule and
no literal hostname (LAW 46). No network socket is opened by this file.
"""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "backstage" / "plugins" / "catalog-backend-module-dagster-entity-provider"
FIXTURE = MODULE / "__fixtures__" / "dagster-response.json"
APP_CONFIG = ROOT / "backstage" / "app-config.yaml"
BACKEND_INDEX = ROOT / "backstage" / "packages" / "backend" / "src" / "index.ts"
BACKEND_PACKAGE_JSON = ROOT / "backstage" / "packages" / "backend" / "package.json"


def test_the_module_and_its_pure_mapping_and_jest_test_exist():
    for rel in ("package.json", "src/index.ts", "src/DagsterEntityProvider.ts",
                "src/mapping.ts", "src/mapping.test.ts", "src/dagsterClient.ts", "src/types.ts"):
        assert (MODULE / rel).is_file(), rel


def test_the_fixture_is_a_recorded_dagster_graphql_response_with_lineage_and_owners():
    payload = json.loads(FIXTURE.read_text())
    asset_nodes = payload["data"]["assetNodes"]
    assert len(asset_nodes) >= 2, "fixture needs at least one dependency edge to prove lineage"
    dependents = [a for a in asset_nodes if a["dependencyKeys"]]
    assert dependents, "fixture must carry at least one asset with dependencyKeys (lineage)"
    owners = {tuple(a["owners"]) for a in asset_nodes}
    assert any(o and o[0].startswith("team:") for o in owners), "no team owner in fixture"
    assert any(o and "@" in o[0] for o in owners), "no user-email owner in fixture"
    assert any(len(o) == 0 for o in owners), "no owner-less asset in fixture (fallback path)"
    repos = payload["data"]["repositoriesOrError"]["nodes"]
    assert repos and repos[0]["jobs"] and repos[0]["schedules"]


def test_app_config_declares_the_dagster_provider_with_a_schedule_and_no_literal_hostname():
    config = yaml.safe_load(APP_CONFIG.read_text())
    dagster = config["catalog"]["providers"]["dagster"]
    assert "schedule" in dagster, "no poll schedule configured"
    assert "frequency" in dagster["schedule"], "schedule carries no frequency"
    url = dagster["url"]
    assert url.startswith("${DAGSTER_GRAPHQL_URL"), (
        f"catalog.providers.dagster.url must read the env var, not a literal host: {url!r}"
    )
    # LAW 46: no literal IP/hostname anywhere outside the one documented local-dev default,
    # inside the ${VAR:-default} substitution itself.
    raw = APP_CONFIG.read_text()
    dagster_block_start = raw.index("dagster:")
    dagster_block = raw[dagster_block_start:dagster_block_start + 400]
    assert "url: ${DAGSTER_GRAPHQL_URL" in dagster_block


def test_the_backend_registers_the_module():
    src = BACKEND_INDEX.read_text()
    assert "backend.add(\n  import('catalog-backend-module-dagster-entity-provider'),\n)" in src

    pkg = json.loads(BACKEND_PACKAGE_JSON.read_text())
    assert pkg["dependencies"]["catalog-backend-module-dagster-entity-provider"] == "workspace:*"
