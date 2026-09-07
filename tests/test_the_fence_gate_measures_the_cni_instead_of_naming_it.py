"""The live fence gate's CNI answer must come from the cluster's state, not a DaemonSet's name.

`enforcing_cni` used to return the first kube-system DaemonSet whose name contained "calico",
"cilium" and so on. That answered identically for a CNI with two ready pods and one with none,
and it could not see a second CNI running beside it. On 2026-09-07 the estate was in exactly the
state it could not see: `calico-node` ready 2/2 in kube-system while `kube-flannel-ds` was also
ready 2/2, so pods created before the rollout were networked by the plugin that ignores every
NetworkPolicy and pods created after it were not -- and the gate reported "calico is on the nodes
to enforce the deny" for all of them.
"""

import importlib.machinery
import importlib.util
import json
import pathlib

import pytest

GATE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "ns-fence-gate"


def _gate():
    loader = importlib.machinery.SourceFileLoader("ns_fence_gate", str(GATE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _ds(name, ready, want):
    return {
        "metadata": {"name": name},
        "status": {"numberReady": ready, "desiredNumberScheduled": want},
    }


def _cluster(monkeypatch, mod, *daemonsets):
    class Done:
        stdout = json.dumps({"items": list(daemonsets)})

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: Done())


@pytest.fixture
def mod():
    return _gate()


def test_a_lone_enforcing_cni_ready_everywhere_is_the_only_clean_answer(
    monkeypatch, mod
):
    _cluster(monkeypatch, mod, _ds("calico-node", 2, 2))
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert problems == []


def test_no_enforcing_cni_at_all_is_reported_as_absence_not_as_a_problem(
    monkeypatch, mod
):
    """The caller prints a different, louder verdict for this, so it must not be conflated."""
    _cluster(monkeypatch, mod, _ds("kube-flannel-ds", 2, 2))
    name, problems = mod.enforcing_cni()
    assert name is None
    assert problems == []


def test_an_enforcing_cni_ready_on_some_nodes_disqualifies_the_answer(monkeypatch, mod):
    """Policy holds on the node it is ready on and nowhere else; one cluster-wide line cannot
    carry a per-node answer."""
    _cluster(monkeypatch, mod, _ds("calico-node", 1, 2))
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert any("1 of 2" in p for p in problems)


def test_a_non_enforcing_cni_running_alongside_disqualifies_the_answer(
    monkeypatch, mod
):
    """The state the estate was actually in: whether a policy applies depends on which plugin
    networked the pod, so the fenced namespaces look identical to the unfenced ones."""
    _cluster(monkeypatch, mod, _ds("calico-node", 2, 2), _ds("kube-flannel-ds", 2, 2))
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert len(problems) == 1
    assert "kube-flannel-ds" in problems[0] and "calico-node" in problems[0]


def test_a_drained_non_enforcing_cni_no_longer_disqualifies_it(monkeypatch, mod):
    """After the flannel add-on is disabled its DaemonSet reports zero ready pods. That is the
    end of the cutover, and the gate has to be able to say so or it can never go green."""
    _cluster(monkeypatch, mod, _ds("calico-node", 2, 2), _ds("kube-flannel-ds", 0, 0))
    name, problems = mod.enforcing_cni()
    assert name == "calico-node"
    assert problems == []
