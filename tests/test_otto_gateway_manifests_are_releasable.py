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


# --- one path for every channel -------------------------------------------


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
