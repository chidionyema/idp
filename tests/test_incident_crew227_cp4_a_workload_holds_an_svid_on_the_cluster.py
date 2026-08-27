"""crew#227 CP4, incident: the first cluster-state receipt with the spiffe rows (oke-check apply
33042911059, 2026-08-27T05:30Z) showed 59 registered entries and `csi_workloads: []`: registration
without possession, because nothing on OKE mounted the SPIFFE CSI socket. The proof workload existed
only as a one-shot k3d Job. Rule: the spire Kustomization ships a CronJob in the backstage namespace
that mounts csi.spiffe.io and asks the Workload API for an X.509 SVID, under the restricted PSA
profile, and the receipt's csi_workloads selector matches it. Both ways: the same selector rejects a
pod with an emptyDir in the same slot."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPIRE = ROOT / "platform" / "spire"


def _csi_mounting(pod_spec) -> bool:
    # the selector platform/state/cluster-state.yaml uses for spiffe.csi_workloads, verbatim
    return any((v.get("csi") or {}).get("driver") == "csi.spiffe.io" for v in (pod_spec.get("volumes") or []))


def test_the_spire_tree_ships_a_cronjob_that_holds_an_svid_and_the_receipt_selector_matches_it():
    kust = yaml.safe_load((SPIRE / "kustomization.yaml").read_text())
    assert "proof-cronjob.yaml" in kust["resources"]
    cj = yaml.safe_load((SPIRE / "proof-cronjob.yaml").read_text())
    assert cj["kind"] == "CronJob" and cj["metadata"]["namespace"] == "backstage"
    pod = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert _csi_mounting(pod)
    fetch = pod["containers"][0]
    assert fetch["command"][:4] == ["/opt/spire/bin/spire-agent", "api", "fetch", "x509"]
    # restricted PSA: the backstage namespace enforces it, so a non-compliant pod never starts
    assert pod["securityContext"]["runAsNonRoot"] is True
    assert pod["securityContext"]["seccompProfile"] == {"type": "RuntimeDefault"}
    assert fetch["securityContext"]["allowPrivilegeEscalation"] is False
    assert fetch["securityContext"]["capabilities"] == {"drop": ["ALL"]}
    # the other way: a pod with no CSI volume is not a workload that can hold an SVID
    assert not _csi_mounting({"volumes": [{"name": "spiffe-workload-api", "emptyDir": {}}]})
