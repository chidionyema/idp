"""The Otto readiness gate must answer the founder's question, and be able to say no.

The founder asked (2026-10-29) for Otto to be "fully ready and onboarded into the estate as
soon as infrastructure is ready". `bin/otto-readiness-gate` answers that with four receipts.
This file pins the two halves that matter: the offline rows are green on the estate's own
tree, and a tree that breaks the estate's one-writer rule makes the gate refuse.

No cluster, no network, no executor: the rows read files, and the runtime row -- which is
delegated to the doctor -- is not exercised here.
"""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin/otto-readiness-gate"
DOCTOR = ROOT / "platform/estate/libexec/telegram-agent-doctor.py"

MODULE = runpy.run_path(str(GATE), run_name="otto_readiness_gate")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _webhook_writer(name: str, path: str) -> str:
    return """kind: CronJob
apiVersion: batch/v1
metadata:
  name: {name}
  annotations:
    idp.estate/path: "{path}"
spec:
  template:
    spec:
      containers:
        - name: {name}
          command: ["python3", "-c", "print('https://api.telegram.org/botX/setWebhook')"]
""".format(name=name, path=path)


def test_the_manifests_row_is_green_on_the_estate_tree():
    status, detail = MODULE["row_manifests"](ROOT)
    assert status == "ok", detail


def test_the_door_registry_row_is_green_on_the_estate_tree():
    status, detail = MODULE["row_door_registry"](ROOT, DOCTOR)
    assert status == "ok", detail


def test_a_second_webhook_writer_makes_the_single_writer_row_refuse(tmp_path):
    _write(
        tmp_path / "platform/otto-gateway/registration-reconciler.yaml",
        _webhook_writer("otto-registration-reconciler", "otto-gateway"),
    )
    _write(
        tmp_path / "platform/otto-golden/deployment.yaml",
        _webhook_writer("otto-golden", "otto-golden"),
    )
    status, detail = MODULE["row_single_writer"](tmp_path)
    assert status == "FAIL", detail
    assert "setWebhook" in detail


def test_the_declared_writer_alone_is_green(tmp_path):
    _write(
        tmp_path / "platform/otto-gateway/registration-reconciler.yaml",
        _webhook_writer("otto-registration-reconciler", "otto-gateway"),
    )
    status, detail = MODULE["row_single_writer"](tmp_path)
    assert status == "ok", detail


def test_a_manifest_that_holds_the_bot_token_outside_the_owner_is_refused(tmp_path):
    _write(
        tmp_path / "platform/otto-gateway/registration-reconciler.yaml",
        _webhook_writer("otto-registration-reconciler", "otto-gateway"),
    )
    _write(
        tmp_path / "platform/hermes-agent/external-secret.yaml",
        """kind: ExternalSecret
apiVersion: external-secrets.io/v1
metadata:
  name: hermes-agent
spec:
  data:
    - secretKey: TELEGRAM_BOT_TOKEN
      remoteRef:
        key: vault
        property: telegram
""",
    )
    status, detail = MODULE["row_single_writer"](tmp_path)
    assert status == "FAIL", detail
    assert "bot token" in detail


def test_the_gate_answers_not_ready_when_a_row_fails(tmp_path):
    _write(
        tmp_path / "platform/otto-gateway/registration-reconciler.yaml",
        _webhook_writer("otto-registration-reconciler", "otto-gateway"),
    )
    _write(
        tmp_path / "platform/otto-golden/deployment.yaml",
        _webhook_writer("otto-golden", "otto-golden"),
    )
    status, detail = MODULE["row_single_writer"](tmp_path)
    assert status == "FAIL"
    assert "otto-golden" in detail or "2 manifests" in detail


def test_the_offline_run_never_claims_every_row_is_proven():
    """The review found this: --offline skipped the runtime row and still said READY.

    The line it printed was "READY  Otto is onboarded: every row is proven" -- while the one
    row that proves Otto is (the runtime row, delegated to the doctor) had not run. The
    offline run must say what it proved and what it did not.
    """
    done = subprocess.run(
        [sys.executable, str(GATE), "--offline"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "every row is proven" not in done.stdout, done.stdout
    assert "SKIPPED" in done.stdout, done.stdout
    assert "NOT PROVEN onboarded" in done.stdout, done.stdout
