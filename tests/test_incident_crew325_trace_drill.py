"""Incident crew#325, 2026-08-26: the showcase's last step, one routed call visible as a trace at
langfuse.<zone>, had no command that proved it, and the login ForwardAuth in front of every
Langfuse path meant no program could have read a trace back anyway. The rule: the trace drill
exists as a catalogued drill, and Langfuse's key-authenticated public API bypasses the login."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _route(name: str, ns_file: Path) -> dict:
    docs = [d for d in yaml.safe_load_all(ns_file.read_text()) if d]
    return next(d for d in docs if d["kind"] == "HTTPRoute" and d["metadata"]["name"] == name)


def test_langfuse_public_api_bypasses_the_login_forward_auth() -> None:
    f = ROOT / "platform" / "observability" / "httproute.yaml"
    api = _route("langfuse-api", f)
    assert api["metadata"]["annotations"]["idp.estate/auth"] == "langfuse-project-keys"
    paths = [m["path"] for r in api["spec"]["rules"] for m in r["matches"]]
    assert paths == [{"type": "PathPrefix", "value": "/api/public/"}], paths
    assert not any(r.get("filters") for r in api["spec"]["rules"]), "the public API route must carry no ForwardAuth filter"
    assert api["spec"]["rules"][0]["backendRefs"][0]["name"] == "langfuse-web"
    # The browser route keeps the login on every path except the /oauth2/ redirect.
    ui = _route("langfuse", f)
    for r in ui["spec"]["rules"]:
        paths = {m.get("path", {}).get("value") for m in r.get("matches", [])}
        if "/oauth2/" in paths:
            continue
        assert any(x.get("extensionRef", {}).get("name") == "login-forward-auth" for x in r.get("filters", [])), r


def test_trace_drill_is_catalogued_and_reads_keys_only_from_the_vault() -> None:
    drills = {d["name"]: d for d in yaml.safe_load((ROOT / "drills" / "catalogue.yaml").read_text())["drills"]}
    assert "trace-drill" in drills
    assert (ROOT / ".github" / "workflows" / drills["trace-drill"]["workflow"]).exists()
    script = (ROOT / "bin" / "idp-trace-drill").read_text()
    # The three secrets are named, never typed (LAW 46): a key literal would look like sk-... or pk-lf-...
    for name in ("litellm-upstream", "langfuse-init-public-key", "langfuse-init-secret-key"):
        assert name in script, name
    assert not re.search(r"(sk-lf-|pk-lf-|sk-)[A-Za-z0-9]{8,}", script), "a key literal in the drill"


def test_trace_drill_reads_only_the_active_vault_secret() -> None:
    """Run 33006811039: `data[0].id` with no lifecycle filter can pick a same-named secret pending
    deletion. Every vault reader in bin filters ACTIVE, and the miss names key names, never values."""
    script = (ROOT / "bin" / "idp-trace-drill").read_text()
    # crew#66 CP3: the ACTIVE filter moved into the one cloud layer; the drill reads through it and
    # never names a provider CLI (bin/cloud-agnostic-gate refuses one).
    assert '"$IDP/bin/idp-cloud" secret get' in script
    cloud = (ROOT / "bin" / "idp-cloud").read_text()
    assert "lifecycle-state" in cloud and "ACTIVE" in cloud
    assert "keys present:" in script and "keys | join" in script


def test_github_app_installation_step_runs_even_when_a_drill_row_is_red() -> None:
    """Run 32988930880: the rebuild step failed on drill rows, the installation step was skipped, the
    installation id never reached the vault, and ExternalSecret flux-system/github-app could not
    render. The step is gated on always() so a red drill row cannot skip it."""
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "oke-check.yml").read_text())
    steps = [s for j in wf["jobs"].values() for s in j.get("steps", []) if "idp-github-app installation" in s.get("name", "")]
    assert len(steps) == 1, steps
    cond = str(steps[0]["if"])
    assert "always()" in cond and "inputs.mode == 'apply'" in cond, cond


def test_litellm_upstream_is_minted_on_apply_and_never_echoes_a_value() -> None:
    """trace-drill run 33007689530: the ACTIVE vault secret litellm-upstream held a raw value, not the
    JSON envelope ExternalSecret llm/litellm-upstream extracts. The apply job used to re-put it from
    SEED_* secrets; crew#66 root trust (crew#575) replaced that with bin/idp-estate-seed, which mints
    the master key in-process and keeps a well-formed one. The step is still always()-gated on apply,
    no SEED_LITELLM_MASTER_KEY exists anywhere, and no line echoes a key variable."""
    wf_text = (ROOT / ".github" / "workflows" / "oke-check.yml").read_text()
    wf = yaml.safe_load(wf_text)
    steps = [s for j in wf["jobs"].values() for s in j.get("steps", []) if "idp-estate-seed" in s.get("name", "")]
    assert len(steps) == 1, steps
    step = steps[0]
    assert "always()" in str(step["if"]) and "inputs.mode == 'apply'" in str(step["if"])
    assert step["run"].strip() == "bin/idp-estate-seed"
    assert "SEED_LITELLM_MASTER_KEY" not in wf_text and "idp-vault-put litellm-upstream" not in wf_text
    seed = (ROOT / "bin" / "idp-estate-seed").read_text()
    assert "litellm-upstream" in seed and "LITELLM_MASTER_KEY" in seed, "the master key is one PLAN row"
    assert not re.search(r"echo[^\n]*\$\{?(MINIMAX|DEEPSEEK|OPENROUTER|GEMINI|LITELLM)_", seed), "a value echoed"


def test_incident_crew325_trace_drill_default_model_is_a_funded_router_route() -> None:
    # Incident 2026-08-26: the drill asked for the direct `deepseek` key, DeepSeek answered
    # 402 Insufficient Balance, litellm does not fall back on a 4xx, and three runs on main were red
    # while langfuse was already up. Rule: the default model is a model_name in the router config
    # whose upstream goes through OpenRouter, the one funded aggregator (crew#284, idp#257).
    drill = (ROOT / "bin/idp-trace-drill").read_text()
    default = re.search(r'MODEL="\$\{TRACE_DRILL_MODEL:-([a-z0-9_]+)\}"', drill)
    assert default, "bin/idp-trace-drill no longer declares a default model"
    config = yaml.safe_load((ROOT / "platform/llm/config.yaml").read_text())
    routes = {m["model_name"]: m["litellm_params"]["model"] for m in config["model_list"]}
    assert default.group(1) in routes, (default.group(1), sorted(routes))
    assert routes[default.group(1)].startswith("openrouter/"), routes[default.group(1)]
