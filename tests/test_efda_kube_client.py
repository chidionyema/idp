"""The controller's kubectl call must keep the in-cluster config.

Measured 2026-10-27 inside the running efda-controller, with the projected
token present and KUBERNETES_SERVICE_HOST=10.96.0.1: ``kubectl get ns`` reached
the API server, while the same call carrying kubectl's request-timeout flag --
before the subcommand or after it -- answered

    Get "http://localhost:8080/api?timeout=30s": dial tcp [::1]:8080: connect: connection refused

One flag lost the in-cluster config and fell back to the laptop's default
server, so the controller read nothing and the pod crash-looped. These tests
are the fence around that: the flag does not come back, and the call is still
bounded -- at the process level, where the bound cannot be lost.
"""

from __future__ import annotations

import ast
import os
import subprocess

import pytest

from efda.k8s import KubeClient, KubeError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO, "efda", "k8s.py")


class _Completed:
    def __init__(self, returncode=0, stdout="{}", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _capture(monkeypatch, completed=None):
    """Stand in for subprocess.run and record what the client asked for."""
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = list(command)
        seen["kwargs"] = kwargs
        return completed if completed is not None else _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def test_the_call_carries_no_request_timeout_flag(monkeypatch):
    seen = _capture(monkeypatch)
    client = KubeClient(namespace="efda-system", timeout=30)
    client.run(["get", "namespaces"])
    argv = seen["command"]
    assert argv[0] == "kubectl"
    offenders = [arg for arg in argv if arg.startswith("--request-timeout")]
    assert not offenders, f"the flag loses the in-cluster config: {argv}"


def test_no_string_literal_in_the_module_can_reintroduce_the_flag():
    """The flag is one edit away from coming back. The code may not hold it.

    Comments are allowed to name the fault -- they are how the next reader
    learns it -- so the check is on the literals the interpreter sees, not on
    the text of the file.
    """
    with open(SOURCE, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    offenders = [value for value in literals if value.startswith("--request-timeout")]
    assert not offenders, f"the flag is back in the code: {offenders}"


def test_the_call_is_still_bounded_by_the_process_timeout(monkeypatch):
    seen = _capture(monkeypatch)
    client = KubeClient(namespace="efda-system", timeout=30)
    client.run(["get", "namespaces"])
    assert seen["kwargs"]["timeout"] == 40


def test_a_failing_kubectl_is_an_error_not_a_silent_empty(monkeypatch):
    seen = _capture(monkeypatch, _Completed(returncode=1, stderr="forbidden"))
    client = KubeClient(namespace="efda-system", timeout=30)
    with pytest.raises(KubeError) as caught:
        client.run(["get", "namespaces"])
    assert "forbidden" in str(caught.value)
    assert seen["command"][0] == "kubectl"
