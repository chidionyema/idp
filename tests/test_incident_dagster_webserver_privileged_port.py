"""idp incident 2026-09-02: the dagster webserver crash-looped binding port 80.

The class of mistake: a pod hardened to run non-root (uid 999) told to bind a
privileged port. A non-root process cannot hold a port under 1024, so the
webserver died at start with "[Errno 13] permission denied" on 0.0.0.0:80 --
the security context and the listen port were decided in the same file and
never checked against each other. This test holds the pair consistent, and
holds the front door at 80: the chart renders the Service on the bind port, so
a postRenderer patch must put external port 80 back or every consumer
(Backstage's DAGSTER_GRAPHQL_URL names :80) goes dark.
"""

from pathlib import Path

import yaml

DAGSTER = Path(__file__).resolve().parents[1] / "platform" / "dagster" / "dagster.yaml"


def release_values():
    docs = list(yaml.safe_load_all(DAGSTER.read_text()))
    rel = next(d for d in docs if d and d.get("kind") == "HelmRelease")
    return rel["spec"]["values"], rel["spec"]


def test_a_nonroot_webserver_never_binds_a_privileged_port():
    values, _ = release_values()
    web = values["dagsterWebserver"]
    if not web.get("podSecurityContext", {}).get("runAsNonRoot"):
        return
    port = web.get("service", {}).get("port", 80)
    assert port >= 1024, (
        f"dagsterWebserver runs non-root but is told to bind port {port}; "
        "a non-root process cannot hold a port under 1024 (Errno 13, 2026-09-02)"
    )


def test_the_readiness_probe_knocks_on_the_bind_port():
    values, _ = release_values()
    web = values["dagsterWebserver"]
    bind = web.get("service", {}).get("port", 80)
    probe = web["readinessProbe"]["httpGet"]["port"]
    assert probe == bind, (
        f"readinessProbe knocks on {probe} but the webserver binds {bind}; "
        "the chart comment says to move the probes with the port"
    )


def test_the_service_still_answers_on_port_80_outside():
    _, spec = release_values()
    patches = []
    for pr in spec.get("postRenderers", []):
        patches.extend(pr.get("kustomize", {}).get("patches", []))
    for entry in patches:
        tgt = entry.get("target", {})
        if (
            tgt.get("kind") == "Service"
            and tgt.get("name") == "dagster-dagster-webserver"
        ):
            ops = yaml.safe_load(entry["patch"])
            assert {"op": "replace", "path": "/spec/ports/0/port", "value": 80} in ops
            return
    raise AssertionError(
        "no postRenderer patch keeps the webserver Service on port 80; the bind moved "
        "to 3000 and without this patch every consumer of :80 goes dark"
    )
