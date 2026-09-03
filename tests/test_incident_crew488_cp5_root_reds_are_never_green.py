"""crew#488 CP5: the portability drill graded 2/38 as ok, because it could not tell a cause from a cascade.

Run 33208911991 (2026-08-28): four layers broke for reasons of their own (a ClusterPolicy applied
before Kyverno's CRD, an ExternalSecret before ESO's, the vault ConfigMap, the private catalog
artifact), thirty-two fell behind them with Flux's "dependency X is not ready", and the line read
`ok portability ready 2/38 (floor 2)`. The floor was met, the tree was broken, and nothing said so.

The grader now names each red: `cascaded` (a row above is red), `oci-red` (a reason of its own that
drills/portability-oci-reds.txt names for that layer), or `ROOT-RED` (a reason of its own nobody has
named), and a ROOT-RED FAILS the run whatever the floor says. Proved both ways per LAW 45 step 3.
The tree fixes that turned the four roots into two honest reds are proved by the drill's own run on
the branch (the PR carries the URL); this file proves the grader, and that the two remaining roots
are on the list and every ClusterPolicy in the tree is applied by some layer.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader(
    "drill", str(ROOT / "bin" / "idp-portability-drill")
)
drill = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("drill", _loader)
)
_loader.exec_module(drill)

REDS = drill.read_reds(str(ROOT / "drills" / "portability-oci-reds.txt"))
CASCADE = "dependency 'flux-system/secret-store' is not ready"


def _ks(name: str, ready: bool, msg: str = "") -> dict:
    return {
        "metadata": {"name": name, "namespace": "flux-system"},
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "True" if ready else "False",
                    "message": msg,
                }
            ]
        },
    }


def test_a_reds_row_without_a_reason_is_refused(tmp_path):
    p = tmp_path / "reds.txt"
    p.write_text("secret-store\n")
    try:
        drill.read_reds(str(p))
    except ValueError as e:
        assert "root-red" in str(e)
    else:
        raise AssertionError("a layer with no reason was accepted")


def _layer_paths() -> dict[str, str]:
    out = {}
    for f in sorted((ROOT / "clusters" / "oke").glob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if (
                d
                and d.get("kind") == "Kustomization"
                and str((d.get("spec") or {}).get("path", "")).startswith("./platform/")
            ):
                out[d["metadata"]["name"]] = d["spec"]["path"]
    return out


def test_the_two_remaining_roots_are_the_vault_and_the_private_catalog():
    assert [layer for layer, _ in REDS] == ["secret-store", "estate-catalog"], REDS


def test_the_security_page_lists_exactly_the_policies_the_tree_applies():
    """Founder 2026-08-28: the crew must never be confused about how security works. The page
    carries bin/idp-admission-policies' table verbatim; a hand edit or a new policy without a
    regenerate is red, and a policy in no layer is red in the command itself."""
    import subprocess

    r = subprocess.run(
        [str(ROOT / "bin" / "idp-admission-policies")], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout
    page = (ROOT / "docs" / "reference" / "security-policy.md").read_text()
    begin, end = (
        "<!-- admission-policies:begin -->\n",
        "<!-- admission-policies:end -->",
    )
    assert begin in page and end in page
    assert page.split(begin, 1)[1].split(end, 1)[0] == r.stdout, (
        "page table differs from bin/idp-admission-policies; regenerate"
    )


def docs(rel: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((ROOT / rel).read_text()) if d]


def test_the_priority_classes_exist_before_the_front_door_names_one():
    """Runs 33212542369/33212575403: traefik names infrastructure-critical, the class lived in
    `scheduling`, and scheduling waited on edge. A fresh cluster deadlocked; OKE only escaped
    because the class predated the dependsOn."""
    plat = {d["metadata"]["name"]: d for d in docs("clusters/oke/platform.yaml")}
    edge = {d["metadata"]["name"]: d for d in docs("clusters/oke/edge.yaml")}
    pc = plat["priority-classes"]["spec"]
    assert pc["path"] == "./platform/priority-classes" and "dependsOn" not in pc
    assert "priority-classes" in {d["name"] for d in edge["edge"]["spec"]["dependsOn"]}
    assert "priority-classes" in {
        d["name"] for d in plat["scheduling"]["spec"]["dependsOn"]
    }
    names = {
        d["metadata"]["name"]
        for d in docs("platform/priority-classes/priorityclasses.yaml")
    }
    assert "infrastructure-critical" in names
    assert (
        "priorityclasses.yaml"
        not in yaml.safe_load(
            (ROOT / "platform/scheduling/kustomization.yaml").read_text()
        )["resources"]
    )


def _spec(row: str) -> dict:
    for f in sorted((ROOT / "clusters" / "oke").glob("*.yaml")):
        for d in docs(f"clusters/oke/{f.name}"):
            if (
                d.get("kind") == "Kustomization"
                and str(d.get("apiVersion", "")).startswith("kustomize.toolkit")
                and d["metadata"]["name"] == row
            ):
                return d["spec"]
    raise AssertionError(f"no Kustomization {row}")


def _depends_on(row: str) -> set[str]:
    return {d["name"] for d in _spec(row).get("dependsOn", [])}


def _ready(name: str) -> dict:
    return _ks(name, True)


def test_a_row_flux_has_not_judged_yet_is_pending_not_a_root():
    """Run 33214748124: observability sat at Ready=Unknown/Progressing and was graded ROOT-RED.
    Not ready, not a root: it counts as pending and never fails the run on its own."""
    items = [
        _ready("edge"),
        _ready("kyverno"),
        {
            "metadata": {"name": "observability", "namespace": "flux-system"},
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "Unknown",
                        "reason": "Progressing",
                        "message": "Reconciliation in progress",
                    }
                ]
            },
        },
    ]
    verdict, lines = drill.grade(items, 2)
    assert verdict.startswith("ok"), verdict
    assert "pending 1" in verdict
    assert any(
        line.startswith("  pending    flux-system/observability") for line in lines
    )
    assert not any("ROOT-RED" in line for line in lines)


def test_the_rows_that_write_into_backstage_wait_for_the_namespace_and_never_for_the_portal():
    """Run 33214748124: cluster-state and spire applied ServiceAccount/CronJob into namespace
    backstage before the backstage row created it -> 'namespaces "backstage" not found'.

    They wait for `backstage-namespace`, not for `backstage`. The portal row carries `wait: true`
    with a healthCheck on Deployment/catalogue, so waiting on it is crew#539 verbatim -- a stalled
    catalogue rollout holding fifteen Kustomizations Not Ready -- and
    tests/test_incident_crew539_platform_rows_never_wait_on_the_portal.py refuses that edge. The
    namespace is its own row precisely so both rules hold at once.
    """
    for row in ("cluster-state", "spire", "image-automation"):
        deps = _depends_on(row)
        assert "backstage-namespace" in deps, (row, deps)
        assert "backstage" not in deps, (row, deps)
    assert _depends_on("backstage-namespace") == set(), (
        "the namespace layer waits for nothing"
    )
    assert "backstage-namespace" in _depends_on("backstage"), (
        "the portal waits for its namespace"
    )


def test_the_singleton_dns_controller_is_excepted_from_runs_two_by_name():
    """Run 33214748124: require-availability denied external-dns (one replica by design)."""
    exc = docs("platform/edge/external-dns-exception.yaml")[0]
    assert exc["spec"]["exceptions"][0]["policyName"] == "require-availability"
    assert exc["spec"]["match"]["any"][0]["resources"]["names"] == ["external-dns"]
    assert exc["spec"]["match"]["any"][0]["resources"]["kinds"] == ["Deployment"]
    assert (
        "external-dns-exception.yaml"
        in docs("platform/edge/kustomization.yaml")[0]["resources"]
    )


def test_rows_behind_a_booting_webhook_retry_in_a_minute_not_ten():
    """Run 33214748124: ESO's webhook answered 'ca cert not yet ready' once; the next try was 10m."""
    for row in ("prospector-platform", "dns"):
        assert _spec(row).get("retryInterval") == "1m", row


def test_dns_waits_for_the_row_that_makes_its_secret_and_the_k3s_agent_shares_its_mounts():
    """Run 33216301296: external-dns mounts cloudflare-api-token (an ExternalSecret in
    platform/prospector) -> dns waits on prospector-platform; cilium-agent on the k3s agent needed
    /var/run rshared ('not a shared or slave mount')."""
    assert "prospector-platform" in _depends_on("dns")
    assert (
        "cloudflare-api-token"
        in (ROOT / "platform/prospector/cloudflare-external-secret.yaml").read_text()
    )
    wf = (ROOT / ".github/workflows/portability-drill.yml").read_text()
    assert "mount --make-rshared /var/run" in wf
