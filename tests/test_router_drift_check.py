"""bin/router-drift-check: the check that says whether the laptop router and the cluster router
still serve the same names.

Two defects it had on 2026-10-25, both measured against the live cluster:

1. The cluster ConfigMap name was written down (litellm-config-ddgh6tmckk). Flux renames it on
   every render, so the constant was stale within hours and the check exited 2 -- "could not
   measure" -- on a healthy cluster that was serving traffic. The name is now read from the
   live Deployment.
2. It printed "DRIFT wiring differs on vision" and exited 0. A printed DRIFT the verdict does
   not count is a lie the reader cannot detect; and the printed line and the exit code could
   disagree because the verdict was computed after the printing. Now the verdict is computed
   first: every DRIFT line is a counted drift, and every counted drift prints a DRIFT line.
"""

from __future__ import annotations

import importlib.machinery
import io
import json
import types
from contextlib import redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/router-drift-check"


def _load() -> types.ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "router_drift_check_under_test", str(SCRIPT)
    )
    mod = types.ModuleType(loader.name)
    loader.exec_module(mod)
    return mod


rc = _load()


def _config(lanes: dict) -> dict:
    return {
        "model_list": [
            {
                "model_name": name,
                "litellm_params": {"model": model, "api_base": api, "api_key": "x"},
            }
            for name, (model, api) in lanes.items()
        ]
    }


def _write(tmp_path: Path, name: str, cfg: dict) -> str:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(cfg))
    return str(p)


def _run_with_args(argv: list[str]) -> tuple[int, str]:
    import sys

    old = sys.argv
    sys.argv = ["router-drift-check", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = rc.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


def test_the_cluster_configmap_is_read_from_the_live_deployment(monkeypatch):
    """The name is a property of the running Deployment, not a constant in a script."""
    seen: list[list[str]] = []
    deployment = {
        "spec": {
            "template": {
                "spec": {
                    "volumes": [
                        {
                            "name": "config",
                            "configMap": {"name": "litellm-config-28gmg72thg"},
                        },
                        {"name": "other", "configMap": {"name": "litellm-other-xyz"}},
                    ]
                }
            }
        }
    }

    class R:
        returncode = 0
        stdout = json.dumps(deployment)
        stderr = ""

    def fake_kubectl(args, timeout=120):
        seen.append(list(args))
        return R()

    monkeypatch.setattr(rc, "kubectl", fake_kubectl)
    name, why = rc.resolve_cluster_cm("ctx", "llm", "litellm", "config")
    assert name == "litellm-config-28gmg72thg"
    assert why is None
    assert seen and seen[0][-1] == "json"
    assert "get" in seen[0] and "deploy" in seen[0] and "litellm" in seen[0]


def test_no_configmap_name_is_written_down():
    """A hardcoded name is the defect; the check must not carry one."""
    import re

    source = SCRIPT.read_text()
    assert not re.search(r"litellm-config-[a-z0-9]{6,}", source)


def test_a_sphere_local_difference_is_a_note_and_not_a_drift(tmp_path):
    """The laptop serves `vision` from ollama on the host, the cluster serves it from the vendor
    API. That is fulfillment detail (founder 2026-10-25: the names are the contract), so the
    check must exit 0 -- and must not print DRIFT, because a printed DRIFT that is not counted
    is what made this check untrustworthy."""
    laptop = _write(
        tmp_path,
        "laptop.yaml",
        _config(
            {"vision": ("openai/gemma3:4b", "http://host.docker.internal:11434/v1")}
        ),
    )
    cluster = _write(
        tmp_path,
        "cluster.yaml",
        _config(
            {
                "vision": (
                    "gemini/gemini-2.5-flash",
                    "https://generativelanguage.googleapis.com",
                )
            }
        ),
    )
    code, out = _run_with_args(["--laptop", laptop, "--cluster", cluster])
    assert code == 0, out
    assert "DRIFT" not in out
    assert "note wiring differs on vision" in out
    assert out.strip().splitlines()[-1].startswith("OK lanes within policy")


def test_a_rewired_cloud_lane_is_a_counted_drift(tmp_path):
    """Both sides cloud-wired and the wiring differs: that is real drift, counted and printed."""
    laptop = _write(
        tmp_path,
        "laptop.yaml",
        _config({"fast": ("groq/llama-3.1-8b", "https://api.groq.com")}),
    )
    cluster = _write(
        tmp_path,
        "cluster.yaml",
        _config({"fast": ("openai/gpt-4o", "https://api.openai.com")}),
    )
    code, out = _run_with_args(["--laptop", laptop, "--cluster", cluster])
    assert code == 1, out
    assert "DRIFT wiring differs on fast" in out
    assert "FAIL router drift" in out


def test_a_laptop_only_lane_outside_the_allowed_prefix_is_drift(tmp_path):
    laptop = _write(
        tmp_path,
        "laptop.yaml",
        _config(
            {
                "ollama-local": (
                    "ollama/llama3",
                    "http://host.docker.internal:11434/v1",
                ),
                "stray": ("groq/llama", "https://api.groq.com"),
            }
        ),
    )
    cluster = _write(
        tmp_path,
        "cluster.yaml",
        _config({"fast": ("groq/llama-3.1-8b", "https://api.groq.com")}),
    )
    code, out = _run_with_args(["--laptop", laptop, "--cluster", cluster])
    assert code == 1, out
    assert "DRIFT laptop-only lane: stray" in out
    assert "note laptop-only (allowed): ollama-local" in out
