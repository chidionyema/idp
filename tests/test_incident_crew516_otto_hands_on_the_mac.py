"""crew#516 CP5: Otto (`platform/hermes-agent/`) stays the one pod holding the single Telegram
poller lock, and executes its shell tools on the founder's Mac.

The design is the founder's own locked spec, verbatim (LAW 2 -- this is not a session's paraphrase
of it): crew#66 comment 5451926212, "so we solve the problem once" -- three designs tried and
rejected before it, in order: 5451614620/5451623095 (a hand-pasted reusable Tailscale OAuth-client
auth key -- "a hand-pasted OAuth secret is the laptop-paste habit the estate closed"), 5451900443
point 1 (an interactive login URL the founder taps -- itself superseded, in the same comment, by
this one). Locked spec, Phases 1-3 (Phase 4, the no-toil Rego gate, is a different worker's):

  Phase 1 -- platform/tailscale/: the Tailscale Kubernetes operator (HelmRepository + HelmRelease),
  authenticated by one OAuth client (vault entry `tailscale-operator`, seeded by vault-seed.yml
  exactly like every other provider key), never a value the founder's hands touch after that one
  seeding step.

  Phase 2 -- platform/tailscale/policy.hujson: the tailnet ACL, in git, applied by CI
  (bin/idp-tailscale-policy, oke-check's apply job) -- never an admin-console edit. One ssh rule:
  tag:k8s -> tag:founder-mac, the founder's own Mac user.

  Phase 3 -- hermes-agent: the tailscale sidecar's TS_AUTHKEY is minted from the SAME OAuth client
  (a Tailscale OAuth client secret is itself a valid device auth key -- no second credential, no
  hand-minted key); mac-run (ssh through the sidecar's SOCKS5 proxy, LAW 46 placeholders) is
  unchanged in shape; the executor runs its tool through mac-run only.

Rung 2 properties over the checkout (no network, no cluster):
  - the `tailscale` sidecar in gateway.yaml reads TS_AUTHKEY from a file under a Secret volume,
    never a literal key and never a Kyverno-refused secretKeyRef/env (crew#341);
  - that Secret is composed, by the ExternalSecret's own template, from vault entry
    `tailscale-operator` -- the same one platform/tailscale/'s operator reads -- never a second,
    hand-minted vault entry;
  - `mac-run.yaml`'s script targets `${FOUNDER_MAC_TS_IP}`/`${FOUNDER_MAC_USER}` as unresolved
    placeholders (LAW 46 -- no literal Tailscale CGNAT IP, 100.64.0.0/10), and carries no `-i` key
    flag -- Tailscale SSH authenticates by tailnet node identity, so no ssh keypair of ours is
    generated, mounted or held anywhere in platform/hermes-agent/ or platform/tailscale/;
  - the executor (`estate.yaml`) runs its tool through `mac-run`;
  - the tailnet policy names exactly one ssh rule (LAW 45: the paste-habit and the by-hand-ACL
    mistakes do not come back as a second rule);
  - no README or doc touched by this change contains the toil phrases the founder named twice
    (5451623095, 5451909915) as the mistake to never repeat;
  - (A) the single Telegram poller lock: `gateway.yaml`'s Deployment is replicas 1, Recreate;
  - (B) model-agnostic: no vendor endpoint literal anywhere in the directory, and the model is a
    config key (`models.watch`/`models.work`), not an endpoint;
  - (C) Otto is a founder surface: `backstage/founder/catalog-info.yaml` carries a `founder-otto`
    Component whose links all resolve, with no unsubstituted `${...}`.
"""
import json
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "platform" / "hermes-agent" / "gateway.yaml"
ESTATE = ROOT / "platform" / "hermes-agent" / "estate.yaml"
MAC_RUN = ROOT / "platform" / "hermes-agent" / "mac-run.yaml"
TAILSCALE = ROOT / "platform" / "hermes-agent" / "tailscale.yaml"
KUSTOMIZATION = ROOT / "platform" / "hermes-agent" / "kustomization.yaml"
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"
HERMES_AGENT_DIR = ROOT / "platform" / "hermes-agent"

OPERATOR_DIR = ROOT / "platform" / "tailscale"
OPERATOR = OPERATOR_DIR / "operator.yaml"
OPERATOR_SECRET = OPERATOR_DIR / "external-secret.yaml"
POLICY = OPERATOR_DIR / "policy.hujson"
OPERATOR_KUSTOMIZATION = OPERATOR_DIR / "kustomization.yaml"

VAULT_SEED = ROOT / ".github" / "workflows" / "vault-seed.yml"
OKE_CHECK = ROOT / ".github" / "workflows" / "oke-check.yml"
POLICY_SCRIPT = ROOT / "bin" / "idp-tailscale-policy"

# Tailscale's own CGNAT range for tailnet addresses (kb/1015/100.x-addresses): 100.64.0.0/10.
TAILNET_IP_RE = re.compile(r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
# LAW 45: the rejected sentence of 5451623095/5451909915, never again in a README or doc.
TOIL_PHRASES = ("paste this", "manually create", "founder must", "click here", "log into the web interface", "paste it into")
TOUCHED_DOCS = [
    ROOT / "platform" / "hermes-agent" / "README.md",
    ROOT / "docs" / "founder" / "otto-on-the-mac.md",
    ROOT / "docs" / "founder" / "mac-remote-desk" / "README.md",
]


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _gateway_deployment():
    return next(d for d in _docs(GATEWAY) if d["kind"] == "Deployment")


def _gateway_containers():
    return _gateway_deployment()["spec"]["template"]["spec"]["containers"]


# ---------------------------------------------------------------------------
# Phase 1: the operator, authenticated by one OAuth client, seeded like every other provider key.
# ---------------------------------------------------------------------------

def test_the_operator_helmrelease_reads_its_oauth_client_from_a_secret_not_a_literal():
    """The chart has no *FromSecret values field (verified live, `helm show values
    tailscale-operator --version 1.102.3`, 2026-08-28): leaving `oauth` unset in values makes it
    fall back to reading the pre-created `operator-oauth` Secret -- so the HelmRelease must name
    no oauth.clientId/clientSecret value at all, literal or otherwise."""
    docs = _docs(OPERATOR)
    repo = next(d for d in docs if d["kind"] == "HelmRepository")
    assert repo["spec"]["url"] == "https://pkgs.tailscale.com/helmcharts"
    rel = next(d for d in docs if d["kind"] == "HelmRelease")
    assert "oauth" not in rel["spec"]["values"]
    raw = OPERATOR.read_text()
    assert "clientId:" not in raw and "clientSecret:" not in raw


def test_the_operator_secret_comes_from_the_one_vault_entry():
    es = next(d for d in _docs(OPERATOR_SECRET) if d["kind"] == "ExternalSecret")
    assert es["metadata"]["name"] == "tailscale-operator-secret" and es["metadata"]["namespace"] == "tailscale"
    assert es["spec"]["target"]["name"] == "operator-oauth"
    keys = {e["secretKey"]: e["remoteRef"] for e in es["spec"]["data"]}
    assert keys["client_id"] == {"key": "tailscale-operator", "property": "client_id"}
    assert keys["client_secret"] == {"key": "tailscale-operator", "property": "client_secret"}


def test_operator_kustomization_carries_its_resources():
    ks = yaml.safe_load(OPERATOR_KUSTOMIZATION.read_text())
    assert set(ks["resources"]) >= {"namespace.yaml", "external-secret.yaml", "operator.yaml"}
    assert "policy.hujson" not in ks["resources"], "not a Kubernetes manifest; applied by bin/idp-tailscale-policy"


def test_flux_row_wires_the_operator_after_secret_store():
    rows = [d for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text()) if d and d.get("kind") == "Kustomization" and d["metadata"]["name"] == "tailscale"]
    (row,) = rows
    assert row["spec"]["path"] == "./platform/tailscale"
    assert {"name": "secret-store"} in row["spec"]["dependsOn"]
    assert row["spec"]["healthChecks"] == [{"apiVersion": "apps/v1", "kind": "Deployment", "name": "tailscale-operator", "namespace": "tailscale"}]


def test_vault_seed_carries_the_one_oauth_client_entry_never_a_reusable_key():
    wf = yaml.safe_load(VAULT_SEED.read_text())
    on_key = "on" if "on" in wf else True  # PyYAML 1.1 resolves the bare `on:` scalar to bool True
    options = wf[on_key]["workflow_dispatch"]["inputs"]["entry"]["options"]
    assert "tailscale-operator" in options
    assert "hermes-agent-tailscale" not in options, "the design that entry belonged to (5451614620) was rejected"
    raw = VAULT_SEED.read_text()
    # crew#66 root trust (5453747447, crew#576): the OAuth client is born by bin/idp-bootstrap-tailscale,
    # which writes the vault itself; vault-seed REFUSES the entry instead of pasting it from a GitHub secret.
    assert "put tailscale-operator client_id=" not in raw, "the pasted-secret path is gone (crew#66 root trust)"
    assert "born by bin/idp-bootstrap-tailscale, never seeded by hand" in raw
    assert "TAILSCALE_OAUTH_CLIENT_SECRET" not in raw, "no GitHub secret holds the client secret"
    assert "SEED_TS_AUTHKEY" not in raw, "the reusable-key seeding path (5451614620) is gone, not just renamed"


# ---------------------------------------------------------------------------
# Phase 2: the tailnet policy, in git, one ssh rule, applied by CI.
# ---------------------------------------------------------------------------

def _policy_hujson():
    # hujson allows comments and trailing commas; strip both for a plain json.loads.
    raw = POLICY.read_text()
    no_comments = re.sub(r"//.*", "", raw)
    no_trailing_commas = re.sub(r",(\s*[}\]])", r"\1", no_comments)
    return json.loads(no_trailing_commas)


def test_policy_carries_exactly_one_ssh_rule_tag_k8s_to_tag_founder_mac():
    pol = _policy_hujson()
    assert len(pol["ssh"]) == 1, "LAW 45: the paste/by-hand-ACL mistake does not come back as a second rule"
    rule = pol["ssh"][0]
    assert rule["action"] == "check"
    assert rule["src"] == ["tag:k8s"] and rule["dst"] == ["tag:founder-mac"]
    assert rule["users"] == ["${FOUNDER_MAC_USER}"], "LAW 46: no literal founder username in git"


def test_policy_acl_and_tag_owners_match_the_locked_spec():
    pol = _policy_hujson()
    assert {"tag:k8s", "tag:founder-mac"} <= set(pol["tagOwners"])
    assert pol["acls"] == [{"action": "accept", "src": ["tag:k8s"], "dst": ["tag:founder-mac:22"]}]


def test_tailscale_policy_script_exists_executable_and_reads_the_estate_config():
    assert POLICY_SCRIPT.exists() and (POLICY_SCRIPT.stat().st_mode & 0o111), "bin/idp-tailscale-policy must be executable"
    raw = POLICY_SCRIPT.read_text()
    assert "FOUNDER_MAC_USER" in raw and "estate-config.yaml" in raw
    assert "api.tailscale.com/api/v2/tailnet" in raw


def test_oke_check_apply_runs_the_policy_script_never_a_laptop():
    raw = OKE_CHECK.read_text()
    assert "bin/idp-tailscale-policy apply" in raw
    step = raw.split("bin/idp-tailscale-policy apply (crew#516 CP5)")[1][:400]
    assert "inputs.mode == 'apply'" in step
    assert "bin/idp-tailscale-policy apply" in step


def test_mac_checklist_advertises_the_policy_tag_and_names_no_admin_console_step():
    raw = (ROOT / "docs" / "founder" / "mac-remote-desk" / "README.md").read_text()
    assert "tailscale up --ssh --advertise-tags=tag:founder-mac" in raw
    assert "admin console" not in raw.lower() or "no admin-console edit" in raw.lower() or "no ACL step" in raw


# ---------------------------------------------------------------------------
# the tailscale sidecar (Phase 3): TS_AUTHKEY is a file, never a literal or secretKeyRef, minted
# from the SAME OAuth client Phase 1 reads.
# ---------------------------------------------------------------------------

def test_tailscale_sidecar_present_in_the_gateway_pod():
    names = {c["name"] for c in _gateway_containers()}
    assert "tailscale" in names
    assert "gateway" in names


def test_ts_authkey_is_a_file_never_a_literal_or_a_secretkeyref():
    ts = next(c for c in _gateway_containers() if c["name"] == "tailscale")
    env = {e["name"]: e for e in ts["env"]}
    authkey = env["TS_AUTHKEY"]
    assert "valueFrom" not in authkey, "Kyverno secrets-not-from-env-vars (crew#341) refuses secretKeyRef"
    assert authkey["value"].startswith("file:")
    assert "tskey-" not in authkey["value"], "no literal Tailscale key in this file"


def test_the_authkey_file_is_mounted_from_the_hermes_agent_tailscale_secret():
    ts = next(c for c in _gateway_containers() if c["name"] == "tailscale")
    mounts = {m["mountPath"]: m for m in ts["volumeMounts"]}
    mount_path = next(p for p in mounts if "hermes-agent-tailscale" in p)
    vol_name = mounts[mount_path]["name"]
    volumes = {v["name"]: v for v in _gateway_deployment()["spec"]["template"]["spec"]["volumes"]}
    assert volumes[vol_name]["secret"]["secretName"] == "hermes-agent-tailscale"


def test_tailscale_container_never_privileged_or_root():
    ts = next(c for c in _gateway_containers() if c["name"] == "tailscale")
    sc = ts["securityContext"]
    assert sc["privileged"] is False
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["runAsNonRoot"] is True
    assert sc["capabilities"]["drop"] == ["ALL"]


def test_the_sidecars_own_secret_is_composed_from_the_one_oauth_client_not_a_second_entry():
    es = next(d for d in _docs(TAILSCALE) if d["kind"] == "ExternalSecret")
    assert es["metadata"]["name"] == "hermes-agent-tailscale"
    keyed = {e["secretKey"]: e["remoteRef"] for e in es["spec"]["data"]}
    assert keyed["client_secret"] == {"key": "tailscale-operator", "property": "client_secret"}, "same vault entry Phase 1 reads, not a hand-minted one"
    template = es["spec"]["target"]["template"]["data"]["TS_AUTHKEY"]
    assert "{{ .client_secret }}" in template and "ephemeral=false" in template and "preauthorized=true" in template


# ---------------------------------------------------------------------------
# mac-run: no literal Tailscale IP, no ssh key, executable.
# ---------------------------------------------------------------------------

def test_mac_run_script_carries_the_placeholders_not_a_literal_ip():
    docs = _docs(MAC_RUN)
    cm = next(d for d in docs if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "hermes-agent-mac-run")
    script = cm["data"]["mac-run"]
    assert "${FOUNDER_MAC_TS_IP}" in script
    assert "${FOUNDER_MAC_USER}" in script
    assert not TAILNET_IP_RE.search(script), "a literal tailnet (100.64.0.0/10) address in the script"


def test_mac_run_has_no_ssh_key_flag_and_no_key_is_mounted():
    docs = _docs(MAC_RUN)
    cm = next(d for d in docs if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "hermes-agent-mac-run")
    script = cm["data"]["mac-run"]
    assert " -i " not in script and not script.strip().endswith("-i"), "Tailscale SSH needs no key flag"
    assert "id_rsa" not in script and "id_ed25519" not in script and "ssh-keygen" not in script
    for f in (GATEWAY, MAC_RUN, TAILSCALE, ESTATE, OPERATOR, OPERATOR_SECRET, POLICY, POLICY_SCRIPT):
        text = f.read_text()
        assert "ssh-keygen" not in text
        assert "authorized_keys" not in text
        assert "-----BEGIN" not in text


def test_mac_run_is_mounted_executable_at_usr_local_bin():
    volumes = {v["name"]: v for v in _gateway_deployment()["spec"]["template"]["spec"]["volumes"]}
    mac_run_vol = volumes["mac-run"]
    assert mac_run_vol["configMap"]["name"] == "hermes-agent-mac-run"
    assert mac_run_vol["configMap"]["defaultMode"] == 0o755
    gw = next(c for c in _gateway_containers() if c["name"] == "gateway")
    mount = next(m for m in gw["volumeMounts"] if m["name"] == "mac-run")
    assert mount["mountPath"] == "/usr/local/bin/mac-run"


def test_founder_mac_user_and_ip_are_declared_estate_config_keys():
    """Strict Flux envsubst (tests/test_incident_crew284_flux_envsubst_strict_variable.py) needs
    both keys to exist in a ConfigMap the hermes-agent Kustomization substitutes from."""
    cfg = yaml.safe_load((ROOT / "clusters" / "oke" / "estate-config.yaml").read_text())
    assert "FOUNDER_MAC_USER" in cfg["data"]
    assert "FOUNDER_MAC_TS_IP" in cfg["data"]


def test_kustomization_carries_the_new_resources():
    ks = yaml.safe_load(KUSTOMIZATION.read_text())
    assert set(ks["resources"]) >= {"gateway.yaml", "estate.yaml", "mac-run.yaml", "tailscale.yaml"}


# ---------------------------------------------------------------------------
# LAW 45: the paste-habit mistake ends as a guard, not a repeated sentence.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("directory", [HERMES_AGENT_DIR, OPERATOR_DIR])
def test_no_authkey_literal_or_ssh_keypair_anywhere_in_the_two_directories(directory):
    # .md prose is allowed to *name* authorized_keys/ssh-keygen while stating none is used (e.g.
    # "node identity, no keypair, no `authorized_keys`") -- README.md is scanned separately below
    # for the actual banned toil phrases. Manifests, scripts and the policy file may never contain
    # any of these strings at all: there is no legitimate reason for one to appear there.
    for f in directory.rglob("*"):
        if f.is_file() and (f.suffix in (".yaml", ".yml", ".hujson") or f.name.startswith("idp-")):
            text = f.read_text()
            assert not re.search(r"tskey-(client|auth)-[A-Za-z0-9]", text), f"{f}: a live-shaped Tailscale key"
            assert "authorized_keys" not in text, f
            assert "ssh-keygen" not in text, f
            assert "-----BEGIN" not in text, f
        elif f.is_file() and f.suffix == ".md":
            text = f.read_text()
            assert not re.search(r"tskey-(client|auth)-[A-Za-z0-9]", text), f"{f}: a live-shaped Tailscale key"
            assert "-----BEGIN" not in text, f


@pytest.mark.parametrize("doc", TOUCHED_DOCS)
def test_no_toil_phrase_in_a_touched_readme_or_doc(doc):
    text = doc.read_text().lower()
    for phrase in TOIL_PHRASES:
        assert phrase not in text, f"{doc}: {phrase!r} is the mistake 5451623095/5451909915 named"


# ---------------------------------------------------------------------------
# the executor runs through mac-run.
# ---------------------------------------------------------------------------

def test_executor_runs_through_mac_run():
    cfg = yaml.safe_load(ESTATE.read_text())
    doc = yaml.safe_load(cfg["data"]["estate.yaml"])
    claude_cmd = doc["dispatch"]["runtimes"]["claude"]
    assert claude_cmd[0] == "mac-run"


def test_executor_keeps_the_existing_allowed_tools():
    cfg = yaml.safe_load(ESTATE.read_text())
    doc = yaml.safe_load(cfg["data"]["estate.yaml"])
    claude_cmd = doc["dispatch"]["runtimes"]["claude"]
    assert "Bash(git *) Bash(gh *)" in claude_cmd


def test_no_ssh_flag_or_key_in_the_executor_line():
    cfg = yaml.safe_load(ESTATE.read_text())
    doc = yaml.safe_load(cfg["data"]["estate.yaml"])
    claude_cmd = doc["dispatch"]["runtimes"]["claude"]
    assert "ssh" not in claude_cmd, "ssh is mac-run's job, not the executor line's"


# ---------------------------------------------------------------------------
# (A) single Telegram poller lock.
# ---------------------------------------------------------------------------

def test_hermes_agent_gateway_is_one_replica_recreate():
    dep = _gateway_deployment()
    assert dep["metadata"]["name"] == "hermes-agent-gateway"
    assert dep["spec"]["replicas"] == 1
    assert dep["spec"]["strategy"]["type"] == "Recreate"


# ---------------------------------------------------------------------------
# (B) model-agnostic: no vendor endpoint literal, model is a config key.
# ---------------------------------------------------------------------------

VENDOR_ENDPOINTS = ("api.anthropic.com", "api.openai.com")


def test_no_vendor_endpoint_literal_in_hermes_agent_manifests():
    for f in (ROOT / "platform" / "hermes-agent").glob("*.yaml"):
        text = f.read_text()
        for v in VENDOR_ENDPOINTS:
            assert v not in text, f"{f}: {v}"


def test_the_model_is_a_config_key_not_an_inline_endpoint():
    """hermes-v2's own config.yaml (a separate repo) is what actually routes model calls through
    the estate's one LiteLLM router (platform/llm/config.yaml) as of CP4; this repo's estate.yaml
    only ever names a model key, never an endpoint, so there is nothing here to route twice."""
    cfg = yaml.safe_load(ESTATE.read_text())
    doc = yaml.safe_load(cfg["data"]["estate.yaml"])
    models = doc["models"]
    assert set(models) == {"watch", "work"}
    for v in models.values():
        assert not v.startswith("http"), f"a model value must be a name, not an endpoint: {v}"


def test_the_estate_router_config_exists_and_is_the_only_one():
    """LAW 43: don't build a second router. platform/llm/config.yaml is the estate's one LiteLLM
    router and fallback config; this directory does not carry a competing one."""
    router = ROOT / "platform" / "llm" / "config.yaml"
    assert router.exists()
    assert not (ROOT / "platform" / "hermes-agent" / "config.yaml").exists()


# ---------------------------------------------------------------------------
# (C) founder surface.
# ---------------------------------------------------------------------------

def test_founder_otto_surface_exists_and_carries_no_unresolved_link():
    docs = _docs(FOUNDER)
    otto = next(d for d in docs if d["metadata"]["name"] == "founder-otto")
    assert otto["kind"] == "Component" and otto["spec"]["type"] == "founder-surface"
    assert otto["metadata"]["description"].strip()
    ann = otto["metadata"]["annotations"]
    assert ann["backstage.io/kubernetes-namespace"] == "hermes-agent"
    assert ann["backstage.io/kubernetes-id"] == "hermes-agent-gateway"
    links = otto["metadata"]["links"]
    assert links
    for link in links:
        assert "${" not in link["url"], link["url"]
        assert re.match(r"https?://", link["url"])


def test_founder_otto_link_urls_are_unique_in_the_file():
    """tests/test_incident_crew401_every_founder_surface_is_in_the_catalogue.py refuses a
    duplicate link URL anywhere in the file; check it here too so this test fails on its own."""
    docs = _docs(FOUNDER)
    all_urls = [l["url"] for d in docs if d.get("kind") == "Component" for l in d["metadata"].get("links", [])]
    assert len(all_urls) == len(set(all_urls)), "a link URL is reused across two Components"
