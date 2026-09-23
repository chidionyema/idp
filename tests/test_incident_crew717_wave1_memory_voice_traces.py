"""crew#717 wave 1: Otto's memory, voice and observability are graded rows, not claims.

Founder, 2026-08-30: "i need otto sorted once and for all". The no-new-key powers land first:
Langfuse keys reach the pod from the pair Langfuse was initialised with, the trace URL is the
in-cluster service, and the otto-parity playbook grades memory persistence, the hindsight door,
the mounted keys, the trace door and the voice import from inside the running pod.
"""

from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
HA = ROOT / "platform" / "hermes-agent"


def test_incident_crew717_langfuse_keys_come_from_the_init_pair():
    docs = list(
        yaml.safe_load_all((HA / "langfuse-key.yaml").read_text(encoding="utf-8"))
    )
    es = docs[0]
    keys = {d["secretKey"]: d["remoteRef"]["key"] for d in es["spec"]["data"]}
    assert keys == {
        "LANGFUSE_PUBLIC_KEY": "langfuse-init-public-key",
        "LANGFUSE_SECRET_KEY": "langfuse-init-secret-key",
    }


def test_incident_crew717_gateway_points_traces_at_the_cluster_langfuse():
    text = (HA / "gateway.yaml").read_text(encoding="utf-8")
    assert "value: http://langfuse-web.observability.svc:3000" in text
    assert "hermes-agent-langfuse" in text
    # 4ca529a0.md: no enumerated reload list to fall out of step with a new Secret
    assert 'reloader.stakater.com/auto: "true"' in text
    assert "secret.reloader.stakater.com/reload" not in text
    assert "langfuse-key.yaml" in (HA / "kustomization.yaml").read_text(
        encoding="utf-8"
    )


def test_incident_crew717_wave1_rows_are_steps_in_the_playbook():
    body = (ROOT / "bin" / "idp-oke-break-glass").read_text(encoding="utf-8")
    rows = set(re.findall(r"^\s+step ([a-z0-9-]+) ", body, re.M))
    for row in (
        "memory-survives-restart",
        "memory-volume-bound",
        "memory-hindsight-answers",
        "langfuse-key-mounted",
        "otto-emits-traces",
        "tts-edge-answers",
    ):
        assert row in rows, row
    assert "toolsets-available" in body, "the inventory receipt row is gone"
