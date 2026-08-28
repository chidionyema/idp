"""crew#66 point 3, founder 2026-08-28: "Create an immutable Backstage Software Template ...
specifically for External Integrations. This template must hardcode the OIDC/Workload Identity
paths. When the agent is tasked with adding a new tool ... it is forced to inherit the
zero-touch authentication pattern, leaving no room to hallucinate a manual paste step."

So the template's own proof is not "the file exists": it renders the skeleton for every
provider the template offers and puts the rendered output through the no-toil rule from
policy/no-manual-steps.rego. If a future edit puts a credential-carrying sentence into the
skeleton, this test is the thing that catches it.

The renderer here is the ${{ values.x }} substitution Backstage's fetch:template does, not
Backstage itself -- the skeleton uses no loops or conditionals precisely so that a render is
a substitution and can be proved offline. No sockets.
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "backstage" / "templates" / "external-integration"
SKELETON = TPL / "skeleton"
POLICY = ROOT / "policy" / "no-manual-steps.rego"

PROVIDERS = ["oci", "github", "tailscale", "other"]

conftest_only = pytest.mark.skipif(
    shutil.which("conftest") is None,
    reason="conftest is not installed; CI installs the pinned v0.62.0 build",
)


def _auth_mode(provider):
    """The one branch in the template, mirrored: OCI federates, everything else is a tap."""
    if provider == "oci":
        return "workload identity federation (OIDC), never a value a person carries"
    return "a one-tap install or login in the provider, never a value a person carries"


def _render(text, provider):
    values = {
        "provider": provider,
        "name": "acme-widgets",
        "namespace": "acme",
        "authMode": _auth_mode(provider),
    }
    out = text
    for k, v in values.items():
        out = re.sub(r"\$\{\{\s*values\." + k + r"\s*\}\}", v, out)
        # the filter chain the vault-seed stanza uses
        out = re.sub(
            r"\$\{\{\s*values\." + k + r'\s*\|\s*upper\s*\|\s*replace\("-",\s*"_"\)\s*\}\}',
            v.upper().replace("-", "_"),
            out,
        )
    return out


def test_the_template_is_a_backstage_template_and_offers_no_paste_option():
    spec = yaml.safe_load((TPL / "template.yaml").read_text())
    assert spec["kind"] == "Template"
    assert spec["metadata"]["name"] == "external-integration"
    props = spec["spec"]["parameters"][0]["properties"]
    assert props["provider"]["enum"] == PROVIDERS
    for required in ("provider", "name", "namespace"):
        assert required in spec["spec"]["parameters"][0]["required"]
    # Both fixed auth strings live in the template, and the mode is derived from the provider
    # rather than typed by whoever fills the form.
    body = (TPL / "template.yaml").read_text()
    assert "authMode:" in body
    for provider in PROVIDERS:
        assert _auth_mode(provider) in body


def test_the_skeleton_reads_the_estate_vault_through_the_one_cluster_secret_store():
    es = _render((SKELETON / "external-secret.yaml").read_text(), "oci")
    doc = yaml.safe_load(es)
    assert doc["kind"] == "ExternalSecret"
    assert doc["spec"]["secretStoreRef"]["name"] == "estate-vault"
    assert doc["spec"]["secretStoreRef"]["kind"] == "ClusterSecretStore"
    assert doc["spec"]["dataFrom"][0]["extract"]["key"] == "acme-widgets"
    assert doc["metadata"]["namespace"] == "acme"
    # No literal ever: the manifest names an entry, it does not carry a value.
    assert "data" not in doc and "stringData" not in doc
    assert "data" not in doc["spec"] and "stringData" not in doc["spec"]


def test_the_skeleton_carries_the_vault_seed_entry_stanza():
    stanza = yaml.safe_load(_render((SKELETON / "vault-seed-entry.yaml").read_text(), "github"))
    assert stanza["entry"] == "acme-widgets"
    assert stanza["auth"] == _auth_mode("github")
    assert all(s.startswith("SEED_ACME_WIDGETS_") for s in stanza["seed_secrets"]), stanza


@pytest.mark.parametrize("provider", PROVIDERS)
def test_the_docs_auth_section_is_fixed_text_for_the_provider(provider):
    doc = _render((SKELETON / "docs" / "index.md").read_text(), provider)
    assert "## How this integration authenticates" in doc
    assert _auth_mode(provider) in doc
    assert "${{" not in doc, "a placeholder survived the render"
    # The three permitted shapes, and only those.
    assert "Workload identity federation (OIDC)" in doc
    assert "A one-tap install or login" in doc
    assert "A CI-seeded vault entry" in doc
    assert "a value a person carries from one browser tab to another" in doc


@conftest_only
@pytest.mark.parametrize("provider", PROVIDERS)
def test_the_rendered_skeleton_passes_the_no_toil_gate(provider, tmp_path):
    """The template's output is graded by the rule the founder asked for, for every provider
    it offers -- so the Day-0 shape can never render the sentence the gate refuses."""
    for src in sorted(SKELETON.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(SKELETON)
        rendered = _render(src.read_text(), provider)
        # Judged under the path the file lands on, so the policy's own scope applies.
        judged = f"docs/{rel.name}" if rel.suffix == ".md" else f"platform/acme-widgets/{rel.name}"
        payload = tmp_path / f"{provider}-{rel.name}.json"
        payload.write_text(json.dumps({"file_path": judged, "content": rendered.split("\n")}))
        r = subprocess.run(
            ["conftest", "test", "--parser", "json", "-p", str(POLICY), str(payload)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"{rel} rendered for {provider} was refused:\n{r.stdout}"


def test_the_template_is_registered_in_the_catalogue_and_shipped_in_the_image():
    for cfg, target in (
        ("app-config.yaml", "../../templates/external-integration/template.yaml"),
        ("app-config.container.yaml", "/app/templates/external-integration/template.yaml"),
    ):
        text = (ROOT / "backstage" / cfg).read_text()
        assert target in text, f"{cfg} does not register the template"
    # templates/ is copied wholesale into the image, so the second location resolves.
    assert "COPY --chown=node:node templates ./templates" in (ROOT / "backstage" / "Dockerfile").read_text()
