"""The registry reconciler (G3)."""

from __future__ import annotations

from efda.reconciler import (
    NCWP_POLICY_NAME,
    SNAPSHOT_NAME,
    build_snapshot,
    ncwp_expression,
    reconcile,
)
from efda.packs import pack_spec

from efda_fake_kube import FakeKube, workload


def a_cluster():
    kube = FakeKube(
        workloads=[workload("observed-001", component_class="efda-test-workload")],
        namespaces={"default": {"efda.estate/enforced": "true"}},
    )
    return kube


def test_an_observed_workload_is_registered_and_covered():
    kube = a_cluster()
    summary = reconcile(kube, namespace="efda-system")
    registrations = kube.list("componentregistrations", all_namespaces=True)
    assert len(registrations) == 1
    assert registrations[0]["spec"]["componentClass"] == "efda-test-workload"
    assert registrations[0]["status"]["coverageState"] == "BASELINE"
    assert registrations[0]["status"]["packRef"]
    assert registrations[0]["status"]["compliant"] is True
    assert summary["packs_created"] == 1


def test_a_baseline_pack_is_generated_for_the_class():
    kube = a_cluster()
    reconcile(kube, namespace="efda-system")
    packs = kube.list("skillpacks", all_namespaces=True)
    assert len(packs) == 1
    assert pack_spec(packs[0])["coverageTier"] == "baseline"


def test_the_coverage_report_is_published():
    kube = a_cluster()
    reconcile(kube, namespace="efda-system")
    report = kube.get("coveragereports", "latest", namespace="efda-system")
    assert report["spec"]["counts"]["observed"] == 1
    assert report["spec"]["counts"]["BASELINE"] == 1
    assert report["spec"]["nonCompliant"] == []


def test_the_registry_snapshot_names_every_class():
    kube = a_cluster()
    reconcile(kube, namespace="efda-system")
    snapshot = kube.get("configmaps", SNAPSHOT_NAME, namespace="efda-system")
    assert "efda-test-workload" in snapshot["data"]["registry.json"]


def test_a_registration_whose_workload_left_the_cluster_is_an_orphan():
    kube = a_cluster()
    reconcile(kube, namespace="efda-system")
    kube.workloads = []
    summary = reconcile(kube, namespace="efda-system")
    registrations = kube.list("componentregistrations", all_namespaces=True)
    assert registrations[0]["status"]["coverageState"] == "ORPHAN"
    assert registrations[0]["status"]["compliant"] is False
    assert summary["orphans"] == 1


def test_the_gate_expression_carries_the_registered_classes():
    expression = ncwp_expression(["efda-test-agent", "efda-test-workload"])
    assert "efda.estate/component-class" in expression
    assert "'efda-test-agent'" in expression
    assert "'efda-test-workload'" in expression


def test_the_gate_is_rewritten_only_when_the_classes_change():
    kube = a_cluster()
    kube.objects[("ValidatingAdmissionPolicy", None, NCWP_POLICY_NAME)] = {
        "apiVersion": "admissionregistration.k8s.io/v1",
        "kind": "ValidatingAdmissionPolicy",
        "metadata": {"name": NCWP_POLICY_NAME},
        "spec": {"validations": [{"expression": "old"}]},
    }
    reconcile(kube, namespace="efda-system")
    policy = kube.get("validatingadmissionpolicies", NCWP_POLICY_NAME)
    assert "efda-test-workload" in policy["spec"]["validations"][0]["expression"]
    written = len(kube.applied_of_kind("ValidatingAdmissionPolicy"))
    assert written == 1
    reconcile(kube, namespace="efda-system")
    assert len(kube.applied_of_kind("ValidatingAdmissionPolicy")) == written


def test_the_snapshot_names_the_packs_that_cover_a_class():
    kube = a_cluster()
    reconcile(kube, namespace="efda-system")
    snapshot = build_snapshot(
        {
            pack["metadata"]["name"]: pack
            for pack in kube.list("skillpacks", all_namespaces=True)
        }
    )
    entry = snapshot["classes"]["efda-test-workload"]
    assert entry["packs"][0]["tier"] == "baseline"
    assert entry["packs"][0]["digest"].startswith("sha256:")
