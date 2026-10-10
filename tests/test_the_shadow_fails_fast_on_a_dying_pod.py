"""The shadow fails fast on a pod the kubelet has already given up on, and only then.

Incident: every red shadow-verify burned the full 900s CI deadline, because wait_ks reads
only Flux's Kustomization condition and a crash-looping workload holds that in
Progressing -- Flux is retrying, which is its job. The pods were already dead: the
kubelet had backed off, the image ref did not resolve, the Secret did not exist.
Founder, 2026-10-10: "Fail in seconds, not 10 minutes."

A doom state that clears within the grace is waited out: a first pull attempt, a Secret
the vault stand-in has not written yet, an app that retries its way to green. Only a
state that persists past the grace is a verdict, and it carries the pod's own name,
reason and last termination message, so a red run names its culprit instead of a
"timed out waiting for Flux" nobody can act on.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def ks(status, reason, message):
    return {
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": status,
                    "reason": reason,
                    "message": message,
                }
            ],
            "inventory": {"entries": [{"id": "crd"}]},
        }
    }


def drive(monkeypatch, shadow, ks_states, pod_states, clock_step=1.0):
    """Feed wait_ks a Kustomization sequence and a per-poll pod-failure sequence."""
    ks_seq = iter(ks_states)
    pod_seq = iter(pod_states)
    last_ks, last_pod = [ks_states[0]], [pod_states[0]]
    polls = [0]

    def fake_status(name):
        last_ks[0] = next(ks_seq, last_ks[0])
        return last_ks[0]

    def fake_pods():
        last_pod[0] = next(pod_seq, last_pod[0])
        polls[0] += 1
        return last_pod[0]

    now = [0.0]
    monkeypatch.setattr(shadow, "ks_status", fake_status)
    monkeypatch.setattr(shadow, "pod_failures", fake_pods)
    monkeypatch.setattr(shadow.time, "time", lambda: now[0])
    monkeypatch.setattr(
        shadow.time, "sleep", lambda s: now.__setitem__(0, now[0] + clock_step)
    )
    return polls


PROGRESSING = ks("False", "Progressing", "reconciliation in progress")
CRASHLOOP = [
    "pod default/llm-0 container llm is CrashLoopBackOff "
    "(restarts 6): Back-off restarting failed container"
]
MISSING_SECRET = [
    "pod default/llm-0 container llm is CreateContainerConfigError (restarts 2): "
    'secret "llm-api-key" not found'
]


def test_a_pod_past_rescue_ends_the_run_in_seconds(monkeypatch):
    shadow = load_shadow()
    polls = drive(
        monkeypatch, shadow, [PROGRESSING], [[]] + [CRASHLOOP] * 20, clock_step=5.0
    )
    ready, msg, inv = shadow.wait_ks("shadow-platform-llm", 900)
    assert not ready
    assert "pods past rescue" in msg and "CrashLoopBackOff" in msg
    # The old behaviour held this out to the 900s deadline; the watch ends it at the
    # grace. 7 polls x 5s is ~35s, against 180 polls to time out.
    assert polls[0] < 15, f"took {polls[0]} polls; the watch did not end the run early"


def test_a_missing_secret_names_the_secret(monkeypatch):
    shadow = load_shadow()
    drive(
        monkeypatch, shadow, [PROGRESSING], [[]] + [MISSING_SECRET] * 20, clock_step=5.0
    )
    ready, msg, _ = shadow.wait_ks("shadow-platform-llm", 900)
    assert not ready
    assert 'secret "llm-api-key" not found' in msg
    assert "CreateContainerConfigError" in msg


def test_a_state_that_clears_within_the_grace_is_waited_out(monkeypatch):
    shadow = load_shadow()
    applied = ks("True", "ReconciliationSucceeded", "Applied revision main@sha1:378b")
    drive(
        monkeypatch,
        shadow,
        [PROGRESSING, PROGRESSING, applied],
        [[], MISSING_SECRET, []],
        clock_step=5.0,
    )
    ready, msg, inv = shadow.wait_ks("shadow-platform-llm", 900)
    assert ready, msg
    assert msg.startswith("Applied revision")
    assert inv == [{"id": "crd"}]


def test_a_healthy_run_is_never_accused(monkeypatch):
    shadow = load_shadow()
    applied = ks("True", "ReconciliationSucceeded", "Applied revision main@sha1:378b")
    drive(monkeypatch, shadow, [PROGRESSING, applied], [[], []], clock_step=5.0)
    ready, msg, _ = shadow.wait_ks("shadow-platform-llm", 900)
    assert ready, msg


def test_pods_that_cannot_be_listed_are_not_a_verdict(monkeypatch):
    shadow = load_shadow()

    def blind():
        return []

    now = [0.0]
    monkeypatch.setattr(shadow, "ks_status", lambda name: PROGRESSING)
    monkeypatch.setattr(shadow, "pod_failures", blind)
    monkeypatch.setattr(shadow.time, "time", lambda: now[0])
    monkeypatch.setattr(
        shadow.time, "sleep", lambda s: now.__setitem__(0, now[0] + 10.0)
    )
    ready, msg, _ = shadow.wait_ks("shadow-platform-llm", 100)
    assert not ready
    assert "timed out" in msg
