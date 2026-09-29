"""The local-path class exists, is opt-in, and the claims that need it use it (idp#5089)."""

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _docs(text):
    return [d for d in yaml.safe_load_all(text) if d]


def test_local_path_class_is_built_and_never_the_default():
    out = subprocess.run(
        ["kustomize", "build", str(ROOT / "platform/local-path")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    classes = [d for d in _docs(out) if d["kind"] == "StorageClass"]
    assert [c["metadata"]["name"] for c in classes] == ["local-path"]
    anns = classes[0]["metadata"].get("annotations") or {}
    assert anns.get("storageclass.kubernetes.io/is-default-class") != "true"


def test_ollama_model_cache_is_node_local():
    docs = _docs((ROOT / "platform/llm/ollama.yaml").read_text())
    pvc = next(d for d in docs if d["kind"] == "PersistentVolumeClaim")
    assert pvc["spec"]["storageClassName"] == "local-path"
