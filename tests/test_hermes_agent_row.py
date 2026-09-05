"""The `hermes-agent` Flux row (crew#516 CP4): The Architect (Telegram + a2a gateway) on OKE.

Rung 2 (properties over the manifests) and rung 4 (incident: idp#365's standby kept HERMES_HOME
on an emptyDir under a read-only root, so every restart lost every session, and its secrets came
by envFrom, which Kyverno refuses at admission, crew#284/crew#341). The rules under test: the
state lives on a volume that outlives the pod; the build is the image, not a ConfigMap copy of
config.yaml; secrets are files the container exports; the image tag is moved by Flux; the vault
entry the pod reads is the one oke-check seeds. Proved both ways with a mutated copy.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "platform" / "hermes-agent"


def _docs():
    return list(yaml.safe_load_all((DIR / "gateway.yaml").read_text()))


def _one(docs, kind):
    found = [d for d in docs if d and d.get("kind") == kind]
    assert len(found) == 1, (kind, len(found))
    return found[0]


def _container(docs):
    dep = _one(docs, "Deployment")
    spec = dep["spec"]["template"]["spec"]
    # crew#516 CP5 added a `tailscale` sidecar (platform/hermes-agent/tailscale.yaml); this helper
    # is about the `gateway` container specifically.
    (c,) = [c for c in spec["containers"] if c["name"] == "gateway"]
    return spec, c


def state_outlives_the_pod(docs) -> bool:
    spec, c = _container(docs)
    home = {e["name"]: e.get("value") for e in c["env"]}["HERMES_HOME"]
    mounts = {m["mountPath"]: m["name"] for m in c["volumeMounts"]}
    vols = {v["name"]: v for v in spec["volumes"]}
    vol = vols.get(mounts.get(home, ""), {})
    return (
        "persistentVolumeClaim" in vol
        and vol["persistentVolumeClaim"]["claimName"]
        == _one(docs, "PersistentVolumeClaim")["metadata"]["name"]
    )


def test_hermes_home_is_a_persistent_volume():
    assert state_outlives_the_pod(_docs())


def test_an_emptydir_home_is_refused():
    docs = _docs()
    spec, _ = _container(docs)
    for v in spec["volumes"]:
        if "persistentVolumeClaim" in v:
            v.pop("persistentVolumeClaim")
            v["emptyDir"] = {}
    assert not state_outlives_the_pod(docs)


def test_secrets_are_files_the_container_exports_never_pod_env():
    docs = _docs()
    spec, c = _container(docs)
    assert "envFrom" not in c
    assert not [e for e in c["env"] if "valueFrom" in e]
    env_dir = {e["name"]: e.get("value") for e in c["env"]}["HERMES_ENV_DIR"]
    mounts = {m["mountPath"]: m for m in c["volumeMounts"]}
    assert mounts[env_dir]["readOnly"] is True
    vols = {v["name"]: v for v in spec["volumes"]}
    # crew#516 CP4: the env dir is a projected volume -- the vault entry plus the in-cluster a2a token.
    secrets = [
        s["secret"]["name"]
        for s in vols[mounts[env_dir]["name"]]["projected"]["sources"]
    ]
    ess = {
        d["metadata"]["name"]: d
        for d in docs
        if d and d.get("kind") == "ExternalSecret"
    }
    # crew#561 CP3: plus the estate MCP key (mcp-key.yaml), optional so a vault miss never blocks the gateway.
    mcp = {
        d["metadata"]["name"]: d
        for f in ("mcp-key.yaml", "langfuse-key.yaml")
        for d in yaml.safe_load_all((DIR / f).read_text())
        if d and d.get("kind") == "ExternalSecret"
    }
    ess.update(mcp)
    # Founder 2026-09-05: hermes-agent-webhook is gone with the Telegram door. This pod
    # re-registered the bot's webhook onto its own dead /telegram path on every restart and
    # took the bot away from otto-gateway, the estate's one ingress.
    assert secrets == [
        "hermes-agent-env",
        "hermes-agent-a2a",
        "hermes-agent-mcp",
        "hermes-agent-langfuse",
    ]
    # idp#852: plus the App-key ExternalSecret that feeds the GithubAccessToken generator; it
    # feeds the generator, never the env dir.
    assert set(ess) == set(secrets) | {"hermes-agent-github-app-pem"}
    assert ess["hermes-agent-env"]["spec"]["target"]["name"] == "hermes-agent-env"
    assert ess["hermes-agent-env"]["spec"]["dataFrom"][0] == {
        "extract": {"key": "hermes-agent-env"},
        "rewrite": [
            {"regexp": {"source": "^TELEGRAM_(.*)$", "target": "DISABLED_TELEGRAM_$1"}}
        ],
    }


def test_the_build_is_the_image_not_a_configmap_copy():
    docs = _docs()
    assert not [d for d in docs if d and d.get("kind") == "ConfigMap"], (
        "config.yaml rides in the image (hermes-v2 Dockerfile), never a hand-synced copy here"
    )
    spec, c = _container(docs)
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    assert spec["securityContext"]["runAsNonRoot"] is True


def test_one_process_holds_the_token():
    dep = _one(_docs(), "Deployment")
    assert dep["spec"]["replicas"] == 1
    assert dep["spec"]["strategy"] == {"type": "Recreate"}


def test_the_tag_is_moved_by_flux_image_automation():
    kust = yaml.safe_load((DIR / "kustomization.yaml").read_text())
    (img,) = kust["images"]
    assert img["name"] == "ghcr.io/chidionyema/hermes-agent"
    raw = (DIR / "kustomization.yaml").read_text()
    assert re.search(
        r'newTag: \S+ # \{"\$imagepolicy": "flux-system:hermes-agent:tag"\}', raw
    )
    pol = [
        d
        for d in yaml.safe_load_all(
            (ROOT / "platform/image-automation/hermes-agent.yaml").read_text()
        )
        if d.get("kind") == "ImagePolicy"
    ]
    assert (
        pol
        and pol[0]["spec"]["filterTags"]["pattern"]
        == "^main-(?P<run>[0-9]+)-[0-9a-f]{40}$"
    )
    ia = yaml.safe_load(
        (ROOT / "platform/image-automation/kustomization.yaml").read_text()
    )
    assert "hermes-agent.yaml" in ia["resources"]


def test_flux_row_waits_on_the_deployment_and_the_vault():
    rows = [
        d
        for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text())
        if d
        and d.get("kind") == "Kustomization"
        and d["metadata"]["name"] == "hermes-agent"
    ]
    (row,) = rows
    assert row["spec"]["path"] == "./platform/hermes-agent"
    assert {"name": "secret-store"} in row["spec"]["dependsOn"]
    assert row["spec"]["healthChecks"] == [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "name": "hermes-agent-gateway",
            "namespace": "hermes-agent",
        }
    ]


def test_oke_check_seeds_the_entry_the_pod_reads():
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    steps = [
        s
        for s in wf["jobs"]["check"]["steps"]
        if "hermes-agent-env" in s.get("name", "")
    ]
    (step,) = steps
    assert "bin/idp-vault-put --merge hermes-agent-env" in step["run"]
    # crew#66 root trust (crew#576, #577, #579): only configuration rides this step; every credential
    # the gateway reads is born by a bootstrapper and lands in the same entry with --merge.
    for key in (
        "TELEGRAM_ALLOWED_USER_IDS",
        "TELEGRAM_ALLOWED_USERS",
        "TELEGRAM_HOME_CHANNEL",
        "HERMES_AUTH_JSON",
    ):
        assert key in step["env"] and key in step["run"], key
    for key in (
        "TELEGRAM_BOT_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "LITELLM_API_KEY",
        "GITHUB_TOKEN",
        "EXA_API_KEY",
    ):
        assert key not in step["env"], (
            f"{key} is born by a bootstrapper, never pasted (crew#66 root trust)"
        )
    registry = (ROOT / "platform/vendors/consoles.yaml").read_text()
    assert "TELEGRAM_BOT_TOKEN" in registry and "hermes-agent-env" in registry, (
        "the bot token has a vendor row"
    )
    assert "hermes-agent-env" in (ROOT / "bin/idp-estate-seed").read_text(), (
        "LITELLM_API_KEY has an estate-seed row"
    )
    consumers = json.loads(
        (ROOT / "platform/github-app/token-consumers.json").read_text()
    )["consumers"]
    assert not [c for c in consumers if c.get("entry") == "hermes-agent-env"], (
        "GITHUB_TOKEN is minted in-cluster by the GithubAccessToken generator (idp#852 "
        "deleted the hourly refresh lane and the token died with it), never by a workflow"
    )


@pytest.mark.skipif(
    subprocess.run(["which", "kustomize"], capture_output=True).returncode != 0,
    reason="kustomize not on PATH",
)
def test_the_row_renders():
    out = subprocess.run(
        ["kustomize", "build", str(DIR)], capture_output=True, text=True, check=True
    ).stdout
    assert (
        "claimName: hermes-agent-data" in out
        and "image: ghcr.io/chidionyema/hermes-agent:" in out
    )


def test_incident_apply_dispatch_is_not_displaced_by_pull_request_pushes():
    """Runs 33089051005 and 33091098027: the queued apply dispatch was cancelled by later PR pushes
    because GitHub keeps one pending run per concurrency group. Dispatches get their own group."""
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    assert wf["concurrency"]["group"] == "oke-check-${{ github.event_name }}"
    assert wf["concurrency"]["cancel-in-progress"] is False


# "the pod rolls when the vault entry changes" was graded here, on this one Deployment. It is a
# property of every workload, not of Otto, and it is graded as one in
# tests/test_incident_crew684_every_workload_restarts_when_its_config_changes.py.


def github_token_is_minted_in_cluster(docs) -> bool:
    """idp#852: the hourly off-cluster re-mint rode verify-drill.yml and died when the drill was
    deleted (founder 2026-08-30: "otto is infra ... not afterthought"). Rung 2: Otto's
    GITHUB_TOKEN is a property of the row itself -- an in-cluster GithubAccessToken generator
    feeding the env ExternalSecret inside the token's 60m life -- never a workflow side effect."""
    gens = [d for d in docs if d and d.get("kind") == "GithubAccessToken"]
    if len(gens) != 1:
        return False
    es = [
        d
        for d in docs
        if d
        and d.get("kind") == "ExternalSecret"
        and d["metadata"]["name"] == "hermes-agent-env"
    ][0]
    m = re.fullmatch(r"(\d+)m", es["spec"]["refreshInterval"])
    if not m or int(m.group(1)) >= 60:
        return False
    last = es["spec"]["dataFrom"][-1]
    # the mint is the LAST dataFrom entry: entries merge in the order listed, so the fresh token
    # wins over any stale GITHUB_TOKEN field the vault entry still carries
    return (
        last.get("sourceRef", {}).get("generatorRef", {}).get("kind")
        == "GithubAccessToken"
        and last["sourceRef"]["generatorRef"]["name"] == gens[0]["metadata"]["name"]
        and last["rewrite"] == [{"transform": {"template": "GITHUB_TOKEN"}}]
    )


def test_github_token_is_minted_in_cluster_day0():
    docs = _docs()
    assert github_token_is_minted_in_cluster(docs)
    gen = [d for d in docs if d and d.get("kind") == "GithubAccessToken"][0]
    lanes = json.loads((ROOT / "platform/github-app/lanes.json").read_text())
    assert gen["spec"]["permissions"] == lanes["application-engineer"], (
        "the generator holds exactly the application-engineer lane, no widening"
    )
    # LAW 46: the identifiers ride strict envsubst from the flux-system/github-app Secret
    assert gen["spec"]["appID"] == "${githubAppIDQuoted}"
    assert gen["spec"]["installID"] == "${githubAppInstallationIDQuoted}"
    pem = [
        d
        for d in docs
        if d
        and d.get("kind") == "ExternalSecret"
        and d["metadata"]["name"] == "hermes-agent-github-app-pem"
    ][0]
    assert pem["spec"]["target"]["template"]["data"]["key"] == "{{ .pem_b64 | b64dec }}"
    assert gen["spec"]["auth"]["privateKey"]["secretRef"] == {
        "name": pem["spec"]["target"]["name"],
        "key": "key",
    }


def test_a_mint_slower_than_the_tokens_life_is_refused():
    docs = _docs()
    es = [
        d
        for d in docs
        if d
        and d.get("kind") == "ExternalSecret"
        and d["metadata"]["name"] == "hermes-agent-env"
    ][0]
    es["spec"]["refreshInterval"] = "2h"
    assert not github_token_is_minted_in_cluster(docs)


def test_the_flux_rows_define_the_generators_substitution_vars():
    rows = [
        d
        for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text())
        if d
        and d.get("kind") == "Kustomization"
        and d["metadata"]["name"] in ("hermes-agent", "mcp")
    ]
    assert len(rows) == 2
    for row in rows:
        name = row["metadata"]["name"]
        assert {"kind": "Secret", "name": "github-app"} in row["spec"]["postBuild"][
            "substituteFrom"
        ], name
        # strict envsubst: an undefined ${githubAppIDQuoted} fails the row, so it waits on the Secret
        assert {"name": "alerts-github"} in row["spec"]["dependsOn"], name


def test_this_pod_can_never_register_the_telegram_webhook_again():
    """Founder 2026-09-05, both bots silent: this pod called setWebhook on every start and pointed
    @Ottototbot at its own /telegram door, which has been dead since the adapter hung at
    "Connecting to Telegram (attempt 1/8)". The fork enables the Telegram platform only when
    TELEGRAM_BOT_TOKEN is in the environment (gateway/config.py), so renaming every TELEGRAM_*
    key on the way out of the vault is what makes the registration impossible -- not a comment."""
    docs = _docs()
    spec, c = _container(docs)
    env = {e["name"] for e in c["env"]}
    assert not [n for n in env if n.startswith("TELEGRAM_")], sorted(env)
    assert not [p for p in c.get("ports", []) if p.get("name") == "telegram"]
    svc = _one(docs, "Service")
    assert [p["name"] for p in svc["spec"]["ports"]] == ["a2a"]
    assert not (DIR / "httproute.yaml").exists(), (
        "the /telegram door is otto-gateway's, and only otto-gateway's"
    )
    assert "httproute.yaml" not in (DIR / "kustomization.yaml").read_text()
