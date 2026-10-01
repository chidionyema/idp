"""silence-audit grades what the founder's law names: a workload with no evaluated alert is SILENT,
a workload that should run and does not is DEAD, a KEDA-parked zero is PARKED, and a dead pipeline
makes every workload SILENT whatever its rules say (2026-09-30: 0/0 on all four, 126 rules unread).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SRC = (
    Path(__file__).resolve().parents[1]
    / "platform"
    / "estate"
    / "libexec"
    / "silence-audit.py"
)
spec = importlib.util.spec_from_file_location("silence_audit", SRC)
sa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa)


def _meta(ns, name, owner="row"):
    return {
        "namespace": ns,
        "name": name,
        "labels": {"kustomize.toolkit.fluxcd.io/name": owner},
    }


def _cluster(pipeline_up: bool, rule_ns: str, keda_target: str | None = None):
    pipe = [
        {
            "metadata": {"name": n, "namespace": "monitoring"},
            "spec": {"replicas": 1},
            "status": {"readyReplicas": 1 if pipeline_up else 0},
        }
        for _, _, n in sa.PIPELINE
    ]
    data = {
        "pods": [],
        "statefulset": [p for p in pipe if p["metadata"]["name"].endswith("-kps")],
        "deployment": [p for p in pipe if not p["metadata"]["name"].endswith("-kps")],
        "scaledobjects": (
            [
                {
                    "metadata": {"namespace": "app"},
                    "spec": {"scaleTargetRef": {"name": keda_target}},
                }
            ]
            if keda_target
            else []
        ),
        "kustomizations": [
            {
                "metadata": {"name": "row"},
                "spec": {"path": "./platform/app"},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        ],
        "prometheusrules": [
            {
                "metadata": {"namespace": rule_ns},
                "spec": {
                    "groups": [
                        {
                            "rules": [
                                {
                                    "alert": "X",
                                    "expr": 'up{namespace="%s"} == 0' % rule_ns,
                                }
                            ]
                        }
                    ]
                },
            }
        ],
        "deployments": [
            {
                "metadata": _meta("app", "web"),
                "spec": {"replicas": 1},
                "status": {"readyReplicas": 1},
            },
            {
                "metadata": _meta("app", "sleeper"),
                "spec": {"replicas": 0},
                "status": {},
            },
        ],
        "statefulsets": [],
        "daemonsets": [],
        "cronjobs": [{"metadata": _meta("app", "tick"), "spec": {}, "status": {}}],
    }
    return lambda kind, ns=None: [
        i for i in data[kind] if ns is None or i["metadata"]["namespace"] == ns
    ]


def _verdicts(monkeypatch, **kw):
    monkeypatch.setattr(sa, "kget", _cluster(**kw))
    a = sa.audit(None)
    return a, {r["name"]: r["verdict"] for r in a["workloads"]}


def test_dead_pipeline_makes_every_running_workload_silent(monkeypatch):
    a, v = _verdicts(monkeypatch, pipeline_up=False, rule_ns="app")
    assert not a["pipeline"]["alive"] and a["verdict"] == "SILENT"
    assert v["web"] == "SILENT"


def test_live_pipeline_and_a_rule_is_heard(monkeypatch):
    a, v = _verdicts(monkeypatch, pipeline_up=True, rule_ns="app")
    assert v["web"] == "HEARD"


def test_no_rule_is_silent_even_with_a_live_pipeline(monkeypatch):
    a, v = _verdicts(monkeypatch, pipeline_up=True, rule_ns="elsewhere")
    assert v["web"] == "SILENT" and a["verdict"] == "SILENT"


def test_zero_replicas_is_dead_unless_keda_parks_it(monkeypatch):
    _, v = _verdicts(monkeypatch, pipeline_up=True, rule_ns="app")
    assert v["sleeper"] == "DEAD"
    _, v = _verdicts(
        monkeypatch, pipeline_up=True, rule_ns="app", keda_target="sleeper"
    )
    assert v["sleeper"] == "PARKED"


def test_cronjob_that_never_ran_is_dead(monkeypatch):
    _, v = _verdicts(monkeypatch, pipeline_up=True, rule_ns="app")
    assert v["tick"] == "DEAD"
