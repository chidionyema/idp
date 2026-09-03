"""Incident (crew#284, idp#262, 2026-08-27 00:1xZ): `platform/llm/litellm.yaml` carried
`${LITELLM_DB_PASSWORD}` inside a shell launch script. Flux post-build substitution is strict, the
name is in no substituteFrom source, and the `llm` Kustomization stopped at
`BuildFailed: envsubst error: variable substitution failed: variable not set (strict mode)` while CI
was green: nothing in CI knew which `${NAME}` Flux would try to substitute.

Rule (rung 2, a property over every Kustomization in clusters/*/platform.yaml): every `${UPPER_NAME}`
in the files a Kustomization applies is a key of one of its substituteFrom sources. Sources come from
git (`clusters/*/estate-config.yaml`) or from the bootstrap that creates them (`bin/idp-flux-bootstrap`
writes `estate-vars`). A shell variable in a manifest is written `$(...)`, `$name` or `$$`-escaped.
"""
import glob
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
VAR = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def source_keys() -> dict[str, set[str]]:
    keys: dict[str, set[str]] = {}
    for f in glob.glob(str(ROOT / "clusters" / "*" / "*.yaml")):
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if d and d.get("kind") == "ConfigMap":
                keys.setdefault(d["metadata"]["name"], set()).update((d.get("data") or {}).keys())
    boot = (ROOT / "bin" / "idp-flux-bootstrap").read_text()
    for m in re.finditer(r"create configmap (\S+)((?:\s+--from-literal=[A-Z_]+=\S+)+)", boot):
        keys.setdefault(m.group(1), set()).update(re.findall(r"--from-literal=([A-Z_]+)=", m.group(2)))
    return keys


def undefined_variables(path_text: str, allowed: set[str]) -> set[str]:
    """Pure: the `${NAME}` references in one manifest text that no source defines."""
    return {v for v in VAR.findall(path_text) if v not in allowed}


def kustomizations():
    for f in glob.glob(str(ROOT / "clusters" / "*" / "*.yaml")):
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if d and d.get("kind") == "Kustomization" and d["spec"].get("path"):
                yield d


def test_every_flux_variable_has_a_source():
    keys = source_keys()
    assert keys.get("estate-config") and keys.get("estate-vars"), keys
    bad = {}
    for ks in kustomizations():
        subs = ks["spec"].get("postBuild", {}).get("substituteFrom", [])
        if not subs:
            continue  # Flux only runs envsubst when postBuild is set; without it `${X}` is passed through
        allowed = set().union(*(keys.get(s["name"], set()) for s in subs))
        for f in sorted(glob.glob(str(ROOT / ks["spec"]["path"] / "**" / "*.yaml"), recursive=True)):
            missing = undefined_variables(pathlib.Path(f).read_text(), allowed)
            if missing:
                bad[str(pathlib.Path(f).relative_to(ROOT))] = sorted(missing)
    assert not bad, f"Flux strict envsubst would refuse these builds: {bad}"


def test_guard_refuses_the_incident_and_permits_shell_forms():
    allowed = {"ESTATE_ZONE"}
    assert undefined_variables('export X="pg://u:${LITELLM_DB_PASSWORD}@h"', allowed) == {"LITELLM_DB_PASSWORD"}
    assert undefined_variables('host: a.${ESTATE_ZONE}\nexport "$(basename "$f")=$(cat "$f")"', allowed) == set()
