"""The spine's manifests, read against the code that has to match them.

The cross-checks are the point: the Provider's channel in the manifest must be the subject
the code derives, or the bridge terminates every event it is sent as a mismatch. A test
that reads both and compares them is what keeps that from being true.
"""

from __future__ import annotations

import os

import yaml

from spine.contracts import subject_for

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPINE = os.path.join(REPO, "platform", "spine")
CLUSTER = os.path.join(REPO, "clusters", "oke", "platform.yaml")


def load(*parts):
    with open(os.path.join(*parts), "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_all(*parts):
    with open(os.path.join(*parts), "r", encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def test_the_provider_is_the_native_nats_one():
    docs = load_all(SPINE, "events", "provider.yaml")
    providers = [d for d in docs if d.get("kind") == "Provider"]
    assert providers, "no Provider declared"
    for provider in providers:
        assert provider["spec"]["type"] == "nats"
        assert provider["metadata"]["namespace"] == "flux-system"
        assert provider["spec"]["address"].startswith("nats://")


def test_the_provider_channel_is_the_subject_the_code_derives():
    docs = load_all(SPINE, "events", "provider.yaml")
    providers = [d for d in docs if d.get("kind") == "Provider"]
    for provider in providers:
        kind = provider["metadata"]["name"].split("-", 1)[1]
        assert provider["spec"]["channel"] == subject_for(kind.capitalize())


def test_every_alert_selects_a_kind_a_provider_carries():
    docs = load_all(SPINE, "events", "provider.yaml")
    providers = {d["metadata"]["name"] for d in docs if d.get("kind") == "Provider"}
    alerts = [d for d in docs if d.get("kind") == "Alert"]
    assert alerts, (
        "no Alert declared: an event that is not selected is an event that never fires"
    )
    for alert in alerts:
        assert alert["spec"]["providerRef"]["name"] in providers
        assert alert["spec"]["eventSources"]


def test_the_flux_rows_exist_and_the_events_row_waits_for_the_bridge():
    with open(CLUSTER, "r", encoding="utf-8") as handle:
        rows = {
            doc["metadata"]["name"]: doc
            for doc in yaml.safe_load_all(handle)
            if doc and doc.get("kind") == "Kustomization"
        }
    assert "spine" in rows, "the spine has no Flux row"
    assert rows["spine"]["spec"]["path"] == "./platform/spine"
    assert "spine-events" in rows, "the Flux side of the spine has no row"
    assert rows["spine-events"]["spec"]["path"] == "./platform/spine/events"
    # The ordering: the stream has to exist before anything publishes into it.
    depends = [
        d.get("name") for d in (rows["spine-events"]["spec"].get("dependsOn") or [])
    ]
    assert "spine" in depends


def test_the_image_policy_and_the_marker_both_exist():
    policies = load_all(REPO, "platform", "image-automation", "spine.yaml")
    repository = [d for d in policies if d.get("kind") == "ImageRepository"]
    assert repository, "the spine has no ImageRepository"
    assert repository[0]["spec"]["image"] == "ghcr.io/chidionyema/spine"
    kustomization = load(SPINE, "kustomization.yaml")
    marker = [
        i for i in kustomization["images"] if i["name"] == "ghcr.io/chidionyema/spine"
    ]
    assert marker, "the spine's image is not in the kustomization"
    # The marker is a trailing comment on the newTag line, which is how
    # image-automation-controller finds the line to rewrite. Read the raw text for it.
    with open(
        os.path.join(SPINE, "kustomization.yaml"), "r", encoding="utf-8"
    ) as handle:
        raw = handle.read()
    assert "$imagepolicy" in raw, (
        "the spine's newTag line carries no image-policy marker"
    )


def test_the_image_automation_row_is_listed():
    # An ImagePolicy file that nothing applies is a policy that never runs.
    listed = load(REPO, "platform", "image-automation", "kustomization.yaml")[
        "resources"
    ]
    assert "spine.yaml" in listed
    assert "efda.yaml" in listed


def test_the_reader_is_read_only():
    docs = load_all(SPINE, "rbac.yaml")
    roles = [d for d in docs if d.get("kind") == "Role"]
    assert roles, "the spine has no role"
    for role in roles:
        for rule in role["rules"]:
            for verb in rule["verbs"]:
                assert verb in ("get", "list", "watch"), (
                    "a write verb on a status reader: %s" % verb
                )


def test_the_deployments_ask_for_no_secret_in_an_env_var():
    for name in ("bridge.yaml", "worker.yaml"):
        doc = load(SPINE, name)
        container = doc["spec"]["template"]["spec"]["containers"][0]
        for env in container.get("env", []):
            assert "KEY" not in env["name"] or env["name"].endswith("_FILE"), (
                "a credential in an env var: %s" % env["name"]
            )


def test_the_image_names_a_registry():
    for name in ("bridge.yaml", "worker.yaml"):
        doc = load(SPINE, name)
        image = doc["spec"]["template"]["spec"]["containers"][0]["image"]
        assert image.startswith("ghcr.io/"), (
            "the node's cri-o refuses a short name: %s" % image
        )
