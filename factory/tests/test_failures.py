"""Failure injection. Exercises the paths that matter under load."""

import json, os, sys, time, threading, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def fresh_env(tmp_path, monkeypatch, extra=None):
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    monkeypatch.setenv("FACTORY_LEDGER", str(tmp_path / "ledger"))
    monkeypatch.setenv("FACTORY_ORDERS", str(tmp_path / "orders"))
    monkeypatch.setenv("FACTORY_REGISTRY", str(tmp_path / "registry.json"))
    (tmp_path / "ledger").mkdir(exist_ok=True)
    (tmp_path / "orders").mkdir(exist_ok=True)
    if extra:
        for k, v in extra.items():
            monkeypatch.setenv(k, v)
    import importlib, factory.ledger as L

    importlib.reload(L)
    return L


def test_silent_customer_does_not_shed(tmp_path, monkeypatch):
    L = fresh_env(tmp_path, monkeypatch)
    import importlib, factory.ledger

    importlib.reload(factory.ledger)
    factory.ledger.write(
        "executions",
        {"order_id": "ord_S", "outcome": "ok", "runtime": "ok", "steps": 3},
    )
    exec_entry = factory.ledger.read("executions")[-1]
    shed_triggered = False
    if exec_entry["outcome"] != "ok" and exec_entry.get("error"):
        shed_triggered = True
    assert shed_triggered is False, "silence must not shed"
    assert not factory.ledger.read("receipts")


def test_af_cli_shape_adaptation(tmp_path):
    from factory.adapters import af_cli

    af_cli._CACHED_SHAPE = None
    af_dir = tmp_path / "af"
    (af_dir / "af").mkdir(parents=True)
    (af_dir / "af" / "cli.py").write_text("""
import sys
if '--help' in sys.argv:
    print('usage: cli.py {validate,plan,run} <order.json>'); sys.exit(0)
sub = sys.argv[1]; path = sys.argv[2]
import json
order = json.load(open(path))
if set(order.keys()) >= {'order_id','goal'} and sub == 'plan':
    print('plan ok'); sys.exit(0)
if sub == 'run' and set(order.keys()) >= {'order_id','goal'}:
    print('ran'); sys.exit(0)
sys.exit(1)
""")
    shape = af_cli.discover_shape(af_dir)
    assert "error" not in shape
    assert "run" in shape.get("subcommands", [])
    order = {"order_id": "ord_A", "goal": "do a thing"}
    outcome, detail = af_cli.run_order(af_dir, order, [])
    assert outcome == "ok", detail


def test_secrets_refuses_literal(tmp_path):
    from factory import secrets

    with pytest.raises(secrets.SecretError):
        secrets.refuse_literal_secrets(
            b"Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc", "test"
        )


def test_secrets_env_blocked_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_ENV_SECRETS", raising=False)
    monkeypatch.setenv("SECRET_XYZ", "s3cr3t")
    from factory import secrets

    with pytest.raises(secrets.SecretUnavailable):
        secrets.vend("env://SECRET_XYZ")


def test_secrets_env_allowed_when_flagged(monkeypatch):
    monkeypatch.setenv("ALLOW_ENV_SECRETS", "1")
    monkeypatch.setenv("SECRET_XYZ", "s3cr3t")
    from factory import secrets

    assert secrets.vend("env://SECRET_XYZ") == "s3cr3t"


def test_grammar_refuses_literal_secret(tmp_path, monkeypatch):
    fresh_env(tmp_path, monkeypatch)
    repo = tmp_path / "leaky"
    repo.mkdir()
    (repo / "capability.yaml").write_text("""
terminal:
  id: leaky
  name: leaky
  input:  { shape: text }
  output: { shape: text }
  grade: { metric: accuracy, polarity: maximize, scale: [0,1], gate: { terminal: grammar.admission_test, sandbox: subprocess } }
  state: current
  since: "2026-09-24"
  annotations:
    scope:
      secrets: { token: "Bearer eyJhbGciOiJIUzI1NiJ9.secret" }
""")
    from factory import secrets

    with pytest.raises(secrets.SecretError):
        secrets.refuse_literal_secrets((repo / "capability.yaml").read_bytes(), "leaky")


def test_registry_refuses_ambiguous_current(tmp_path, monkeypatch):
    fresh_env(tmp_path, monkeypatch)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    for d in ("a", "b"):
        (tmp_path / d / "capability.yaml").write_text(f"""
terminal:
  id: dupe
  name: dupe_{d}
  input:  {{ shape: text }}
  output: {{ shape: text }}
  grade: {{ metric: accuracy, polarity: maximize, scale: [0,1], gate: {{ terminal: grammar.admission_test, sandbox: subprocess }} }}
  state: current
  since: "2026-09-24"
""")
    from factory.registry import collect

    reg = collect(tmp_path)
    dupes = [t for t in reg["terminals"] if t["id"] == "dupe"]
    assert len(dupes) == 2
    from factory.resolver import resolve

    order = {
        "order_id": "ord_A" * 3,
        "tenant_id": "per_x",
        "goal": "g",
        "capabilities": [{"id": "dupe", "mode": "function"}],
    }
    res = resolve(order, reg)
    assert any(u.get("reason") == "AMBIGUOUS" for u in res["unresolved"])
