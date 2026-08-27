"""Incident 2026-08-27 (crew#483): idp#310 merged a CronJob whose shell script used `${out%% *}`.
The identity Kustomization runs postBuild substitution in strict mode, so Flux refused the whole
layer ("variable not set (strict mode): out"); healthchecks depends on identity and went down
with it. No CI gate rendered substitution before merge. Rule (rung 4): every manifest under a
Kustomization path that declares postBuild passes `flux envsubst --strict` with exactly the keys
its substituteFrom sources provide. A shell expansion inside such a manifest is written `$${var}`.
Both ways: main's line fails, the escaped line passes and keeps the literal for the container.
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLUSTERS = ROOT / "clusters" / "oke"


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _flux():
    if not shutil.which("flux"):
        pytest.skip("BLIND: flux CLI not installed")


def _envsubst(text, env):
    r = subprocess.run(["flux", "envsubst", "--strict"], input=text, capture_output=True, text=True,
                       env={**os.environ, **env})
    return r.returncode, (r.stdout if r.returncode == 0 else r.stderr)


def _source_keys(name, kind):
    """The keys a substituteFrom source provides: a ConfigMap's data, or an ExternalSecret's
    secretKey / template keys for a Secret (the Secret itself never sits in git)."""
    keys = set()
    for path in list(CLUSTERS.glob("*.yaml")) + list((ROOT / "platform").rglob("*.yaml")):
        for d in _docs(path):
            if kind == "ConfigMap" and d.get("kind") == "ConfigMap" and d["metadata"]["name"] == name:
                keys |= set((d.get("data") or {}).keys())
            if kind == "Secret" and d.get("kind") == "ExternalSecret" and (d["spec"].get("target") or {}).get("name", d["metadata"]["name"]) == name:
                keys |= {x["secretKey"] for x in d["spec"].get("data", []) if "secretKey" in x}
                keys |= set((((d["spec"].get("target") or {}).get("template") or {}).get("data") or {}).keys())
    if kind == "ConfigMap" and not keys:
        # estate-vars is created on the cluster by bin/idp-flux-bootstrap from tofu outputs, never
        # committed; its keys are the --from-literal names on that one kubectl line.
        for line in (ROOT / "bin" / "idp-flux-bootstrap").read_text().splitlines():
            if f"create configmap {name} " in line:
                keys |= set(re.findall(r"--from-literal=([A-Za-z_][A-Za-z_0-9]*)=", line))
    assert keys, f"substituteFrom source {kind}/{name}: no keys found in git or bin/idp-flux-bootstrap; the gate would be blind to it"
    return keys


def _postbuild_paths():
    for path in CLUSTERS.glob("*.yaml"):
        for d in _docs(path):
            if d.get("kind") == "Kustomization" and d["spec"].get("postBuild"):
                env = {}
                for s in d["spec"]["postBuild"].get("substituteFrom", []):
                    env.update({k: f"{k}.example" for k in _source_keys(s["name"], s.get("kind", "ConfigMap"))})
                env.update({k: str(v) for k, v in (d["spec"]["postBuild"].get("substitute") or {}).items()})
                yield d["metadata"]["name"], ROOT / d["spec"]["path"], env


def test_incident_crew483_every_postbuild_manifest_substitutes_strictly():
    _flux()
    failures = []
    seen = 0
    for kz, path, env in _postbuild_paths():
        if not path.exists():
            continue  # a product overlay (deploy/k8s) lives in the product's repo, not here
        for f in sorted(path.rglob("*.yaml")):
            seen += 1
            rc, out = _envsubst(f.read_text(), env)
            if rc:
                failures.append(f"{kz}: {f.relative_to(ROOT)}: {out.strip()[:160]}")
    assert seen > 0
    assert not failures, "\n".join(failures)


def test_incident_crew483_the_escape_holds_both_ways():
    _flux()
    bad = "code=${out%% *}; loc=${out#* }; host=${ESTATE_ZONE}\n"
    good = "code=$${out%% *}; loc=$${out#* }; host=${ESTATE_ZONE}\n"
    env = {"ESTATE_ZONE": "example.test"}
    rc, msg = _envsubst(bad, env)
    assert rc == 1 and '"out"' in msg, msg
    rc, out = _envsubst(good, env)
    assert rc == 0 and out == "code=${out%% *}; loc=${out#* }; host=example.test\n", out
