"""A Kubernetes that exists only for the tests.

The reconciler's job is arithmetic over what it observes: what is registered,
what is covered, what is an orphan. This stub is the observed world -- a
namespace, a workload with a component class, and the custom resources the
reconciler writes -- so the arithmetic can be graded without a cluster.
"""

from __future__ import annotations

import copy
import json

from efda.k8s import COMPONENT_CLASS_ANNOTATION


class FakeKube:
    def __init__(self, workloads=(), namespaces=None, existing=None):
        self.namespaces_seen = namespaces if namespaces is not None else {"default": {}}
        self.workloads = [copy.deepcopy(workload) for workload in workloads]
        self.objects = {}
        for obj in existing or []:
            metadata = obj.get("metadata") or {}
            self.objects[
                (obj.get("kind"), metadata.get("namespace"), metadata.get("name"))
            ] = copy.deepcopy(obj)
        self.applied = []

    # -- the interface the reconciler uses -------------------------------
    def namespaces(self, enforced_only=False):
        if enforced_only:
            return [
                name
                for name, labels in self.namespaces_seen.items()
                if labels.get("efda.estate/enforced") == "true"
            ]
        return sorted(self.namespaces_seen)

    def _namespace_labels(self, name):
        return self.namespaces_seen.get(name, {})

    def observed_workloads(self, namespaces=None):
        found = []
        for workload in self.workloads:
            metadata = workload.get("metadata") or {}
            component_class = (metadata.get("annotations") or {}).get(
                COMPONENT_CLASS_ANNOTATION
            )
            if not component_class:
                continue
            found.append(
                {
                    "resource": "deployments",
                    "kind": "deployment",
                    "namespace": metadata.get("namespace", "default"),
                    "name": metadata.get("name", ""),
                    "uid": metadata.get("uid", ""),
                    "component_class": component_class,
                    "image": "",
                    "labels": metadata.get("labels") or {},
                }
            )
        return found

    def list(self, resource, namespace=None, all_namespaces=False):
        kind = {
            "skillpacks": "SkillPack",
            "componentregistrations": "ComponentRegistration",
            "coveragereports": "CoverageReport",
            "diagnosticreports": "DiagnosticReport",
            "remediationartifacts": "RemediationArtifact",
            "configmaps": "ConfigMap",
            "validatingadmissionpolicies": "ValidatingAdmissionPolicy",
        }.get(resource, resource)
        items = []
        for (obj_kind, obj_ns, _name), obj in self.objects.items():
            if obj_kind != kind:
                continue
            if namespace and obj_ns != namespace:
                continue
            items.append(copy.deepcopy(obj))
        return items

    def get(self, resource, name, namespace=None):
        kind = {
            "skillpacks": "SkillPack",
            "componentregistrations": "ComponentRegistration",
            "coveragereports": "CoverageReport",
            "diagnosticreports": "DiagnosticReport",
            "remediationartifacts": "RemediationArtifact",
            "configmaps": "ConfigMap",
            "validatingadmissionpolicies": "ValidatingAdmissionPolicy",
            "namespaces": "Namespace",
        }.get(resource, resource)
        if kind == "Namespace":
            labels = self.namespaces_seen.get(name)
            if labels is None:
                return None
            return {"kind": "Namespace", "metadata": {"name": name, "labels": labels}}
        obj = self.objects.get((kind, namespace, name))
        return copy.deepcopy(obj) if obj else None

    def apply(self, obj):
        metadata = obj.get("metadata") or {}
        key = (obj.get("kind"), metadata.get("namespace"), metadata.get("name"))
        self.objects[key] = copy.deepcopy(obj)
        self.applied.append(copy.deepcopy(obj))
        return obj

    def update_status(self, obj):
        metadata = obj.get("metadata") or {}
        key = (obj.get("kind"), metadata.get("namespace"), metadata.get("name"))
        stored = self.objects.get(key)
        if stored is not None:
            stored.setdefault("status", {}).update((obj.get("status") or {}))
        self.applied.append(copy.deepcopy(obj))
        return obj

    def annotate(self, kind, namespace, name, annotations):
        key = ("Deployment", namespace, name)
        obj = self.objects.get(key) or {
            "kind": "Deployment",
            "metadata": {"name": name, "namespace": namespace, "annotations": {}},
        }
        obj.setdefault("metadata", {}).setdefault("annotations", {}).update(
            annotations or {}
        )
        self.objects[key] = obj

    def applied_of_kind(self, kind):
        """Every object of this kind the reconciler wrote, in order."""
        return [obj for obj in self.applied if obj.get("kind") == kind]

    def get_annotations(self, kind, namespace, name):
        obj = self.objects.get(("Deployment", namespace, name))
        if not obj:
            return {}
        return (obj.get("metadata") or {}).get("annotations") or {}

    def run(self, args, stdin=None):
        raise NotImplementedError("the fake kube does not shell out")

    def to_json(self):
        return json.dumps(self.objects, indent=2, sort_keys=True, default=str)


def workload(
    name, namespace="default", component_class="efda-test-workload", labels=None
):
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "uid": f"uid-{name}",
            "annotations": {COMPONENT_CLASS_ANNOTATION: component_class},
            "labels": labels or {},
        },
    }
