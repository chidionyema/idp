"""crew#66 root-trust ruling (founder 2026-08-28, 5453747447): every credential is born by a
bootstrapper, or it is ticketed. Incident: platform/identity/external-secret.yaml carried a
stale birth claim ("GitHub OAuth App, founder, console") for a credential Terraform mints, and
16 vault entries were seeded by hand with no ticket. The guard is bin/idp-root-trust; this test
proves it both ways on a synthetic tree (no network, no real vault, no secret values).
"""
import importlib.util
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-root-trust"

ES = textwrap.dedent("""\
    apiVersion: external-secrets.io/v1
    kind: ExternalSecret
    metadata: {name: x, namespace: x}
    spec:
      data:
        - secretKey: a
          remoteRef: {key: alpha}
      dataFrom:
        - extract: {key: beta}
    """)

HEAD = "| Vault entry | Consumer | Provider | Birth path | Verdict | Bootstrapper / ticket |\n|---|---|---|---|---|---|\n"


def _tree(tmp, register):
    (tmp / "bin").mkdir()
    (tmp / "bin" / "idp-bootstrap-alpha").write_text("#!/bin/sh\n")
    (tmp / "platform" / "x").mkdir(parents=True)
    (tmp / "platform" / "x" / "es.yaml").write_text(ES)
    (tmp / "docs" / "policy").mkdir(parents=True)
    (tmp / "docs" / "policy" / "root-trust.md").write_text(HEAD + register)


def _run(tmp, *args):
    env = {**os.environ, "IDP_ROOT": str(tmp)}
    p = subprocess.run([sys.executable, str(GATE), *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def test_gate_passes_when_every_entry_is_born_or_ticketed(tmp_path):
    _tree(tmp_path, "| `alpha` | x | p | api | MEETS | `bin/idp-bootstrap-alpha` |\n| `beta` | x | p | by hand | MISS | crew#575 |\n")
    rc, out = _run(tmp_path)
    assert rc == 0 and out.startswith("PASS"), out
    rc, out = _run(tmp_path, "--check")
    assert rc == 1 and "not MEETS" in out, out


def test_gate_refuses_unregistered_entry(tmp_path):
    _tree(tmp_path, "| `alpha` | x | p | api | MEETS | `bin/idp-bootstrap-alpha` |\n")
    rc, out = _run(tmp_path)
    assert rc == 1 and "beta: read by platform/x/es.yaml but absent from the register" in out, out


def test_gate_refuses_meets_without_bootstrapper_and_miss_without_ticket(tmp_path):
    _tree(tmp_path, "| `alpha` | x | p | console | MEETS | `bin/idp-bootstrap-nope` |\n| `beta` | x | p | by hand | MISS | the founder pastes it |\n")
    rc, out = _run(tmp_path)
    assert rc == 1, out
    assert "bin/idp-bootstrap-nope which does not exist" in out
    assert "MISS without a crew ticket" in out


def test_real_register_passes():
    rc, out = _run(ROOT)
    assert rc == 0 and out.startswith("PASS"), out


def test_gate_opens_no_socket(monkeypatch, tmp_path):
    import socket

    def boom(*a, **k):
        raise AssertionError("root-trust gate opened a socket")

    monkeypatch.setattr(socket, "socket", boom)
    spec = importlib.util.spec_from_loader("rt", importlib.machinery.SourceFileLoader("rt", str(GATE)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _tree(tmp_path, "| `alpha` | x | p | api | MEETS | `bin/idp-bootstrap-alpha` |\n| `beta` | x | p | h | MISS | crew#1 |\n")
    rows = mod.register_rows((tmp_path / "docs/policy/root-trust.md").read_text())
    keys = mod.external_secret_keys(str(tmp_path / "platform"))
    findings, _ = mod.grade(rows, keys, str(tmp_path / "bin"))
    assert findings == []
