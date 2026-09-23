"""GOV-01 (2026-09-15 Battalion spec): the free local model lane must not depend on a laptop.

`llm/config.yaml`'s ollama/* entries pointed at `host.docker.internal:11434` -- the founder's
own Mac -- which he killed on 2026-09-10 ("no i killed ollama because machine is slow",
`platform/otto-gateway/three-homes.yaml:28-29`). Every call routed there has been silently
falling through to a paid model since. `platform/llm/ollama.yaml` runs the same free floor
in-cluster instead. This file grades the three things that made that laptop dependency real,
so it cannot come back the same way: the cluster resource exists, the router points at the
cluster Service rather than the laptop, and the manifest is actually wired into the
Kustomization that ships it.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OLLAMA_MANIFEST = ROOT / "platform" / "llm" / "ollama.yaml"
CONFIG_BASE = ROOT / "platform" / "llm" / "config.base.yaml"
KUSTOMIZATION = ROOT / "platform" / "llm" / "kustomization.yaml"

LAPTOP_HOST = "host.docker.internal"
CLUSTER_HOST = "ollama.llm.svc.cluster.local"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_the_cluster_runs_its_own_ollama():
    """A Deployment and a Service named `ollama` exist in the `llm` namespace."""
    docs = _docs(OLLAMA_MANIFEST)
    kinds = {(d.get("kind"), d.get("metadata", {}).get("name")): d for d in docs}

    deployment = kinds.get(("Deployment", "ollama"))
    service = kinds.get(("Service", "ollama"))
    assert deployment is not None, (
        "no Deployment named ollama in platform/llm/ollama.yaml"
    )
    assert service is not None, "no Service named ollama in platform/llm/ollama.yaml"
    assert deployment["metadata"]["namespace"] == "llm"
    assert service["metadata"]["namespace"] == "llm"


def test_the_pod_does_not_depend_on_a_laptop_being_on():
    """Nothing in the manifest reaches for the founder's Mac."""
    # the comment block is allowed to name the retired laptop lane for context; the object
    # bodies below the first `---` line must not.
    for doc in _docs(OLLAMA_MANIFEST):
        assert LAPTOP_HOST not in yaml.dump(doc)


def test_the_router_points_at_the_cluster_service_not_the_laptop():
    """`config.base.yaml`'s new ollama lane must resolve in-cluster."""
    docs = _docs(CONFIG_BASE)
    model_list = next(d["model_list"] for d in docs if "model_list" in d)
    ollama_rows = [row for row in model_list if row.get("model_name") == "ollama"]
    assert ollama_rows, "no model_name: ollama row in config.base.yaml's model_list"
    for row in ollama_rows:
        api_base = row["litellm_params"]["api_base"]
        assert LAPTOP_HOST not in api_base, (
            f"ollama row still points at the laptop: {api_base}"
        )
        assert CLUSTER_HOST in api_base


def test_ollama_manifest_is_wired_into_the_kustomization():
    """A manifest nobody applies is not a deployed lane."""
    docs = _docs(KUSTOMIZATION)
    resources = docs[0]["resources"]
    assert "ollama.yaml" in resources
