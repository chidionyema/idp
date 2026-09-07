"""The bridge from Bitwarden into the cluster resolves a key by name, never by search.

External Secrets offers two ways to pull a value out of Bitwarden Secrets Manager. Only one of
them is safe here, and the unsafe one looks like the convenient one, which is why this is a test
and not a comment.

Measured 2026-09-07 against bitwarden-sdk-server v0.6.0 behind external-secrets v2.9.0, in the
estate's own project: `dataFrom.find` IGNORES `name.regexp`. An ExternalSecret asking for

    dataFrom:
      - find: { name: { regexp: "^NO_SUCH_KEY_AT_ALL$" } }
        rewrite: [ { regexp: { source: ".*", target: "NO_SUCH_KEY_AT_ALL" } } ]

synced green and produced a Secret holding a key called NO_SUCH_KEY_AT_ALL whose value was an
unrelated secret that happened to be the only one in the project. Three such blocks in one
ExternalSecret produced three differently-named keys all carrying the same value. A bridge built
that way would serve one vendor's credential under every other vendor's name and report itself
healthy while doing it.

`data[].remoteRef.key: <name>` resolves exactly and fails closed when the name is absent -- which
is the behaviour a credential path must have, and is what the generator emits. This test grades the
generator's output, so a future edit that reaches for `find` because it tolerates missing keys
fails here rather than in production.
"""

import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "platform/human-vault-bridge/externalsecrets.yaml"
SEED = ROOT / "platform" / "human-vault-bridge" / "pushsecrets.yaml"
REGISTRY = ROOT / "platform/vendors/consoles.yaml"


def bridge_docs():
    return [d for d in yaml.safe_load_all(BRIDGE.read_text()) if d]


def test_no_bridge_external_secret_resolves_a_key_by_search():
    for doc in bridge_docs():
        spec = doc["spec"]
        assert "dataFrom" not in spec, (
            f"{doc['metadata']['name']} in {doc['metadata']['namespace']} uses dataFrom; "
            "this provider ignores find.name.regexp and would map an unrelated secret onto "
            "every field"
        )
        assert spec["data"], f"{doc['metadata']['name']} carries no data entries"
        for entry in spec["data"]:
            assert entry["remoteRef"]["key"], "a remoteRef with no key resolves nothing"


def test_every_bridge_secret_reads_the_human_store():
    for doc in bridge_docs():
        ref = doc["spec"]["secretStoreRef"]
        assert ref["name"] == "human-vault" and ref["kind"] == "ClusterSecretStore", (
            f"{doc['metadata']['name']} reads {ref}; the bridge exists to read the store the "
            "founder writes to, and reading the estate's own vault here would be a loop"
        )


def test_every_human_vault_vendor_target_says_where_it_lands_and_what_it_is_called():
    vendors = yaml.safe_load(REGISTRY.read_text())["vendors"]
    for name, v in vendors.items():
        if v.get("store_default") != "human-vault":
            continue
        for target in v.get("targets") or []:
            if target.get("derived"):
                continue  # computed from another field; no human ever drops it anywhere
            assert target.get("ns"), (
                f"{name} target {target} names no namespace, so nothing can be generated for it"
            )
            assert target.get("bw"), (
                f"{name} target {target} names no Bitwarden secret, so the bridge cannot address it"
            )


def test_the_generated_bridge_matches_the_registry():
    proc = subprocess.run(
        [str(ROOT / "bin/idp-vendor-render"), "--check"], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_bridge_covers_the_vendor_the_founder_actually_uses():
    """A generator that emitted nothing would pass every assertion above."""
    landed = {
        (d["metadata"]["name"], d["metadata"]["namespace"]) for d in bridge_docs()
    }
    assert ("human-minimax", "llm") in landed
    assert len(landed) > 10, (
        f"only {len(landed)} bridge secrets; the registry holds far more"
    )


def test_the_seed_never_overwrites_a_key_the_founder_has_set():
    """A PushSecret defaults to Replace, which would rewrite his rotated key from the estate's
    stale copy on the next refresh -- silently undoing every rotation. IfNotExists fills an
    empty slot and touches nothing else."""
    docs = [d for d in yaml.safe_load_all(SEED.read_text()) if d]
    assert docs
    for d in docs:
        assert d["spec"]["updatePolicy"] == "IfNotExists", d["metadata"]["name"]
        assert d["spec"]["deletionPolicy"] == "None", d["metadata"]["name"]


def test_one_key_the_estate_lacks_cannot_stop_the_others_being_seeded():
    """Measured 2026-09-07: one absent key fails the whole object it sits in and seeds none of
    its siblings. MOONSHOT_API_KEY is in the registry and in no Secret, so grouping would have
    cost GEMINI and OPENROUTER their seed."""
    docs = [d for d in yaml.safe_load_all(SEED.read_text()) if d]
    for d in docs:
        assert len(d["spec"]["data"]) == 1, d["metadata"]["name"]


def test_the_seed_reads_the_secret_the_registry_says_holds_the_key():
    reg = yaml.safe_load(REGISTRY.read_text())["vendors"]
    want = {
        (t["ns"], t["bw"]): (t["entry"], t["field"])
        for v in reg.values()
        if v.get("store_default") == "human-vault"
        for t in (v.get("targets") or [])
        if t.get("bw") and t.get("ns") and not t.get("derived")
    }
    got = {}
    for d in yaml.safe_load_all(SEED.read_text()):
        if not d:
            continue
        m = d["spec"]["data"][0]["match"]
        got[(d["metadata"]["namespace"], m["remoteRef"]["remoteKey"])] = (
            d["spec"]["selector"]["secret"]["name"],
            m["secretKey"],
        )
    assert got == want
