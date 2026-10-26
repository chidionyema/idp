"""The estate's Kubernetes door, as the EFDA controllers use it.

One client, one mechanism: ``kubectl``. It is present on the laptop, it is
present in the estate's images, and it speaks the same API server the estate
already trusts -- so there is no second credential path and no second opinion
about what the cluster holds.

The controllers read and write only their own custom resources (the registry,
the packs, the reports). The admission gates and the static manifests belong
to Flux, not to this module.
"""

from __future__ import annotations

import json
import os
import subprocess

WORKLOAD_RESOURCES = ("deployments", "statefulsets", "daemonsets", "jobs", "cronjobs")

KIND_TO_RESOURCE = {
    "deployment": "deployments",
    "statefulset": "statefulsets",
    "daemonset": "daemonsets",
    "job": "jobs",
    "cronjob": "cronjobs",
    "componentregistration": "componentregistrations",
    "skillpack": "skillpacks",
    "coveragereport": "coveragereports",
    "diagnosticreport": "diagnosticreports",
    "remediationartifact": "remediationartifacts",
}

COMPONENT_CLASS_ANNOTATION = "efda.estate/component-class"
ENFORCED_NAMESPACE_LABEL = "efda.estate/enforced"


class KubeError(Exception):
    pass


class KubeClient:
    """A thin, honest wrapper over ``kubectl``."""

    def __init__(self, kubeconfig=None, namespace=None, timeout=30):
        self.kubeconfig = kubeconfig or os.environ.get("KUBECONFIG", "")
        self.namespace = namespace or os.environ.get("EFDA_NAMESPACE", "efda-system")
        self.timeout = timeout

    # -- plumbing --------------------------------------------------------
    def run(self, args, stdin=None):
        command = ["kubectl", "--request-timeout=%ds" % self.timeout]
        if self.kubeconfig:
            command = ["env", f"KUBECONFIG={self.kubeconfig}"] + command
        command += list(args)
        try:
            completed = subprocess.run(  # noqa: S603 -- fixed argv, no shell
                command,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise KubeError(f"kubectl {args[0]} failed: {exc}") from exc
        if completed.returncode != 0:
            raise KubeError(
                completed.stderr.strip() or completed.stdout.strip() or "kubectl failed"
            )
        return completed.stdout

    # -- reads -----------------------------------------------------------
    def list(self, resource, namespace=None, all_namespaces=False):
        args = ["get", resource]
        if all_namespaces:
            args.append("-A")
        elif namespace:
            args += ["-n", namespace]
        args += ["-o", "json"]
        payload = json.loads(self.run(args) or "{}")
        return payload.get("items") or []

    def get(self, resource, name, namespace=None):
        args = ["get", resource, name]
        if namespace:
            args += ["-n", namespace]
        args += ["-o", "json"]
        try:
            return json.loads(self.run(args) or "{}")
        except KubeError:
            return None

    def get_annotations(self, kind, namespace, name):
        resource = KIND_TO_RESOURCE.get(str(kind).lower(), f"{kind}s")
        obj = self.get(resource, name, namespace)
        if not obj:
            return {}
        return (obj.get("metadata") or {}).get("annotations") or {}

    # -- writes ----------------------------------------------------------
    def apply(self, obj):
        payload = json.dumps(obj)
        self.run(["apply", "-f", "-"], stdin=payload)
        return obj

    def apply_many(self, objects):
        for obj in objects:
            self.apply(obj)

    def annotate(self, kind, namespace, name, annotations):
        resource = KIND_TO_RESOURCE.get(str(kind).lower(), f"{kind}s")
        args = ["annotate", resource, name, "-n", namespace, "--overwrite"]
        for key, value in (annotations or {}).items():
            args.append(f"{key}={value}")
        self.run(args)

    def update_status(self, obj):
        payload = json.dumps(obj)
        self.run(["apply", "-f", "-", "--subresource=status"], stdin=payload)
        return obj

    # -- domain helpers --------------------------------------------------
    def observed_workloads(self, namespaces=None):
        """Every workload that declares a component class.

        A workload without the annotation is not a component the estate has
        been told about; the reconciler reports those separately as
        unannotated, and the NCWP gate refuses them in enforced namespaces.
        """
        found = []
        namespaces = namespaces or [None]
        for namespace in namespaces:
            for resource in WORKLOAD_RESOURCES:
                for item in self.list(resource, namespace=namespace):
                    metadata = item.get("metadata") or {}
                    annotations = metadata.get("annotations") or {}
                    component_class = annotations.get(COMPONENT_CLASS_ANNOTATION)
                    if not component_class:
                        continue
                    found.append(
                        {
                            "resource": resource,
                            "kind": resource.rstrip("s"),
                            "namespace": metadata.get("namespace", "default"),
                            "name": metadata.get("name", ""),
                            "uid": metadata.get("uid", ""),
                            "component_class": component_class,
                            "image": _first_image(item),
                            "labels": metadata.get("labels") or {},
                        }
                    )
        return found

    def namespaces(self, enforced_only=False):
        selector = f"{ENFORCED_NAMESPACE_LABEL}=true" if enforced_only else ""
        args = ["get", "namespaces"]
        if selector:
            args += ["-l", selector]
        args += ["-o", "json"]
        payload = json.loads(self.run(args) or "{}")
        return [
            item.get("metadata", {}).get("name", "")
            for item in payload.get("items") or []
        ]


def _first_image(item):
    spec = item.get("spec") or {}
    template = spec.get("template") or {}
    containers = ((template.get("spec") or {}).get("containers")) or []
    if containers:
        return containers[0].get("image", "")
    return ""


def cluster_name():
    """The cluster identity an artifact is addressed under."""
    return os.environ.get("EFDA_CLUSTER", "oke")
