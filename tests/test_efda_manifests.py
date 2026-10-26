"""The scaffold: the CRDs, the schemas, the gate and the Flux row.

The contract layer is what everything else stands on, so its shape is graded
here rather than assumed: five CRDs, five schemas, one admission gate, one
Flux row, one image policy, and one image the estate's own multi-arch gate
can find.
"""

from __future__ import annotations

import json
import os

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(REPO, "platform", "efda")

CRDS = {
    "componentregistration.yaml": "ComponentRegistration",
    "skillpack.yaml": "SkillPack",
    "coveragereport.yaml": "CoverageReport",
    "diagnosticreport.yaml": "DiagnosticReport",
    "remediationartifact.yaml": "RemediationArtifact",
}


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return list(yaml.safe_load_all(handle))


def test_every_crd_exists_and_declares_its_kind():
    for filename, kind in CRDS.items():
        path = os.path.join(PLATFORM, "crds", filename)
        assert os.path.exists(path), path
        documents = load_yaml(path)
        crd = documents[0]
        assert crd["kind"] == "CustomResourceDefinition"
        assert crd["spec"]["names"]["kind"] == kind
        assert crd["spec"]["group"] == "efda.estate"
        assert crd["spec"]["versions"][0]["served"] is True


def test_the_registry_crd_requires_an_owner():
    crd = load_yaml(os.path.join(PLATFORM, "crds", "componentregistration.yaml"))[0]
    spec = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]
    assert "owner" in spec["required"]
    assert spec["properties"]["owner"]["required"] == ["team"]


def test_the_pack_crd_requires_a_budget_and_an_isolation():
    crd = load_yaml(os.path.join(PLATFORM, "crds", "skillpack.yaml"))[0]
    spec = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]
    assert "executionBudget" in spec["required"]
    assert "isolation" in spec["required"]
    budget = spec["properties"]["executionBudget"]
    assert budget["required"] == ["maxCpuMillicores", "maxMemoryMib", "maxWallClockMs"]
    isolation = spec["properties"]["isolation"]
    assert isolation["properties"]["network"]["enum"] == ["none"]
    assert isolation["properties"]["filesystem"]["enum"] == ["none"]


def test_the_pack_crd_caps_the_signature_match_logic():
    crd = load_yaml(os.path.join(PLATFORM, "crds", "skillpack.yaml"))[0]
    spec = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"]["spec"]
    signature = spec["properties"]["signatures"]["items"]
    assert signature["required"] == [
        "id",
        "symptom",
        "matchLogic",
        "cause",
        "confidenceBase",
    ]
    assert signature["properties"]["matchLogic"]["maxLength"] == 4096


def test_the_five_schemas_exist_and_share_the_envelope():
    directory = os.path.join(REPO, "efda", "schemas")
    names = sorted(os.listdir(directory))
    assert names == [
        "diagnostic-artifact-agent.json",
        "diagnostic-artifact-controller.json",
        "diagnostic-artifact-external_dependency.json",
        "diagnostic-artifact-script.json",
        "diagnostic-artifact-workload.json",
    ]
    for name in names:
        with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
            schema = json.load(handle)
        assert schema["type"] == "object"
        for field in (
            "schema_version",
            "identity",
            "failure_boundary",
            "raw_evidence",
            "self_assessment",
            "integrity",
        ):
            assert field in schema["required"], (name, field)
        assert (
            schema["properties"]["failure_boundary"]["properties"]["failure_class"][
                "type"
            ]
            == "string"
        )
        assert (
            "enum"
            not in schema["properties"]["failure_boundary"]["properties"][
                "failure_class"
            ]
        )


def test_the_gate_denies_and_is_scoped_to_enforced_namespaces():
    documents = load_yaml(os.path.join(PLATFORM, "admission", "ncwp.yaml"))
    policy = documents[0]
    binding = documents[1]
    assert policy["kind"] == "ValidatingAdmissionPolicy"
    assert policy["spec"]["failurePolicy"] == "Fail"
    assert binding["spec"]["validationActions"] == ["Deny"]
    assert binding["spec"]["matchResources"]["namespaceSelector"]["matchLabels"] == {
        "efda.estate/enforced": "true"
    }


def test_the_flux_row_exists_and_declares_no_dependency():
    documents = load_yaml(os.path.join(REPO, "clusters", "oke", "platform.yaml"))
    rows = [doc for doc in documents if doc.get("kind") == "Kustomization"]
    efda = [row for row in rows if row["metadata"]["name"] == "efda"]
    assert len(efda) == 1
    row = efda[0]
    assert row["spec"]["path"] == "./platform/efda"
    assert row["metadata"]["annotations"]["idp.estate.io/runtime"] == "always-on"
    assert "dependsOn" not in row["spec"]


def test_the_image_policy_exists_for_the_efda_image():
    documents = load_yaml(
        os.path.join(REPO, "platform", "image-automation", "efda.yaml")
    )
    repository = documents[0]
    policy = documents[1]
    assert repository["spec"]["image"] == "ghcr.io/chidionyema/efda"
    assert policy["spec"]["imageRepositoryRef"]["name"] == "efda"


def test_the_image_carries_the_policy_marker_the_automation_rewrites():
    path = os.path.join(PLATFORM, "kustomization.yaml")
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    kustomization = yaml.safe_load(raw)
    images = kustomization["images"]
    assert images[0]["name"] == "ghcr.io/chidionyema/efda"
    # The marker is a trailing comment on the tag: that is how Flux's
    # image-automation finds the line it owns.
    assert '"$imagepolicy": "flux-system:efda:tag"' in raw


def test_the_dockerfile_builds_both_architectures():
    with open(os.path.join(REPO, "efda.Dockerfile"), "r", encoding="utf-8") as handle:
        dockerfile = handle.read()
    assert "TARGETARCH" in dockerfile
    assert "linux/${TARGETARCH}/kubectl" in dockerfile


def test_the_allowlist_starts_empty():
    documents = load_yaml(os.path.join(PLATFORM, "controller.yaml"))
    configmap = [doc for doc in documents if doc.get("kind") == "ConfigMap"][0]
    assert configmap["metadata"]["name"] == "efda-allowlist"
    allowlist = json.loads(configmap["data"]["allowlist.json"])
    assert allowlist["actions"] == []


def test_the_failure_class_registry_names_the_classes_the_code_uses():
    documents = load_yaml(
        os.path.join(PLATFORM, "configmaps", "failure-class-registry.yaml")
    )
    configmap = documents[0]
    registry = json.loads(configmap["data"]["classes.json"])
    ids = {entry["id"] for entry in registry["classes"]}
    for expected in (
        "hard_kill",
        "exit_nonzero",
        "schema_violation",
        "provider_quota_exhaustion",
    ):
        assert expected in ids


def test_every_workload_pins_a_pod_and_container_security_context():
    """The manifests must satisfy the estate's own trivy config scan.

    MEASURED 2026-10-26: the Greenlane's security-scan on the EFDA candidate failed with five
    HIGH trivy misconfigurations in platform/efda/controller.yaml and platform/efda/namespace.yaml
    (KSV-0118 default security context, KSV-0014 root filesystem not read-only). The findings were
    real: the controller and the executor set a container securityContext but no POD
    securityContext, and the checkpoint Redis set neither. This test is the local proof, so the
    same defect cannot reach the lane a second time. trivy 0.74.0 is what CI runs, and these are
    the settings it requires: KSV-0118 wants a pod-level securityContext, KSV-0014 wants a
    read-only root filesystem.
    """
    workloads = []
    for name in ("controller.yaml", "namespace.yaml"):
        for document in load_yaml(os.path.join(PLATFORM, name)):
            if document.get("kind") in (
                "Deployment",
                "StatefulSet",
                "DaemonSet",
                "Job",
            ):
                workloads.append((name, document))
    assert len(workloads) == 3, "the EFDA scaffold grew or lost a workload: %s" % [
        doc["metadata"]["name"] for _, doc in workloads
    ]
    for name, document in workloads:
        workload = document["metadata"]["name"]
        pod = document["spec"]["template"]["spec"]
        pod_context = pod.get("securityContext") or {}
        assert pod_context.get("runAsNonRoot") is True, (
            "%s %s: no pod-level runAsNonRoot (trivy KSV-0118)" % (name, workload)
        )
        assert pod_context.get("seccompProfile", {}).get("type") == "RuntimeDefault", (
            "%s %s: no pod-level seccompProfile" % (name, workload)
        )
        for container in pod.get("containers", []):
            context = container.get("securityContext") or {}
            assert context.get("readOnlyRootFilesystem") is True, (
                "%s %s: container %s has a writable root filesystem (trivy KSV-0014)"
                % (name, workload, container["name"])
            )
            assert context.get("allowPrivilegeEscalation") is False, (
                "%s %s: container %s can escalate privileges"
                % (name, workload, container["name"])
            )
            assert "ALL" in (context.get("capabilities") or {}).get("drop", []), (
                "%s %s: container %s does not drop every capability"
                % (name, workload, container["name"])
            )
