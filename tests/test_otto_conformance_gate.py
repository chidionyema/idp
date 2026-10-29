"""The Otto conformance gate must be able to fail.

ADR 0047 said Otto's manifests must not name a layer the estate owns. A gate that cannot fail
is not a gate, so this file proves two things: the estate's own tree is green only because
today's known violations are carried as DEBT with the wave that owns each one, and a manifest
that breaks any of the four rules makes the gate refuse.

No cluster, no network, no executor: the gate reads files.
"""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin/otto-conformance-gate"
MANIFESTS = ROOT / "platform/otto-gateway"

MODULE = runpy.run_path(str(GATE), run_name="otto_conformance_gate")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _deployment(name: str, env_lines: str = "", mounts: str = "") -> str:
    return """kind: Deployment
apiVersion: apps/v1
metadata:
  name: {name}
spec:
  template:
    spec:
      containers:
        - name: {name}
          env:
{env_lines}
          volumeMounts:
{mounts}
""".format(name=name, env_lines=env_lines, mounts=mounts)


def test_the_estate_tree_is_green_only_because_the_debt_is_carried():
    report = MODULE["grade"](MANIFESTS)
    assert report["verdict"] == "OK", report["new"]
    assert report["debt"], "today's known violations must be carried, not hidden"
    for row in report["debt"]:
        assert row["owner"], "every carried debt names the wave that owns it"
        assert row["finding"]["rule"] in ("R1", "R2", "R3", "R4")


def test_a_manifest_that_names_a_retired_memory_plane_is_refused(tmp_path):
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "gateway",
            env_lines="            - { name: OTTO_MEMORY_HINDSIGHT_URL, value: 'http://hindsight-api.hindsight.svc:8888' }",
        ),
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "FAIL"
    assert any(finding["rule"] == "R1" for finding in report["new"])


def test_a_comment_about_a_dead_plane_stays_legal(tmp_path):
    """The estate's rule: a comment about a dead port stays legal.

    Only a key, a URL or a name is graded. Free text is not a finding, or every manifest
    that explains what it replaced would be refused.
    """
    _write(
        tmp_path / "deployment.yaml",
        _deployment("gateway")
        + "# until 2026-09-05 the answering lane read memory from hindsight\n",
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "OK", report["new"]


def test_a_loopback_default_route_is_refused(tmp_path):
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "gateway",
            env_lines="            - { name: LITELLM_BASE_URL, value: 'http://127.0.0.1:4010/v1' }",
        ),
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "FAIL"
    assert any(finding["rule"] == "R2" for finding in report["new"])


def test_a_shell_toolset_in_a_secret_holding_container_is_refused(tmp_path):
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "gateway",
            env_lines='            - { name: OTTO_TOOLSETS, value: "terminal,web" }',
            mounts="            - { name: db-password, mountPath: /run/secrets/otto-gateway-db }",
        ),
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "FAIL"
    assert any(finding["rule"] == "R3" for finding in report["new"])


def test_a_shell_toolset_in_a_container_without_secrets_is_allowed(tmp_path):
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "sandbox",
            env_lines='            - { name: OTTO_TOOLSETS, value: "terminal,web" }',
        ),
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "OK", report["new"]


def test_a_credential_literal_in_a_manifest_is_refused(tmp_path):
    _write(
        tmp_path / "external-secret.yaml",
        """kind: ExternalSecret
apiVersion: external-secrets.io/v1
metadata:
  name: otto-gateway
spec:
  data:
    - secretKey: MINIMAX_API_KEY
      remoteRef:
        key: vault
        property: MINIMAX_API_KEY
""",
    )
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "gateway",
            env_lines="            - { name: MINIMAX_API_KEY, value: 'sk-0123456789abcdef0123456789abcdef' }",
        ),
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "FAIL"
    assert any(finding["rule"] == "R4" for finding in report["new"])


def test_a_key_taken_from_the_vault_by_name_is_allowed(tmp_path):
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "gateway",
            env_lines="            - { name: MINIMAX_API_KEY, value: 'os.environ/MINIMAX_API_KEY' }",
        ),
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "OK", report["new"]


def test_an_unreadable_manifest_directory_is_blind_not_a_pass(tmp_path):
    report = MODULE["grade"](tmp_path / "does-not-exist")
    assert report["verdict"] == "BLIND"


def test_the_gate_refuses_with_a_verdict_not_a_traceback(tmp_path):
    """The review found this: the gate CRASHED on a violation instead of refusing.

    `main()` printed the findings as dataclasses while `grade()` returned them as dicts, so
    the one path that matters -- the one where the gate says NO -- died with an
    AttributeError. The exit code was still 1, so the old tests passed for the wrong reason:
    they proved "not zero", not "a verdict". This test proves the verdict is printed.
    """
    _write(
        tmp_path / "deployment.yaml",
        _deployment(
            "gateway",
            env_lines="            - { name: OTTO_FACTS_URL, value: 'http://otto-facts.otto.svc:8080' }",
        ),
    )
    done = subprocess.run(
        [sys.executable, str(GATE), "--dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "Traceback" not in done.stderr, done.stderr
    assert "FAIL" in done.stdout, done.stdout
    assert "new violation" in done.stdout, done.stdout


def test_grading_one_directory_never_calls_another_directorys_debt_resolved(tmp_path):
    """The review found this too: the 'resolved' line named files it had not read.

    Grading platform/otto-golden printed "R2 platform/otto-gateway/deployment.yaml ...
    is resolved -- remove it from BASELINE" for a file the run never opened. A receipt about
    a file that was not measured is a false receipt.
    """
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "OK", report["new"]
    assert report["resolved"] == [], report["resolved"]

    missing = MODULE["grade"](tmp_path / "does-not-exist")
    assert missing["verdict"] == "BLIND", missing


def test_the_secret_holding_container_is_inside_the_scope():
    """hermes-agent is the container that HOLDS the bot token.

    The gate graded platform/otto-gateway alone for its first hour, so the shell toolset in
    the hermes-agent container was never graded at all.
    """
    directories = [ROOT / rel for rel in MODULE["DEFAULT_REL_DIRS"]]
    assert any("hermes-agent" in str(d) for d in directories), directories
    report = MODULE["grade"](directories)
    assert report["verdict"] == "OK", report["new"]
    assert any("hermes-agent" in row["finding"]["file"] for row in report["debt"]), (
        report["debt"]
    )


def test_a_jobs_pod_spec_is_graded(tmp_path):
    """The retired memory store is a Job, and a rule that reads only spec.template misses it."""
    _write(
        tmp_path / "job.yaml",
        """kind: Job
apiVersion: batch/v1
metadata:
  name: otto-memory-store-8
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: store
              env:
                - { name: LITELLM_BASE_URL, value: 'http://127.0.0.1:4010/v1' }
""",
    )
    report = MODULE["grade"](tmp_path)
    assert report["verdict"] == "FAIL", report
    assert any(finding["rule"] == "R2" for finding in report["new"]), report["new"]
