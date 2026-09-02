"""Incident, 2026-09-02: the external-secrets Flux row could never go ready.

The chart's bitwarden-sdk-server pod mounts TLS Secret bitwarden-tls-certs,
but that certificate lived in the human-vault row, which depends on
external-secrets. The row waited on a pod that waited on a secret that
waited on the row: a deadlock (oke-check run 33619832091, twice).

The guard: if the external-secrets HelmRelease enables the
bitwarden-sdk-server subchart, then the certificate the sdk server mounts
must be produced by the same kustomize row (platform/secrets), that row's
Flux Kustomization must depend on edge (which installs the cert-manager
that signs it), and no other platform row may carry the certificate.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(path: pathlib.Path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _sdk_server_enabled() -> bool:
    for doc in _docs(ROOT / "platform/secrets/external-secrets.yaml"):
        if doc.get("kind") == "HelmRelease":
            values = doc.get("spec", {}).get("values", {})
            return bool(values.get("bitwarden-sdk-server", {}).get("enabled"))
    return False


def test_the_sdk_servers_certificate_is_born_in_its_own_row():
    if not _sdk_server_enabled():
        return
    resources = yaml.safe_load(
        (ROOT / "platform/secrets/kustomization.yaml").read_text()
    )["resources"]
    assert "certs.yaml" in resources, (
        "bitwarden-sdk-server is enabled but platform/secrets does not carry "
        "certs.yaml: the row will wait forever on a certificate a dependent "
        "row creates (the 2026-09-02 deadlock)"
    )
    names = {
        d.get("metadata", {}).get("name")
        for d in _docs(ROOT / "platform/secrets/certs.yaml")
    }
    assert "bitwarden-tls-certs" in names, (
        "platform/secrets/certs.yaml no longer produces bitwarden-tls-certs, "
        "the secret the sdk-server pod mounts"
    )


def test_the_row_names_the_certificate_signer_as_a_dependency():
    if not _sdk_server_enabled():
        return
    rows = [
        d
        for d in _docs(ROOT / "clusters/oke/secrets.yaml")
        if d.get("metadata", {}).get("name") == "external-secrets"
    ]
    assert rows, "clusters/oke/secrets.yaml lost the external-secrets row"
    deps = {x["name"] for x in rows[0]["spec"].get("dependsOn", [])}
    assert "edge" in deps, (
        "the external-secrets row must depend on edge: edge installs the "
        "cert-manager that signs bitwarden-tls-certs, and a clean rebuild "
        "would otherwise apply the Certificate before its CRD exists"
    )


def test_no_dependent_row_carries_the_certificate():
    if not _sdk_server_enabled():
        return
    for kust in (ROOT / "platform").glob("*/kustomization.yaml"):
        if kust.parent.name == "secrets":
            continue
        resources = yaml.safe_load(kust.read_text()).get("resources", [])
        for res in resources:
            target = kust.parent / res
            if not target.is_file():
                continue
            for doc in _docs(target):
                assert doc.get("metadata", {}).get("name") != "bitwarden-tls-certs", (
                    f"{target.relative_to(ROOT)} produces bitwarden-tls-certs; "
                    "the sdk server's certificate must ride the "
                    "external-secrets row alone or the deadlock returns"
                )
