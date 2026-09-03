"""The customer event door is releasable the moment its image builds.

Everything the door needs to come up is in these manifests, and nothing it needs is a
secret written into git. If any of the links below drifts, the pod boots into a state that
reads green and drops every customer's message; these tests fail the change instead.

The links, and what breaks when each one drifts:

* the entrypoint the container runs must be the one the application repository ships;
* the environment the container reads must be the environment the entrypoint reads;
* the seed's table definition must be the table definition the application declares;
* the operator's chat and the channel credential must come from the vault, never a literal;
* the workload must emit to the estate's own collector, or admission refuses it;
* the route must carry every channel on one path, or the door has bought nothing.
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
LAYER = ROOT / "platform/otto-gateway"


def _docs(rel: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((LAYER / rel).read_text()) if d]


def _one(rel: str, kind: str, name: str) -> dict:
    found = [
        d for d in _docs(rel) if d.get("kind") == kind and d["metadata"]["name"] == name
    ]
    assert found, f"{rel} lost its {kind} named {name}"
    return found[0]


def _gateway_container() -> dict:
    pod = _one("deployment.yaml", "Deployment", "otto-gateway")["spec"]["template"][
        "spec"
    ]
    return next(c for c in pod["containers"] if c["name"] == "gateway")


def _env(container: dict) -> dict[str, str]:
    return {e["name"]: e.get("value", "") for e in container.get("env", [])}


# --- every manifest parses, and the layer is complete ---------------------


def test_every_manifest_in_the_layer_parses() -> None:
    listed = yaml.safe_load((LAYER / "kustomization.yaml").read_text())["resources"]
    for rel in listed:
        docs = _docs(rel)
        assert docs, f"{rel} is listed in the layer but holds no document"


def test_the_layer_lists_every_file_it_ships() -> None:
    """A file in this directory that no kustomization names is a file that never
    reaches the cluster, and reads as shipped to anyone browsing the repository."""
    listed = set(
        yaml.safe_load((LAYER / "kustomization.yaml").read_text())["resources"]
    )
    on_disk = {p.name for p in LAYER.glob("*.yaml")} - {"kustomization.yaml"}
    assert on_disk == listed, (
        f"unlisted: {on_disk - listed}; missing: {listed - on_disk}"
    )


# --- the container runs the entrypoint the application ships --------------


def test_the_container_starts_the_gateway_entrypoint() -> None:
    args = "\n".join(_gateway_container()["args"])
    assert "python -m otto.ingress" in args, (
        "the container no longer starts the event gateway; a manifest naming a module "
        "that cannot start is a pod that comes up green and drops every event"
    )


def test_the_container_reads_the_environment_the_entrypoint_reads() -> None:
    """These names are read by otto/ingress/__main__.py and otto/ingress/pg_store.py.
    A rename on either side, without the other, is a refusal at boot."""
    env = _env(_gateway_container())
    for name in (
        "OTTO_INGRESS_PORT",
        "OTTO_INGRESS_DB_HOST",
        "OTTO_INGRESS_DB_PORT",
        "OTTO_INGRESS_DB_NAME",
        "OTTO_INGRESS_DB_USER",
        "OTTO_INGRESS_DB_PASSWORD_FILE",
        "OTTO_NATS_URL",
    ):
        assert name in env, f"the container stopped setting {name}"


def test_the_database_the_door_dials_is_the_database_this_layer_runs() -> None:
    env = _env(_gateway_container())
    service = _one("postgres.yaml", "Service", "otto-gateway-db")
    assert env["OTTO_INGRESS_DB_HOST"] == service["metadata"]["name"]
    assert env["OTTO_INGRESS_DB_PORT"] == str(service["spec"]["ports"][0]["port"])

    db = _one("postgres.yaml", "StatefulSet", "otto-gateway-db")
    db_env = _env(db["spec"]["template"]["spec"]["containers"][0])
    assert env["OTTO_INGRESS_DB_NAME"] == db_env["POSTGRES_DB"]
    assert env["OTTO_INGRESS_DB_USER"] == db_env["POSTGRES_USER"]


def test_the_port_the_door_listens_on_is_the_port_everything_else_names() -> None:
    container = _gateway_container()
    env = _env(container)
    service = _one("deployment.yaml", "Service", "otto-gateway")
    route = _one("httproute.yaml", "HTTPRoute", "otto-gateway")

    assert env["OTTO_INGRESS_PORT"] == str(container["ports"][0]["containerPort"])
    assert service["spec"]["ports"][0]["port"] == 8080
    for rule in route["spec"]["rules"]:
        for backend in rule["backendRefs"]:
            assert backend["port"] == service["spec"]["ports"][0]["port"]

    fence = [
        d
        for d in _docs("network-policy.yaml")
        if d["metadata"]["name"] == "allow-ingress-from-edge"
    ][0]
    allowed = {p["port"] for rule in fence["spec"]["ingress"] for p in rule["ports"]}
    assert int(env["OTTO_INGRESS_PORT"]) in allowed, (
        "the fence no longer lets the edge reach the port the door listens on"
    )


# --- the workload emits, or admission refuses it --------------------------


def test_the_door_emits_to_the_estate_collector() -> None:
    """LAW 50. The entrypoint refuses to start without this value, and the fence must
    let the packets out, or the door starts and exports nothing."""
    env = _env(_gateway_container())
    endpoint = env.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    assert "signoz-otel-collector.observability" in endpoint, (
        "the door no longer names the estate's own collector"
    )
    port = int(endpoint.rsplit(":", 1)[1])

    fence = [
        d
        for d in _docs("network-policy.yaml")
        if d["metadata"]["name"] == "allow-egress-observability"
    ][0]
    allowed = {p["port"] for rule in fence["spec"]["egress"] for p in rule["ports"]}
    assert port in allowed, "the fence no longer lets traces reach the collector"


def test_the_door_can_reach_the_bus_it_publishes_to() -> None:
    env = _env(_gateway_container())
    port = int(env["OTTO_NATS_URL"].rsplit(":", 1)[1])
    fence = [
        d
        for d in _docs("network-policy.yaml")
        if d["metadata"]["name"] == "allow-egress-event-bus"
    ][0]
    allowed = {p["port"] for rule in fence["spec"]["egress"] for p in rule["ports"]}
    assert port in allowed, (
        "the door would accept a customer's event and be unable to publish it"
    )


# --- no secret, and no customer identifier, is written into git -----------


def test_no_manifest_in_this_layer_carries_a_chat_identifier() -> None:
    for path in LAYER.glob("*.yaml"):
        text = path.read_text()
        assert not re.search(r"chat_id\s*[:=]\s*-?\d", text), f"{path.name}"
        assert not re.search(r"TELEGRAM_CHAT_ID\s*[:=]\s*-?\d", text), f"{path.name}"


def test_every_secret_the_pods_read_comes_from_the_vault() -> None:
    externals = {
        d["metadata"]["name"]: d
        for d in _docs("external-secret.yaml")
        if d["kind"] == "ExternalSecret"
    }
    assert set(externals) == {"otto-gateway-db", "otto-gateway-channels"}
    for name, doc in externals.items():
        assert doc["spec"]["secretStoreRef"]["name"] == "estate-vault", (
            f"{name} points somewhere other than the estate vault"
        )

    rows = {
        row["secretKey"]: row["remoteRef"]
        for row in externals["otto-gateway-channels"]["spec"]["data"]
    }
    assert rows["OTTO_TELEGRAM_WEBHOOK_SECRET"]["key"] == "otto-staging-telegram"
    assert rows["OTTO_TELEGRAM_WEBHOOK_SECRET"]["property"] == "webhook_secret"
    # The operator's chat comes from the entry the estate's alerting already reads, so no
    # new vault entry is invented for a value that already exists.
    assert rows["TELEGRAM_CHAT_ID"]["key"] == "flux-telegram"
    assert rows["TELEGRAM_CHAT_ID"]["property"] == "channel"


def test_no_pod_takes_a_secret_as_an_environment_variable() -> None:
    """Kyverno's secrets-not-from-env-vars policy refuses this at admission; failing
    here means finding out in a pull request instead of in a rollout."""
    for rel in ("deployment.yaml", "postgres.yaml"):
        for doc in _docs(rel):
            if doc["kind"] not in ("Deployment", "StatefulSet"):
                continue
            pod = doc["spec"]["template"]["spec"]
            containers = pod.get("containers", []) + pod.get("initContainers", [])
            for container in containers:
                assert "envFrom" not in container, f"{rel}:{container['name']}"
                for entry in container.get("env", []):
                    assert "valueFrom" not in entry, f"{rel}:{container['name']}"


def test_both_pods_read_the_database_password_from_the_same_mounted_file() -> None:
    door_env = _env(_gateway_container())
    db = _one("postgres.yaml", "StatefulSet", "otto-gateway-db")
    db_env = _env(db["spec"]["template"]["spec"]["containers"][0])
    assert door_env["OTTO_INGRESS_DB_PASSWORD_FILE"] == db_env["POSTGRES_PASSWORD_FILE"]


# --- binding row one, from the vault --------------------------------------


def test_the_seed_writes_row_one_from_files_and_never_from_a_literal() -> None:
    seed = _one("binding-seed.yaml", "ConfigMap", "otto-gateway-binding-seed")
    sql = seed["data"]["seed.sql"]
    assert "'estate', 'telegram', :'chat_id'" in sql, (
        "row one no longer names the estate customer, the telegram channel and a "
        "chat identifier supplied at run time"
    )
    assert ":'fingerprint'" in sql, "the credential is no longer supplied at run time"
    assert "vault://otto-staging-telegram/webhook_secret" in sql, (
        "the row no longer stores a reference to the credential; a reference is what the "
        "table is allowed to hold, and the value is not"
    )


def test_the_seed_is_safe_to_run_on_every_replica_and_every_restart() -> None:
    sql = _one("binding-seed.yaml", "ConfigMap", "otto-gateway-binding-seed")["data"][
        "seed.sql"
    ]
    assert "pg_advisory_lock" in sql and "pg_advisory_unlock" in sql
    assert "ON CONFLICT (channel, external_id) DO UPDATE" in sql
    assert "CREATE TABLE IF NOT EXISTS channel_binding" in sql


def test_the_seed_table_is_the_table_the_application_declares() -> None:
    """The init container is a plain database image with no application code in it, so the
    table definition is repeated here. This is what stops the two drifting: the columns,
    the primary key and the lookup index all come from otto/ingress/store.py."""
    sql = _one("binding-seed.yaml", "ConfigMap", "otto-gateway-binding-seed")["data"][
        "seed.sql"
    ]
    for column in (
        "tenant_id",
        "channel",
        "external_id",
        "secret_ref",
        "token_fingerprint",
        "status",
        "created_at",
    ):
        assert column in sql, f"the seed table lost the column {column}"
    assert "PRIMARY KEY (channel, external_id)" in sql
    assert "channel_binding_lookup" in sql
    assert "ON channel_binding (channel, token_fingerprint)" in sql


def test_the_seed_turns_the_credential_into_a_fingerprint_before_it_is_stored() -> None:
    pod = _one("deployment.yaml", "Deployment", "otto-gateway")["spec"]["template"][
        "spec"
    ]
    seed = next(c for c in pod["initContainers"] if c["name"] == "seed-binding")
    args = "\n".join(seed["args"])
    assert "sha256sum" in args, (
        "the credential would be stored as itself; the table is allowed to hold a one-way "
        "fingerprint and a reference, never the credential"
    )
    assert "/run/secrets/otto-gateway-channels/TELEGRAM_CHAT_ID" in args
    assert "/run/secrets/otto-gateway-channels/OTTO_TELEGRAM_WEBHOOK_SECRET" in args


def test_the_reference_in_the_row_resolves_to_the_key_the_container_exports() -> None:
    """otto/ingress/secrets.py maps a reference onto an environment variable name
    mechanically. If either side is edited alone, the door resolves nothing and every
    event from this customer is refused."""
    sql = _one("binding-seed.yaml", "ConfigMap", "otto-gateway-binding-seed")["data"][
        "seed.sql"
    ]
    reference = re.search(r"'(vault://[^']+)'", sql).group(1)
    expected = (
        "OTTO_CHANNEL_SECRET_"
        + re.sub(r"[^A-Za-z0-9]+", "_", reference).strip("_").upper()
    )
    args = "\n".join(_gateway_container()["args"])
    assert expected in args, f"the container does not export {expected}"


# --- one path for every channel -------------------------------------------


def test_one_path_carries_every_channel() -> None:
    route = _one("httproute.yaml", "HTTPRoute", "otto-gateway")
    matches = [m for rule in route["spec"]["rules"] for m in rule.get("matches", [])]
    paths = [(m["path"]["type"], m["path"]["value"]) for m in matches]
    assert ("PathPrefix", "/webhook/") in paths, (
        "the door lost the one path every channel arrives on"
    )
    for _type, value in paths:
        assert not re.search(r"telegram|slack|whatsapp|teams|discord", value, re.I), (
            f"{value} names a channel; carrying a new channel would mean editing this route"
        )


def test_the_staged_route_leaves_the_existing_door_alone() -> None:
    """The cutover is its own change. Until it is released, the old exact path keeps
    working, so a release of this layer cannot take the founder's own bot down."""
    old = [
        d
        for d in yaml.safe_load_all(
            (ROOT / "platform/otto-golden/httproute.yaml").read_text()
        )
        if d and d.get("kind") == "HTTPRoute"
    ][0]
    old_paths = {
        m["path"]["value"]
        for rule in old["spec"]["rules"]
        for m in rule.get("matches", [])
    }
    assert "/telegram-webhook" in old_paths, (
        "the existing door's route was changed in the same change that adds the new one"
    )

    new = _one("httproute.yaml", "HTTPRoute", "otto-gateway")
    new_paths = {
        m["path"]["value"]
        for rule in new["spec"]["rules"]
        for m in rule.get("matches", [])
    }
    assert not (old_paths & new_paths), (
        f"both routes claim {old_paths & new_paths} on one host, which is a precedence "
        "puzzle nobody should meet during an incident"
    )


def test_the_route_says_where_the_credential_is_checked() -> None:
    route = _one("httproute.yaml", "HTTPRoute", "otto-gateway")
    assert (route["metadata"].get("annotations") or {}).get(
        "idp.estate/auth"
    ) == "channel-binding-registry", (
        "every route in this estate says where its door is locked; this one is locked "
        "against the binding table, because each channel presents a different credential"
    )


def test_the_route_wears_the_estate_manners() -> None:
    route = _one("httproute.yaml", "HTTPRoute", "otto-gateway")
    middlewares = {
        d["metadata"]["name"]
        for d in _docs("edge-manners.yaml")
        if d["kind"] == "Middleware"
    }
    assert middlewares == {"friendly-errors", "edge-headers"}
    for rule in route["spec"]["rules"]:
        named = {f["extensionRef"]["name"] for f in rule.get("filters", [])}
        assert named == middlewares, (
            "a rule that skips these answers a stranger with a raw proxy error and the "
            "backend's own banners"
        )


# --- the image follows every build ----------------------------------------


def test_this_layer_follows_the_image_automation() -> None:
    """A tag bumped by hand is a tag never bumped: the staging layer next door sat on one
    build while three merges shipped past it, so nothing merged reached the running pod.
    The marker is what makes a merge reach a pod, and it needs no new object -- the estate
    runs one ImageUpdateAutomation, it walks the whole checkout, and it rewrites every
    marked line. The same repair for platform/otto-golden is a separate change and is not
    graded here, because a guard that fails on a neighbour's unreleased work is noise."""
    marker = '# {"$imagepolicy": "flux-system:hermes-agent:tag"}'
    text = (ROOT / "platform/otto-gateway/kustomization.yaml").read_text()
    assert marker in text, "this layer would never receive a new build"
    tag_line = next(ln for ln in text.splitlines() if "newTag:" in ln)
    assert re.search(r"newTag: main-\d+-[0-9a-f]{40}", tag_line), (
        "the layer names no full build tag, so a node could cache a moving reference"
    )


# --- the layer exists to Flux, and to the catalogue ------------------------


def test_flux_runs_this_layer() -> None:
    text = (ROOT / "clusters/oke/platform.yaml").read_text()
    rows = [
        d
        for d in yaml.safe_load_all(text)
        if d
        and d.get("kind") == "Kustomization"
        and d["metadata"]["name"] == "otto-gateway"
    ]
    assert rows, "a layer with no row in clusters/oke does not exist in the cluster"
    row = rows[0]["spec"]
    assert row["path"] == "./platform/otto-gateway"
    assert {"edge", "secret-store", "event-bus"} <= {
        d["name"] for d in row["dependsOn"]
    }, "the row could apply before the door's gateway, vault or bus exist"
    assert row["healthChecks"][0]["name"] == "otto-gateway"
    assert any(
        s["kind"] == "ConfigMap" and s["name"] == "estate-config"
        for s in row["postBuild"]["substituteFrom"]
    ), "the route's hostname would apply as the literal placeholder"


def _flux_rows() -> dict:
    rows = {}
    for f in sorted((ROOT / "clusters").rglob("*.y*ml")):
        for d in yaml.safe_load_all(f.read_text()):
            if not isinstance(d, dict) or d.get("kind") != "Kustomization":
                continue
            md = d.get("metadata")
            if isinstance(md, dict) and md.get("name"):
                rows[md["name"]] = d.get("spec") or {}
    return rows


def test_the_door_never_wakes_before_its_bus() -> None:
    """The door's only output is a task on the bus, so a running door with a dark bus
    accepts a customer's message and drops it -- green pod, lost work. event-bus is
    suspended (clusters/oke/commerce.yaml: a bus with no publisher is a workload nobody
    reads) and this door is the publisher it was waiting for, so the two wake together.
    This is the assertion the cutover change has to satisfy, not a note about today."""
    rows = _flux_rows()
    bus = rows["event-bus"].get("suspend") is True
    door = rows["otto-gateway"].get("suspend") is True
    assert not (bus and not door), (
        "otto-gateway is running while event-bus is suspended: every message this door "
        "accepts is published to a bus no cluster reconciles. Unsuspend both in one change."
    )


def test_the_vault_entries_this_layer_reads_are_minted_by_the_estate() -> None:
    """A door that boots before its credential exists is an outage nobody can undo from a
    keyboard. Every entry the layer reads is either minted in-process by the estate's
    bootstrapper or already registered as somebody else's root, and the register is the one
    list that says which (docs/reference/policy/root-trust.md, graded by bin/idp-root-trust)."""
    keys = {
        d["remoteRef"]["key"]
        for doc in _docs("external-secret.yaml")
        for d in doc["spec"]["data"]
    }
    register = (ROOT / "docs/reference/policy/root-trust.md").read_text()
    for key in sorted(keys):
        assert f"`{key}`" in register, (
            f"{key} is read by platform/otto-gateway/external-secret.yaml and named nowhere "
            "in the root trust register, so nothing in the estate says who mints it"
        )
    seed = (ROOT / "bin/idp-estate-seed").read_text()
    assert re.search(r"^otto-gateway-db\s+password\s+hex32\s*$", seed, re.M), (
        "the door's own database password is not in the estate seed plan, so the release "
        "would wait on a hand to write it into the vault"
    )


def test_the_catalogue_carries_the_layer() -> None:
    text = (ROOT / "backstage/platform/catalog-info.yaml").read_text()
    assert "otto-gateway" in text, (
        "backstage/platform/catalog-info.yaml is generated; run bin/catalog-platform "
        "after editing its layer table"
    )
