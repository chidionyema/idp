"""crew#631 CP2 (founder, 2026-08-31: "what do you mean by live"). The prover side of the verdict
key was measured (estate-ci stored a signed row); the refusal side was UNKNOWN, because nothing
had ever asked for `verdict-hmac-key` as a non-prover. The probe is an ExternalSecret that asks
for exactly that key as the cluster's pods and must stay refused. Three things make it a
measurement rather than a wish: it lives in its own never-waiting Flux row (a `wait: true` row
would hold red forever on a probe doing its job), the cluster-state collector inverts its Ready
condition through the estate/expect-ready annotation (so the estate page reads a breach as red
and a refusal as green), and bin/idp-verdict key-wall reads the same object on every prover run.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROBE = ROOT / "platform/verification/verdict-key-wall.yaml"
ROW = ROOT / "clusters/oke/verification.yaml"


def _docs(p):
    return [d for d in yaml.safe_load_all(p.read_text()) if d]


def test_the_probe_asks_for_the_signing_key_as_a_pod_and_says_it_expects_refusal():
    es = next(d for d in _docs(PROBE) if d["kind"] == "ExternalSecret")
    assert (
        es["metadata"]["name"] == "verdict-key-wall"
        and es["metadata"]["namespace"] == "backstage"
    )
    assert es["metadata"]["annotations"]["estate/expect-ready"] == "false"
    assert es["spec"]["secretStoreRef"] == {
        "kind": "ClusterSecretStore",
        "name": "estate-vault",
    }
    assert [d["remoteRef"]["key"] for d in es["spec"]["data"]] == ["verdict-hmac-key"]
    # the control (a permitted key, same store) sits beside it in the portal's row
    ctrl = next(
        d
        for d in _docs(
            ROOT / "platform/backstage/overlays/oke/backstage-external-secret.yaml"
        )
        if d["kind"] == "ExternalSecret"
    )
    assert (
        ctrl["spec"]["secretStoreRef"]["name"] == "estate-vault"
        and ctrl["metadata"]["namespace"] == "backstage"
    )


def test_the_probe_lives_in_a_row_that_never_waits():
    row = next(d for d in _docs(ROW) if d["kind"] == "Kustomization")
    assert (
        row["metadata"]["name"] == "verification"
        and row["spec"]["path"] == "./platform/verification"
    )
    assert row["spec"]["wait"] is False and "healthChecks" not in row["spec"]
    deps = {d["name"] for d in row["spec"]["dependsOn"]}
    assert {"external-secrets", "secret-store", "backstage-namespace"} <= deps
    kust = yaml.safe_load(
        (ROOT / "platform/verification/kustomization.yaml").read_text()
    )
    assert kust["resources"] == ["verdict-key-wall.yaml"]
    # and NOT in the portal's wait:true row, where a refused probe would hold the portal red
    overlay = (ROOT / "platform/backstage/overlays/oke/kustomization.yaml").read_text()
    assert "verdict-key-wall" not in overlay


def _collect_py():
    docs = _docs(ROOT / "platform/state/cluster-state.yaml")
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]


def test_the_collector_reads_a_refused_probe_as_green_and_a_synced_one_as_red():
    src = _collect_py()
    compile(src, "collect.py", "exec")
    assert 'get("estate/expect-ready") == "false"' in src
    assert 'row["ready"] = not synced' in src
    assert "WALL BREACHED" in src and "wall standing" in src
    # the inversion runs after the ExternalSecret staleness grading, so a stale-sync red cannot
    # flip a refused probe to red or a synced one to green
    assert (
        src.index("stale_sync(o.get")
        < src.index('get("estate/expect-ready")')
        < src.index("flux.append(row)")
    )
    # only a value of "false" inverts: an ordinary object with no annotation is graded as before
    assert src.count('"estate/expect-ready"') == 1


def test_the_row_is_in_the_catalogue_in_plain_english():
    ents = _docs(ROOT / "backstage/platform/catalog-info.yaml")
    comp = next(
        e
        for e in ents
        if e["kind"] == "Component"
        and e["metadata"]["annotations"].get("estate/flux-kustomization")
        == "verification"
    )
    assert comp["metadata"]["title"] == "Verification wall" and comp["metadata"][
        "description"
    ].endswith(".")
