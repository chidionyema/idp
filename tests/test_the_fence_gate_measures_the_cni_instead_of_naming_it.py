"""The live fence gate's CNI answer must come from the cluster's state, not a DaemonSet's name.

`enforcing_cni` used to return the first kube-system DaemonSet whose name contained "calico",
"cilium" and so on. That answered identically for a CNI with two ready pods and one with none,
and it could not see a second plugin running beside it.

The first fix over-corrected: it failed the whole cluster whenever a non-enforcing DaemonSet was
ready. On a managed cluster that is permanently red and therefore grades nothing -- OKE ships
flannel as an add-on and refuses add-on removal on a basic cluster, so `kube-flannel-ds` runs
regardless of what the datapath is doing. What decides the datapath is which plugin wired each
pod, and the pod carries that answer as an annotation. These tests grade the returned tuple
against a faked cluster.
"""

import importlib.machinery
import importlib.util
import json
import pathlib

import pytest

GATE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "ns-fence-gate"
CALICO = "cni.projectcalico.org/podIP"


def _gate():
    loader = importlib.machinery.SourceFileLoader("ns_fence_gate", str(GATE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def mod():
    return _gate()


def _ds(name, ready, want):
    return {
        "metadata": {"name": name},
        "status": {"numberReady": ready, "desiredNumberScheduled": want},
    }


def _pod(ns, name, *, wired=True, host=False, phase="Running"):
    ann = {CALICO: "10.244.0.5/32"} if wired else {}
    return {
        "metadata": {"name": name, "namespace": ns, "annotations": ann},
        "spec": {"hostNetwork": host},
        "status": {"phase": phase},
    }


def _cluster(monkeypatch, mod, daemonsets, pods=()):
    """Answer `kubectl get daemonset` and `kubectl get pods` from fixtures, by argv."""

    def fake(argv, **kwargs):
        items = list(pods) if "pods" in argv else list(daemonsets)

        class Done:
            stdout = json.dumps({"items": items})

        return Done()

    monkeypatch.setattr(mod.subprocess, "run", fake)


def test_a_lone_enforcing_cni_that_wired_every_pod_is_the_only_clean_answer(
    monkeypatch, mod
):
    _cluster(
        monkeypatch,
        mod,
        [_ds("calico-node", 2, 2)],
        [_pod("a", "one"), _pod("b", "two")],
    )
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert problems == []


def test_no_enforcing_cni_at_all_is_reported_as_absence_not_as_a_problem(
    monkeypatch, mod
):
    """The caller prints a different, louder verdict for this, so it must not be conflated."""
    _cluster(
        monkeypatch,
        mod,
        [_ds("kube-flannel-ds", 2, 2)],
        [_pod("a", "one", wired=False)],
    )
    name, problems = mod.enforcing_cni()
    assert name is None
    assert problems == []


def test_an_enforcing_cni_ready_on_some_nodes_disqualifies_the_answer(monkeypatch, mod):
    """Policy holds on the node it is ready on and nowhere else; one cluster-wide line cannot
    carry a per-node answer."""
    _cluster(monkeypatch, mod, [_ds("calico-node", 1, 2)], [_pod("a", "one")])
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert any("1 of 2" in p for p in problems)


def test_pods_the_enforcing_cni_did_not_wire_disqualify_the_answer(monkeypatch, mod):
    """The state the estate was actually in: a clean split, both DaemonSets ready, and the fences
    reaching only the pods that happened to start after the rollout."""
    _cluster(
        monkeypatch,
        mod,
        [_ds("calico-node", 2, 2), _ds("kube-flannel-ds", 2, 2)],
        [
            _pod("new", "wired"),
            _pod("old", "stranded", wired=False),
            _pod("old", "stranded-too", wired=False),
        ],
    )
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert len(problems) == 1
    assert "2 running pod(s)" in problems[0]
    assert "old (2)" in problems[0]
    assert "kube-flannel-ds" in problems[0]


def test_a_still_running_flannel_daemonset_alone_does_not_fail_the_gate(
    monkeypatch, mod
):
    """A managed add-on cannot be removed on a basic OKE cluster, so failing on its presence would
    make the gate permanently red. Once every pod is wired by the enforcing CNI, the datapath is
    the enforcing CNI's whatever else is installed."""
    _cluster(
        monkeypatch,
        mod,
        [_ds("calico-node", 2, 2), _ds("kube-flannel-ds", 2, 2)],
        [_pod("a", "one"), _pod("b", "two")],
    )
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert problems == []


def test_host_network_and_finished_pods_are_not_counted_as_gaps(monkeypatch, mod):
    """hostNetwork pods share the node's stack and are outside every NetworkPolicy by
    construction; a Completed pod has no datapath left to grade. Counting either would leave a
    gap that no restart could ever close."""
    _cluster(
        monkeypatch,
        mod,
        [_ds("calico-node", 2, 2)],
        [
            _pod("a", "wired"),
            _pod("kube-system", "host-thing", wired=False, host=True),
            _pod("jobs", "finished", wired=False, phase="Succeeded"),
        ],
    )
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert problems == []


def test_an_enforcing_cni_with_no_measured_annotation_fails_rather_than_passes(
    monkeypatch, mod
):
    """Fail closed: a coverage claim this gate cannot grade is not a pass."""
    _cluster(monkeypatch, mod, [_ds("cilium", 2, 2)], [_pod("a", "one", wired=False)])
    name, problems = mod.enforcing_cni()
    assert name == "cilium"
    assert len(problems) == 1
    assert "CNI_POD_ANNOTATION" in problems[0]
