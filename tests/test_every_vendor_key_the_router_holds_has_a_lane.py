"""Founder, 2026-09-10: "all agets send should be in litelln".

A key the estate router mounts but serves no model row is a credential every agent has to
go around, and an agent that goes around the router spends off the ledger. On the day this
was written the router held CEREBRAS_API_KEY, NVIDIA_API_KEY and OPENROUTER_API_KEY and
served a lane for none of them, so three vendors were reachable only by agents willing to
call them direct.

This runs the renderer -- the same one bin/idp-ci runs -- and grades what it produced.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONSOLES = ROOT / "platform" / "vendors" / "consoles.yaml"
ROUTER = ROOT / "platform" / "llm" / "config.yaml"
POD = ROOT / "platform" / "llm" / "litellm.yaml"

# A vendor may deliberately hold no git-rendered lane. R75, founder 2026-09-03: a model row
# declared in the rendered config is read-only in the LiteLLM console, so a git-owned row
# takes the credential out of his hands. Those lanes are console-owned and named here.
CONSOLE_OWNED = {"kimi", "deepseek"}


def _vendors():
    d = yaml.safe_load(CONSOLES.read_text())
    return d.get("vendors", d)


def _rendered_lane_names():
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "bin" / "idp-vendor-render")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (  # noqa: S101
        f"the renderer that owns platform/llm/config.yaml failed, so nothing below is "
        f"gradeable:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )
    cfg = yaml.safe_load(ROUTER.read_text())
    return {m["model_name"] for m in cfg["model_list"]}


def _router_mounts():
    """Every env name the router pod will actually hold, read from its own manifest."""
    names = set()
    for doc in yaml.safe_load_all(POD.read_text()):
        if not doc or doc.get("kind") != "Deployment":
            continue
        for c in doc["spec"]["template"]["spec"]["containers"]:
            for v in c.get("volumeMounts", []):
                names.add(v["name"])
    return names


@pytest.fixture(scope="module")
def lanes():
    return _rendered_lane_names()


def test_a_vendor_the_router_can_reach_is_a_vendor_the_router_serves(lanes):
    missing = []
    for name, v in sorted(_vendors().items()):
        if not isinstance(v, dict) or name in CONSOLE_OWNED:
            continue
        reaches_router = any(
            t.get("ns") == "llm" for t in v.get("targets", []) if isinstance(t, dict)
        )
        if reaches_router and not v.get("router"):
            missing.append(name)
    assert not missing, (  # noqa: S101
        f"{missing} put a key in the estate router's namespace and serve no lane on it, so "
        "every agent that wants those vendors has to call them direct and spends off the "
        "ledger the router keeps"
    )


def test_a_lane_the_router_serves_is_a_key_the_router_pod_mounts(lanes):
    """A rendered lane whose key nothing mounts is a lane that answers 401 forever."""
    cfg = yaml.safe_load(ROUTER.read_text())
    mounts = _router_mounts()
    orphans = []
    for m in cfg["model_list"]:
        key = str(m["litellm_params"].get("api_key", ""))
        if not key.startswith("os.environ/"):
            continue
        env = key.split("/", 1)[1]
        vendor = env.rsplit("_API_KEY", 1)[0].lower()
        # the key arrives either inside the one extracted upstream entry or on its own
        # human-<vendor> bridge mount; both are volumeMounts on this Deployment.
        if "upstream" in mounts or f"human-{vendor}" in mounts:
            continue
        orphans.append((m["model_name"], env))
    assert not orphans, (  # noqa: S101
        f"{orphans} name an environment variable the router pod mounts nothing for; the lane "
        "renders, the chain names it, and every turn that reaches it fails auth"
    )
