#!/usr/bin/env python3
"""Real tests of platform/idp_agent/gateway.py: webhook signature
verification and event-to-task normalization, against the actual FastAPI
app and hmac verification code, not a mocked stand-in for either."""

import hashlib
import hmac
import importlib
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient


class _FakeQueue:
    """Records rpush calls in memory -- no real Redis needed to test the
    gateway's own normalization and signature-verification logic."""

    def __init__(self):
        self.pushed: list[tuple[str, str]] = []

    def rpush(self, key, value):
        self.pushed.append((key, value))

    def llen(self, key):
        return len([k for k, _ in self.pushed if k == key])


@pytest.fixture
def gateway_module(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    idp_agent_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "platform", "idp_agent"
    )
    sys.path.insert(0, os.path.abspath(idp_agent_dir))
    if "gateway" in sys.modules:
        del sys.modules["gateway"]
    import gateway as gw

    importlib.reload(gw)
    gw.queue = _FakeQueue()
    yield gw
    sys.path.remove(os.path.abspath(idp_agent_dir))


@pytest.fixture
def client(gateway_module):
    return TestClient(gateway_module.app)


def _sign(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def test_verify_github_signature_accepts_real_signature(gateway_module):
    body = b'{"a": 1}'
    sig = _sign("test-secret", body)
    assert gateway_module.verify_github_signature(body, sig) is True


def test_verify_github_signature_rejects_wrong_secret(gateway_module):
    body = b'{"a": 1}'
    sig = _sign("wrong-secret", body)
    assert gateway_module.verify_github_signature(body, sig) is False


def test_verify_github_signature_rejects_missing_header(gateway_module):
    assert gateway_module.verify_github_signature(b"{}", None) is False


def test_issue_opened_becomes_worker_feature_task(client, gateway_module):
    payload = {
        "action": "opened",
        "repository": {"clone_url": "https://github.com/acme/repo.git"},
        "issue": {"number": 42, "body": "Fix the thing"},
    }
    body = json.dumps(payload).encode()
    resp = client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": _sign("test-secret", body),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["task_type"] == "worker_feature"

    assert len(gateway_module.queue.pushed) == 1
    key, task_json = gateway_module.queue.pushed[0]
    assert key == "idp_tasks"
    task = json.loads(task_json)
    assert task["type"] == "worker_feature"
    assert task["issue_id"] == 42
    assert task["repo_url"] == "https://github.com/acme/repo.git"


def test_pr_opened_becomes_judge_review_task(client, gateway_module):
    payload = {
        "action": "opened",
        "repository": {"clone_url": "https://github.com/acme/repo.git"},
        "pull_request": {"number": 7, "head": {"ref": "feature-x"}},
    }
    body = json.dumps(payload).encode()
    resp = client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign("test-secret", body),
        },
    )
    assert resp.status_code == 200
    task = json.loads(gateway_module.queue.pushed[0][1])
    assert task["type"] == "judge_review"
    assert task["pr_num"] == 7
    assert task["branch"] == "feature-x"


def test_failed_check_run_becomes_sre_revert_task(client, gateway_module):
    payload = {
        "action": "completed",
        "repository": {"clone_url": "https://github.com/acme/repo.git"},
        "check_run": {
            "conclusion": "failure",
            "head_sha": "abc123",
            "output": {"summary": "tests failed"},
        },
    }
    body = json.dumps(payload).encode()
    resp = client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "check_run",
            "X-Hub-Signature-256": _sign("test-secret", body),
        },
    )
    assert resp.status_code == 200
    task = json.loads(gateway_module.queue.pushed[0][1])
    assert task["type"] == "sre_revert"
    assert task["commit_sha"] == "abc123"


def test_passed_check_run_is_ignored(client, gateway_module):
    payload = {
        "action": "completed",
        "repository": {"clone_url": "https://github.com/acme/repo.git"},
        "check_run": {"conclusion": "success", "head_sha": "abc123"},
    }
    body = json.dumps(payload).encode()
    resp = client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "check_run",
            "X-Hub-Signature-256": _sign("test-secret", body),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert gateway_module.queue.pushed == []


def test_invalid_signature_is_refused(client):
    body = json.dumps({"action": "opened"}).encode()
    resp = client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert resp.status_code == 401


def test_flux_error_severity_becomes_sre_revert_task(client, gateway_module):
    resp = client.post(
        "/webhook/flux",
        json={
            "severity": "error",
            "message": "reconciliation failed",
            "metadata": {"revision": "main@sha1:def456"},
        },
    )
    assert resp.status_code == 200
    task = json.loads(gateway_module.queue.pushed[0][1])
    assert task["type"] == "sre_revert"
    assert task["commit_sha"] == "main@sha1:def456"


def test_flux_non_error_severity_is_ignored(client, gateway_module):
    resp = client.post(
        "/webhook/flux", json={"severity": "info", "message": "reconciled"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"
    assert gateway_module.queue.pushed == []


def test_health_reports_queue_length(client, gateway_module):
    gateway_module.queue.rpush("idp_tasks", "{}")
    gateway_module.queue.rpush("idp_tasks", "{}")
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "queue_length": 2}
