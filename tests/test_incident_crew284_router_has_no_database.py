"""Incident crew#284 (2026-08-26 23:2xZ): POST /key/generate on https://llm.mumchimp.com answered
"DB not connected. This endpoint needs a database", so no budgeted virtual key could be minted and
the CP2 scenario "the api key is not the proxy master key" could not pass. The cluster router had
been shipped deliberately without Postgres. Rule (rung 4): the cluster router runs the -database
image, composes DATABASE_URL from the mounted LITELLM_DB_PASSWORD, and a Postgres StatefulSet in the
llm namespace reads the same key from the same Secret; the password is never an env literal.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LLM = ROOT / "platform" / "llm"


def _docs(rel):
    return [d for d in yaml.safe_load_all((LLM / rel).read_text()) if d]


def test_incident_crew284_cluster_router_has_its_database():
    dep = next(d for d in _docs("litellm.yaml") if d["kind"] == "Deployment")
    c = dep["spec"]["template"]["spec"]["containers"][0]
    assert c["image"].startswith("ghcr.io/berriai/litellm-database:")
    script = c["args"][0]
    # idp#262 shipped `${LITELLM_DB_PASSWORD}` here and Flux's strict envsubst refused the build
    # ("variable not set (strict mode)"); the shell reads the file instead, `$(...)` is not a Flux variable.
    assert 'export DATABASE_URL="postgresql://litellm:$(cat /run/secrets/litellm/upstream/LITELLM_DB_PASSWORD)@litellm-db' in script
    assert "${LITELLM_DB_PASSWORD}" not in script
    assert "DATABASE_URL" not in {e["name"] for e in c["env"]}, "the URL holds the password; it is composed, not declared"

    sts = next(d for d in _docs("postgres.yaml") if d["kind"] == "StatefulSet")
    pg = sts["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e.get("value") for e in pg["env"]}
    assert "POSTGRES_PASSWORD" not in env
    assert env["POSTGRES_PASSWORD_FILE"] == "/run/secrets/litellm/upstream/LITELLM_DB_PASSWORD"
    vols = {v["name"]: v for v in sts["spec"]["template"]["spec"]["volumes"]}
    assert vols["upstream"]["secret"] == {"secretName": "litellm-upstream"}
    assert "postgres.yaml" in yaml.safe_load((LLM / "kustomization.yaml").read_text())["resources"]


def test_incident_crew284_router_survives_its_migration_window():
    """2026-08-26 23:2xZ: the -database image ran Prisma migrations, :4000 stayed closed, liveness
    (timeout 1s, no startupProbe) killed it 8 times. A DB-backed router declares a startupProbe
    covering at least 3 minutes and probe timeouts above the 1s default."""
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/llm/litellm.yaml").read_text()) if d]
    dep = [d for d in docs if d.get("kind") == "Deployment" and d["metadata"]["name"] == "litellm"][0]
    c = dep["spec"]["template"]["spec"]["containers"][0]
    s = c["startupProbe"]
    assert s["periodSeconds"] * s["failureThreshold"] >= 180
    assert s["timeoutSeconds"] >= 3 and c["livenessProbe"]["timeoutSeconds"] >= 3
    # Second cause, same incident: OOMKilled at 1Gi 19s after start (lastState.terminated.reason).
    mem = c["resources"]["limits"]["memory"]
    assert mem.endswith("Gi") and int(mem[:-2]) >= 2, mem
