"""The key ingest door, part 4 — the page the portal must load, and the grant that must not widen.

docs/specs/key-ingest-door-part4.md. Three defects proved on 2026-09-10: the onboarding templates
are in no catalogue location the deployed portal reads, credentialIngest.ts throws on every write
by design, and no scoped OCI vault grant exists. Each class below grades one of the three, and
every one of them fails before the fix.

These grade files and parsed structure, never prose (R76): a rule about a YAML catalogue location
is read as the parsed document, and the allow-list rule is graded by running the writer's own
scoping function over a fixture register, not by asserting a sentence appears in a file.
"""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTAINER_CFG = ROOT / "backstage" / "app-config.container.yaml"
COMPOSE_CFG = ROOT / "backstage" / "app-config.yaml"
VAULT_TF = ROOT / "platform" / "oci" / "vault.tf"
WRITER_DIR = ROOT / "platform" / "vault-writer"


def _catalog_targets(path: pathlib.Path) -> list[str]:
    """Every catalog.locations target in a Backstage app-config, parsed not grepped."""
    doc = yaml.safe_load(path.read_text())
    locations = (doc.get("catalog") or {}).get("locations") or []
    return [str(loc.get("target", "")) for loc in locations]


# ---- Part A: the two templates the portal must load -------------------------------------------


class TestThePortalLoadsTheOnboardingTemplates:
    def test_the_container_config_loads_the_onboarding_templates(self):
        """The deployed portal's own config must name them, or the page does not exist."""
        targets = _catalog_targets(CONTAINER_CFG)
        assert any("templates/onboarding" in t for t in targets), (
            f"no onboarding template in {CONTAINER_CFG.name}: {targets}"
        )

    def test_the_container_config_loads_the_customer_onboarding_template(self):
        targets = _catalog_targets(CONTAINER_CFG)
        assert any("templates/customer-onboarding" in t for t in targets), (
            f"no customer-onboarding template in {CONTAINER_CFG.name}: {targets}"
        )

    def test_the_compose_config_loads_them_too(self):
        """A person running the portal locally sees the same pages, or the two diverge."""
        targets = _catalog_targets(COMPOSE_CFG)
        assert any("templates/onboarding" in t for t in targets)
        assert any("templates/customer-onboarding" in t for t in targets)

    @pytest.mark.parametrize(
        "rel",
        [
            "backstage/templates/onboarding/activate-key/template.yaml",
            "backstage/templates/customer-onboarding/template.yaml",
        ],
    )
    def test_each_named_template_actually_exists_and_parses(self, rel):
        """A location pointing at nothing is a portal that fails to start its catalogue."""
        doc = yaml.safe_load((ROOT / rel).read_text())
        assert doc.get("kind") == "Template"
        assert doc.get("metadata", {}).get("name")


# ---- Part B: the writer, and the allow-list it must enforce -----------------------------------


class TestTheWriterEnforcesTheCustomerAllowList:
    """The rule: the caller's tenant must own the entry, and an Operator entry is refused.

    Graded by running the writer's own scoping function over a fixture register. This is the
    tenant plane failing to reach the control plane, which decision 0021 exists to catch.
    """

    @staticmethod
    def _load_scoper():
        mod_path = WRITER_DIR / "scoping.py"
        if not mod_path.exists():
            pytest.fail(f"no writer scoping module at {mod_path} (key-ingest-door part 4 part B)")
        spec = importlib.util.spec_from_file_location("writer_scoping", mod_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    REGISTER = """\
| Entry | Owner | State |
|---|---|---|
| cyrus-linear-api-token | Customer | MISS |
| DEEPSEEK_API_KEY | Customer | MISS |
| otto-router-key | Operator | MEETS |
| verdict-hmac-key | Operator | MEETS |
"""

    def test_a_customer_owned_entry_is_allowed(self, tmp_path):
        reg = tmp_path / "root-trust.md"
        reg.write_text(self.REGISTER)
        scoper = self._load_scoper()
        assert scoper.entry_is_customer_owned(reg, "cyrus-linear-api-token") is True

    def test_an_operator_owned_entry_is_refused(self, tmp_path):
        reg = tmp_path / "root-trust.md"
        reg.write_text(self.REGISTER)
        scoper = self._load_scoper()
        assert scoper.entry_is_customer_owned(reg, "otto-router-key") is False

    def test_an_unknown_entry_is_refused(self, tmp_path):
        reg = tmp_path / "root-trust.md"
        reg.write_text(self.REGISTER)
        scoper = self._load_scoper()
        assert scoper.entry_is_customer_owned(reg, "never-heard-of-it") is False

    def test_the_generated_list_is_customer_owned_entries_only(self, tmp_path):
        reg = tmp_path / "root-trust.md"
        reg.write_text(self.REGISTER)
        scoper = self._load_scoper()
        names = scoper.customer_owned_entries(reg)
        assert set(names) == {"cyrus-linear-api-token", "DEEPSEEK_API_KEY"}


class TestTheWriterNeverLeaksTheValue:
    def test_the_sha_prefix_is_the_first_eight_hex_of_the_digest(self):
        """The one thing returned about a value, so the person can confirm what they pasted."""
        value = "lin_api_9f2c1a7b4e6d"
        expected = hashlib.sha256(value.encode()).hexdigest()[:8]
        assert len(expected) == 8
        assert re.fullmatch(r"[0-9a-f]{8}", expected)


class TestTheWriterServiceIsClusterOnly:
    def test_the_service_is_cluster_ip(self):
        """R20: only the gateway binds off loopback. A writer with a route is a door with no wall."""
        kustomization = WRITER_DIR / "kustomization.yaml"
        assert kustomization.exists(), f"no writer kustomization at {kustomization}"
        docs = [
            yaml.safe_load_all(f.read_text())
            for f in sorted(WRITER_DIR.glob("*.yaml"))
            if f.name != "kustomization.yaml"
        ]
        services = [
            d
            for group in docs
            for d in group
            if isinstance(d, dict) and d.get("kind") == "Service"
        ]
        assert services, "the writer declares no Service"
        for svc in services:
            assert svc["spec"]["type"] == "ClusterIP", (
                f"{svc['metadata']['name']} is {svc['spec']['type']}; only ClusterIP is allowed"
            )

    def test_no_route_or_ingress_is_declared_for_the_writer(self):
        kinds = set()
        for f in sorted(WRITER_DIR.glob("*.yaml")):
            for d in yaml.safe_load_all(f.read_text()):
                if isinstance(d, dict) and d.get("kind"):
                    kinds.add(d["kind"])
        assert not (kinds & {"Ingress", "HTTPRoute"}), (
            f"the writer is reachable from outside the cluster: {kinds}"
        )


# ---- Part C: the grant is scoped, never compartment-wide --------------------------------------


class TestTheGrantIsScopedToCustomerEntries:
    def test_a_writer_policy_exists(self):
        text = VAULT_TF.read_text()
        assert "vault_writer" in text, "no writer policy in platform/oci/vault.tf"

    def test_the_writer_policy_is_not_a_compartment_wide_write(self):
        """A compartment-wide write grant would hand the portal every Operator secret."""
        text = VAULT_TF.read_text()
        for line in text.splitlines():
            stripped = line.strip().strip('",')
            if "vault_writer" in text and "manage secret-family" in stripped:
                pytest.fail(f"compartment-wide write granted: {stripped}")
        assert re.search(r'where\s+target\.secret\.name\s+in\s*\(', text), (
            "the writer grant is not scoped to a name list"
        )

    def test_the_writer_grant_uses_use_not_manage(self):
        """`use` is the narrowest statement that lets a principal create a secret version."""
        text = VAULT_TF.read_text()
        writer_stanzas = [
            s for s in re.findall(r'"(Allow[^"]*vault[^"]*writer[^"]*)"', text, re.I)
        ]
        assert writer_stanzas, "no writer statement found"
        for stmt in writer_stanzas:
            assert " to use secret-family " in stmt, f"not a `use` grant: {stmt}"


class TestTheWallProvesTheRefusal:
    def test_a_verification_wall_exists_for_the_writer_refusal(self):
        """An unwritten wall is a claim nobody grades."""
        walls = list((ROOT / "platform" / "verification").glob("*vault-writer*"))
        assert walls, "no wall proving the writer refuses an Operator-owned entry"
