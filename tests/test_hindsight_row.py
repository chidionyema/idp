"""The `hindsight` Flux row (crew#524 CP1): self-hosted Hindsight memory for the Architect on OKE.

Rung 2, properties over the manifests: nothing secret sits in a value (the DB password and the
router key come from the vault through one ExternalSecret and the chart's `existingSecret`); the
chart's unpinned, root-running bundled Postgres is replaced by a pinned pgvector StatefulSet in the
restricted namespace; the Kyverno waiver is scoped to the api pods and nothing else; the Flux row
waits on the vault and the router; the hermes gateway points at the in-cluster service.
Rung 4, incident: `bin/idp-kyverno-render` addressed every chart with `--repo <url>`, which only
speaks the HTTP index, so an OCI HelmRepository exited 1 and read as "no render"; and helm's
`Pulled:`/`Digest:` preamble on stdout broke kustomize. Proved both ways with a helm shim.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "platform" / "hindsight"


def _docs(rel):
    return [d for d in yaml.safe_load_all((ROW / rel).read_text()) if d]


def _one(rel, kind, name):
    hits = [d for d in _docs(rel) if d.get("kind") == kind and d["metadata"]["name"] == name]
    assert len(hits) == 1, (rel, kind, name, len(hits))
    return hits[0]


def test_no_secret_sits_in_a_value_and_the_chart_reads_the_one_the_vault_writes():
    hr = _one("hindsight.yaml", "HelmRelease", "hindsight")
    values = hr["spec"]["values"]
    flat = json.dumps(values).lower()
    for word in ("password", "api_key", "apikey", "token"):
        assert f'"{word}"' not in flat and not re.search(rf'{word}[^"]*":\s*"[^"$]', flat), (word, flat)
    assert values["existingSecret"] == "hindsight-env"
    assert values["postgresql"]["enabled"] is False, "the chart's bundled ankane/pgvector:latest runs as root"
    es = _one("external-secret.yaml", "ExternalSecret", "hindsight-env")
    assert es["spec"]["target"]["name"] == "hindsight-env"
    assert [d["extract"]["key"] for d in es["spec"]["dataFrom"]] == ["hindsight"]


def test_the_database_is_pinned_non_root_and_reads_its_password_from_the_vault_file():
    sts = _one("postgres.yaml", "StatefulSet", "hindsight-db")
    ns = _one("namespace.yaml", "Namespace", "hindsight")
    assert ns["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"
    c = sts["spec"]["template"]["spec"]["containers"][0]
    assert re.fullmatch(r"docker\.io/pgvector/pgvector:\d+\.\d+\.\d+-pg\d+", c["image"]), c["image"]
    env = {e["name"]: e.get("value") for e in c["env"]}
    assert env["POSTGRES_PASSWORD_FILE"] == "/run/secrets/hindsight-env/postgres-password"
    assert "POSTGRES_PASSWORD" not in env
    sc = c["securityContext"]
    assert sc["allowPrivilegeEscalation"] is False and sc["capabilities"]["drop"] == ["ALL"]
    assert sts["spec"]["template"]["spec"]["securityContext"]["runAsNonRoot"] is True
    hr = _one("hindsight.yaml", "HelmRelease", "hindsight")
    assert hr["spec"]["values"]["postgresql"]["external"]["host"] == "hindsight-db"


def test_the_kyverno_waiver_covers_the_api_pods_only():
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/edge/hindsight-exception.yaml").read_text()) if d]
    (pe,) = [d for d in docs if d["kind"] == "PolicyException"]
    assert pe["metadata"]["namespace"] == "kyverno"
    assert [e["policyName"] for e in pe["spec"]["exceptions"]] == ["secrets-not-from-env-vars"]
    match = pe["spec"]["match"]["any"]
    assert all(r["resources"]["namespaces"] == ["hindsight"] for r in match)
    names = {n for r in match for n in r["resources"]["names"]}
    assert names == {"hindsight-api*"}, names
    assert "hindsight-exception.yaml" in (ROOT / "platform/edge/kustomization.yaml").read_text()


def test_the_flux_row_waits_on_the_vault_and_the_router_and_the_gateway_points_at_it():
    rows = [d for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text())
            if d and d["metadata"]["name"] == "hindsight"]
    assert len(rows) == 1
    deps = {d["name"] for d in rows[0]["spec"]["dependsOn"]}
    assert {"secret-store", "llm"} <= deps, deps
    assert rows[0]["spec"]["healthChecks"][0]["kind"] == "HelmRelease"
    gw = [d for d in yaml.safe_load_all((ROOT / "platform/hermes-agent/gateway.yaml").read_text())
          if d and d["kind"] == "Deployment"][0]
    env = {e["name"]: e.get("value") for c in gw["spec"]["template"]["spec"]["containers"] for e in c["env"]}
    assert env["HINDSIGHT_API_URL"] == "http://hindsight-api.hindsight.svc:8888"
    seed = (ROOT / ".github/workflows/vault-seed.yml").read_text()
    # crew#66 root trust (crew#575): the password is minted by bin/idp-estate-seed; vault-seed refuses the
    # entry by name and no SEED_HINDSIGHT_* secret exists any more.
    assert "SEED_HINDSIGHT_DB_PASSWORD" not in seed and "hindsight|" in seed and "never seeded by hand" in seed
    assert "postgres-password" in (ROOT / "bin/idp-estate-seed").read_text()
    import yaml as _y
    opts = _y.safe_load(seed)[True]["workflow_dispatch"]["inputs"]["entry"]["options"]
    assert "hindsight" in opts, "the dispatch choice list lost `hindsight` in the #430 merge (2026-08-27)"


# --- rung 4: the renderer incident -------------------------------------------------------------

def _renderer_helm_block():
    src = (ROOT / "bin/idp-kyverno-render").read_text()
    m = re.search(r'python3 - "\$S" "\$S/kz.yaml" <<\'PY\'\n(.*?)\nPY\n', src, re.S)
    assert m, "the helm block moved; update the test"
    return m.group(1)


def _run_renderer(tmp_path, url):
    shim = tmp_path / "bin"; shim.mkdir()
    helm = shim / "helm"
    helm.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$HELM_ARGS\"\n"
                    "printf 'Pulled: x\\nDigest: sha256:0\\n---\\napiVersion: v1\\nkind: ConfigMap\\nmetadata:\\n  name: r\\n'\n")
    helm.chmod(helm.stat().st_mode | stat.S_IEXEC)
    s = tmp_path / "S"; s.mkdir()
    (tmp_path / "kz.yaml").write_text(yaml.safe_dump_all([
        {"apiVersion": "source.toolkit.fluxcd.io/v1", "kind": "HelmRepository",
         "metadata": {"name": "repo"}, "spec": {"url": url}},
        {"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease",
         "metadata": {"name": "c", "namespace": "n"},
         "spec": {"chart": {"spec": {"chart": "hindsight", "version": "0.9.2", "sourceRef": {"name": "repo"}}}}}]))
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "HELM_ARGS": str(tmp_path / "args")}
    subprocess.run([sys.executable, "-", str(s), str(tmp_path / "kz.yaml")], input=_renderer_helm_block(),
                   text=True, check=True, env=env, capture_output=True)
    return (tmp_path / "args").read_text().split("\n"), (s / "c.render.yaml").read_text()


def test_incident_crew524_an_oci_repository_is_addressed_as_a_chart_ref_and_the_preamble_is_dropped(tmp_path):
    args, render = _run_renderer(tmp_path, "oci://ghcr.io/vectorize-io/charts")
    assert "oci://ghcr.io/vectorize-io/charts/hindsight" in args and "--repo" not in args, args
    assert render.startswith("---\n") and [d["kind"] for d in yaml.safe_load_all(render) if d] == ["ConfigMap"]


def test_incident_crew524_an_http_repository_still_goes_through_repo(tmp_path):
    args, render = _run_renderer(tmp_path, "https://charts.example.org")
    assert args[args.index("--repo") + 1] == "https://charts.example.org" and "hindsight" in args
    assert yaml.safe_load_all(render)
