"""Incident 2026-08-26 (crew#292 CP4): platform/chaos/mesh/helmrelease.yaml runs Chaos Mesh with
enableFilterNamespace: true, and the backstage-pod-kill Schedule targeted namespace backstage,
whose manifest carried no chaos-mesh.org/inject=enabled label. The Schedule was accepted, the
Flux rows read Ready, and the experiment would never have injected anything.
Rule (rung 4): when the chart filters namespaces, every namespace a chaos-mesh.org object
selects is declared in git with the inject label."""

import glob
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
INJECT = "chaos-mesh.org/inject"


def _docs(pattern):
    for f in sorted(glob.glob(str(ROOT / pattern), recursive=True)):
        for d in yaml.safe_load_all(open(f)):
            if d:
                yield d


def _filter_on():
    for d in _docs("platform/chaos/mesh/*.yaml"):
        if d.get("kind") == "HelmRelease":
            return bool(d["spec"].get("values", {}).get("enableFilterNamespace"))
    return False


def _target_namespaces(docs):
    """Namespaces any chaos-mesh.org object lives in or selects."""
    out = set()
    for d in docs:
        if not str(d.get("apiVersion", "")).startswith("chaos-mesh.org/"):
            continue
        out.add(d["metadata"].get("namespace"))
        text = yaml.safe_dump(d)
        for chunk in (
            yaml.safe_load(text)
            .get("spec", {})
            .get("workflow", {})
            .get("templates", [])
        ):
            for sel in (
                (chunk.get("podChaos") or {}).get("selector", {}).get("namespaces", [])
            ):
                out.add(sel)
    return {n for n in out if n}


def _labelled_namespaces(docs):
    return {
        d["metadata"]["name"]
        for d in docs
        if d.get("kind") == "Namespace"
        and d["metadata"].get("labels", {}).get(INJECT) == "enabled"
    }


def _unlabelled(docs, filter_on):
    if not filter_on:
        return []
    return sorted(_target_namespaces(docs) - _labelled_namespaces(docs))


def test_the_incident_shape_is_refused_and_the_fixed_shape_permitted():
    sched = {
        "apiVersion": "chaos-mesh.org/v1alpha1",
        "kind": "Schedule",
        "metadata": {"name": "backstage-pod-kill", "namespace": "backstage"},
        "spec": {
            "workflow": {
                "templates": [{"podChaos": {"selector": {"namespaces": ["backstage"]}}}]
            }
        },
    }
    bare = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": "backstage", "labels": {}},
    }
    labelled = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": "backstage", "labels": {INJECT: "enabled"}},
    }
    assert _unlabelled([sched, bare], True) == ["backstage"]
    assert _unlabelled([sched, labelled], True) == []
    assert _unlabelled([sched, bare], False) == []
