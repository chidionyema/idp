"""crew#516 CP4, receipt run 33116314460 (2026-08-27 21:00Z): the gateway pod ran Telegram but

  1. "Startup probe failed: ... 9900: connect: connection refused" x151 -- the a2a adapter binds
     127.0.0.1 unless A2A_BEARER_TOKEN (or A2A_PEER_TOKENS) is set and A2A_HOST asks for more
     (hermes-agent plugins/platforms/a2a/security.py resolve_bind_host); the kubelet probes the pod
     IP, so the pod was killed every five minutes (BackOff x49 on the previous ReplicaSet);
  2. "Unauthorized user: <founder> on telegram" -- the vault entry carried TELEGRAM_ALLOWED_USER_IDS
     (the cockpit's name) and hermes-agent reads TELEGRAM_ALLOWED_USERS (gateway/run.py).

The row now generates the a2a token in the cluster (ESO Password generator, never seeded, never in
git), projects it into the env dir the entrypoint exports, binds a2a on 0.0.0.0, and seeds the
allow-list under both names."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = list(yaml.safe_load_all((ROOT / "platform/hermes-agent/gateway.yaml").read_text()))


def by(kind, name):
    (d,) = [d for d in DOCS if d and d["kind"] == kind and d["metadata"]["name"] == name]
    return d


def test_a2a_token_is_generated_in_cluster_and_projected_into_the_env_dir():
    gen = by("Password", "hermes-agent-a2a")
    assert gen["apiVersion"].startswith("generators.external-secrets.io/") and gen["spec"]["length"] >= 32
    es = by("ExternalSecret", "hermes-agent-a2a")
    (src,) = es["spec"]["dataFrom"]
    assert src["sourceRef"]["generatorRef"] == {"apiVersion": gen["apiVersion"], "kind": "Password", "name": "hermes-agent-a2a"}
    assert src["rewrite"] == [{"transform": {"template": "A2A_BEARER_TOKEN"}}]
    assert str(es["spec"]["refreshInterval"]) == "0", "a rotation under a running gateway is a deliberate change, not a timer"
    dep = by("Deployment", "hermes-agent-gateway")
    spec = dep["spec"]["template"]["spec"]
    (env_vol,) = [v for v in spec["volumes"] if v["name"] == "env"]
    names = [s["secret"]["name"] for s in env_vol["projected"]["sources"]]
    assert names == ["hermes-agent-env", "hermes-agent-a2a"]
    # crew#516 CP5 added a `tailscale` sidecar (platform/hermes-agent/tailscale.yaml,
    # tests/test_incident_crew516_otto_hands_on_the_mac.py); this test is about the `gateway`
    # container specifically, so name it rather than assume the pod holds exactly one container.
    (c,) = [c for c in spec["containers"] if c["name"] == "gateway"]
    env = {e["name"]: e.get("value") for e in c["env"]}
    assert env["A2A_HOST"] == "0.0.0.0" and env["HERMES_ENV_DIR"] == "/run/secrets/hermes-agent-env"
    (m,) = [m for m in c["volumeMounts"] if m["name"] == "env"]
    assert m["mountPath"] == env["HERMES_ENV_DIR"]
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert c[probe]["httpGet"] == {"path": "/.well-known/agent-card.json", "port": "a2a"}
    assert "hermes-agent-a2a" in dep["metadata"]["annotations"]["secret.reloader.stakater.com/reload"]


def test_no_token_or_allowlist_value_is_in_git():
    text = (ROOT / "platform/hermes-agent/gateway.yaml").read_text() + (ROOT / ".github/workflows/oke-check.yml").read_text()
    assert "A2A_BEARER_TOKEN:" not in text.replace("template: \"A2A_BEARER_TOKEN\"", "")
    import re
    assert not re.search(r"TELEGRAM_ALLOWED_USERS?[A-Z_]*\s*[:=]\s*[\"']?\d{5,}", text)


def test_oke_check_seeds_the_allowlist_under_the_name_hermes_reads():
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    (step,) = [s for s in wf["jobs"]["check"]["steps"] if "hermes-agent-env" in s.get("name", "")]
    assert step["env"]["TELEGRAM_ALLOWED_USERS"] == step["env"]["TELEGRAM_ALLOWED_USER_IDS"], "one value, both names"
    assert "TELEGRAM_ALLOWED_USERS," in step["run"] and "TELEGRAM_ALLOWED_USER_IDS," in step["run"]
