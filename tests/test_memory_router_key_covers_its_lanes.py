"""The memory server's router key must be allowed every lane the server calls (#6183).

It read otto-golden's key, minted before embed-query existed, so the router refused every recall
(403 key_model_access_denied) and the server answered 503. This reads the ExternalSecret's vault
entry and the server's two embed models, and checks that bin/idp-estate-seed mints that entry a
key allowed both.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/unified-memory-server/oke-unified-memory.yaml"
SEED = ROOT / "bin/idp-estate-seed"


def _router_plan() -> dict:
    text = SEED.read_text()
    block = re.search(r"ROUTER_PLAN=\$\(cat <<EOF\n(.*?)\nEOF", text, re.S).group(1)
    plan = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        entry, field, models = line.split()
        plan[(entry, field)] = set(models.split(","))
    return plan


def test_the_memory_router_key_may_call_every_embed_lane_the_server_uses():
    docs = list(yaml.safe_load_all(MANIFEST.read_text()))
    es = next(d for d in docs if d and d.get("kind") == "ExternalSecret")
    ref = next(
        d["remoteRef"]
        for d in es["spec"]["data"]
        if d["secretKey"] == "litellm_api_key"
    )
    deploy = next(d for d in docs if d and d.get("kind") == "Deployment")
    env = {
        e["name"]: e.get("value")
        for c in deploy["spec"]["template"]["spec"]["containers"]
        for e in c.get("env", [])
    }
    lanes = {env["MEMORY_EMBED_MODEL"], env["MEMORY_EMBED_QUERY_MODEL"]}

    allowed = _router_plan().get((ref["key"], ref["property"]))
    assert allowed is not None, f"{ref} is not a router key bin/idp-estate-seed mints"
    assert lanes <= allowed, f"{ref['key']} key lacks {sorted(lanes - allowed)}"
