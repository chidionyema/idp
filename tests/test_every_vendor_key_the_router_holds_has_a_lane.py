"""Founder, 2026-09-10: "all agets send should be in litelln".

A key the estate router mounts but serves no model row is a credential every agent has to
go around, and an agent that goes around the router spends off the ledger. On the day this
was written the router held CEREBRAS_API_KEY, NVIDIA_API_KEY and OPENROUTER_API_KEY and
served a lane for none of them, so three vendors were reachable only by agents willing to
call them direct.

This runs the renderer -- the same one bin/idp-ci runs -- and grades what it produced.
"""

import importlib.machinery
import importlib.util
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


def _vendor_render():
    """bin/idp-vendor-render as a module: its render() in memory, never its write.

    Run as a script it rewrites llm/config.yaml and platform/llm/config.yaml in the checkout,
    so every test run silently undid an uncommitted edit to either file (2026-10-13: a lane's
    voice-tts rows vanished on each pre-push run).
    """
    loader = importlib.machinery.SourceFileLoader(
        "idp_vendor_render", str(ROOT / "bin" / "idp-vendor-render")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _vendors():
    d = yaml.safe_load(CONSOLES.read_text())
    return d.get("vendors", d)


def _rendered_lane_names():
    vr = _vendor_render()
    vendors = yaml.safe_load(vr.REG.read_text())["vendors"]
    base = "platform/llm/config.base.yaml"
    cfg = yaml.safe_load(vr.render(vendors, (ROOT / base).read_text(), base))
    return {m["model_name"] for m in cfg["model_list"]}


def _router_mounts():
    """Every volume the router pod mounts, read from its own manifest."""
    names = set()
    for doc in yaml.safe_load_all(POD.read_text()):
        if not doc or doc.get("kind") != "Deployment":
            continue
        for c in doc["spec"]["template"]["spec"]["containers"]:
            for v in c.get("volumeMounts", []):
                names.add(v["name"])
    return names


def _upstream_fields():
    """The env names the extracted `litellm-upstream` Secret is DECLARED to carry.

    Read from the registry's targets, because the manifest names the Secret and not its keys.
    This is what the registry asks for, not what the live Secret holds -- measured 2026-10-10,
    llm/litellm-upstream carried 7 keys (ANTHROPIC, GEMINI, GROQ, LITELLM_DB_PASSWORD,
    LITELLM_MASTER_KEY, MINIMAX, OPENROUTER) and NOT DEEPSEEK_API_KEY, though consoles.yaml
    declares a deepseek -> litellm-upstream target. A declaration is not a key. So this set is
    deliberately NOT used to prove a lane can authenticate; `_router_mounts()` is the half git
    can actually witness, and it is the half that was missing for deepseek.
    """
    return {
        t.get("field")
        for v in _vendors().values()
        for t in (v.get("targets") or [])
        if t.get("entry") == "litellm-upstream" and t.get("field")
    }


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
    """A rendered lane whose key nothing mounts is a lane that answers 401 forever.

    2026-10-10: this check could not fail. It asked `"upstream" in mounts`, and `upstream` is
    the name of a volumeMount that is always present, so the condition short-circuited to True
    for every vendor on every run. The deepseek lane sat in exactly the state this docstring
    describes and this test passed: the row rendered, the chain named it, and
    `os.environ/DEEPSEEK_API_KEY` resolved to nothing, because human-deepseek was mounted by
    neither the volumeMounts nor the volumes -- while llm/litellm-upstream, the other route,
    carried 7 keys and not that one (measured in-cluster 2026-10-10).

    The grade is the human-<vendor> mount, which is the half a checkout can witness. A
    registry that declares a litellm-upstream target is not evidence the key is there: for
    deepseek the declaration existed and the key did not.
    """
    cfg = yaml.safe_load(ROUTER.read_text())
    mounts = _router_mounts()
    orphans = []
    for m in cfg["model_list"]:
        key = str(m["litellm_params"].get("api_key", ""))
        if not key.startswith("os.environ/"):
            continue
        env = key.split("/", 1)[1]
        vendor = env.rsplit("_API_KEY", 1)[0].lower()
        if f"human-{vendor}" in mounts or f"human-{env.lower()}" in mounts:
            continue
        orphans.append((m["model_name"], env))
    assert not orphans, (  # noqa: S101
        f"{orphans} name an environment variable no human-<vendor> mount provides; the lane "
        "renders, the chain names it, and every turn that reaches it fails auth"
    )
