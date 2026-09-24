import os
import subprocess
import sys
from pathlib import Path

# __file__ = idp/factory/tests/test_factory.py; two up = idp/factory; three up = idp
PKG = Path(__file__).resolve().parent.parent  # idp/factory (the package)
ROOT = Path(__file__).resolve().parent.parent.parent  # idp (the repo root)
sys.path.insert(0, str(ROOT))


def test_shapes_subsumption_atoms():
    from factory.shapes import subsumes

    assert subsumes("price.result", "price.result")
    assert subsumes("any", "price.result")
    assert subsumes("agent.output", "price.result")  # declared
    assert not subsumes("price.result", "human.expression")


def test_shapes_record_subsumption():
    from factory.shapes import subsumes

    assert subsumes("{sku: text}", "{sku: text, price: text}")
    assert not subsumes("{sku: text, price: text}", "{sku: text}")


def test_metrics_registered():
    from factory.metrics import family, comparable

    assert family("accuracy")["polarity"] == "maximize"
    assert comparable("accuracy", "coverage")
    try:
        family("bogus")
        raise AssertionError("family('bogus') should have raised ValueError")
    except ValueError:
        pass


def test_grammar_bootstrap():
    from factory.grammar import bootstrap

    assert bootstrap()["terminals"][0]["id"] == "grammar"


def test_grammar_refuses_raw_gate():
    from factory.grammar import validate_terminal

    t = {
        "id": "x",
        "name": "x",
        "input": {"shape": "text"},
        "output": {"shape": "text"},
        "grade": {
            "metric": "accuracy",
            "polarity": "maximize",
            "scale": [0, 1],
            "gate": "rm -rf ~",
        },
        "state": "current",
        "since": "2026-09-24",
    }
    errs = validate_terminal(t, set())
    assert any("gate must be an object" in e for e in errs)


def test_grammar_refuses_unregistered_metric():
    from factory.grammar import validate_terminal

    t = {
        "id": "x",
        "name": "x",
        "input": {"shape": "text"},
        "output": {"shape": "text"},
        "grade": {
            "metric": "bogus_metric",
            "polarity": "maximize",
            "scale": [0, 1],
            "gate": {"terminal": "grammar.admission_test", "sandbox": "subprocess"},
        },
        "state": "current",
        "since": "2026-09-24",
    }
    errs = validate_terminal(t, {"grammar.admission_test"})
    assert any("metric not registered" in e for e in errs)


def test_registry_from_repos(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "capability.yaml").write_text("""
terminal:
  id: t1
  name: t1
  input:  { shape: text }
  output: { shape: json }
  grade:
    metric: accuracy
    polarity: maximize
    scale: [0,1]
    gate: { terminal: grammar.admission_test, sandbox: subprocess }
  state: current
  since: "2026-09-24"
""")
    from factory.registry import collect

    reg = collect(tmp_path)
    ids = {t["id"] for t in reg["terminals"]}
    assert "grammar" in ids
    assert "t1" in ids


def test_resolver_refuses_stale():
    from factory.resolver import resolve, Refuse

    reg = {
        "generated_at": "2020-01-01T00:00:00+00:00",
        "ttl_seconds": 60,
        "terminals": [],
    }
    order = {
        "order_id": "ord_" + "A" * 26,
        "tenant_id": "ten_x",
        "goal": "x",
        "capabilities": [{"id": "any", "mode": "function"}],
    }
    try:
        resolve(order, reg)
        raise AssertionError("resolve should have refused the stale order")
    except Refuse as e:
        assert "stale" in str(e)


def test_resolver_refuses_unknown():
    from factory.resolver import resolve
    from datetime import datetime, timezone

    reg = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": 3600,
        "terminals": [
            {
                "id": "grammar",
                "state": "current",
                "input": {"shape": "declaration"},
                "output": {"shape": "registry.entry"},
                "grade": {},
                "annotations": {},
            }
        ],
    }
    order = {
        "order_id": "ord_" + "A" * 26,
        "tenant_id": "ten_x",
        "goal": "x",
        "capabilities": [{"id": "does_not_exist", "mode": "function"}],
    }
    r = resolve(order, reg)
    assert r["unresolved"][0]["reason"] == "NOT_FOUND_OR_NOT_CURRENT"


def test_web_scrape_no_url():
    from factory.nodes import web_scrape

    out = web_scrape({"goal": "do something vague"})
    assert out.get("error") == "NO_URL_IN_EXPRESSION"
    assert out.get("html") == ""


def test_price_extract_empty():
    from factory.nodes import price_extract

    out = price_extract({"html": ""})
    assert out["prices"] == []


def test_alert_insufficient():
    from factory.nodes import alert_emit

    out = alert_emit({"prices": [{"value": 10.0, "currency": "$"}]})
    assert out["alert"] is None
    assert "INSUFFICIENT" in out["reason"]


def test_alert_real_delta():
    from factory.nodes import alert_emit

    out = alert_emit(
        {"prices": [{"value": 10.0, "currency": "$"}, {"value": 12.0, "currency": "$"}]}
    )
    assert out["alert"] is not None
    assert abs(out["delta_pct"] - 20.0) < 0.01


def test_af_run_no_runtime(tmp_path):
    from factory.exec import af_run

    outcome, detail = af_run({"order_id": "ord_X", "goal": "x"}, tmp_path)
    assert outcome == "no_runtime"


def test_end_to_end_cli(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "capability.yaml").write_text("""
terminals:
  - terminal:
      id: web-scrape
      name: "Web scrape"
      input:  { shape: "{goal: text}" }
      output: { shape: "{html: text, url: text}" }
      grade: { metric: accuracy, polarity: maximize, scale: [0,1], gate: { terminal: grammar.admission_test, sandbox: subprocess } }
      state: current
      since: "2026-09-24"
  - terminal:
      id: price-extract
      name: "Price extract"
      input:  { shape: "{html: text}" }
      output: { shape: price.result }
      grade: { metric: accuracy, polarity: maximize, scale: [0,1], gate: { terminal: grammar.admission_test, sandbox: subprocess } }
      state: current
      since: "2026-09-24"
""")
    monkeypatch.setenv("FACTORY_ROOT", str(tmp_path))
    monkeypatch.setenv("FACTORY_LEDGER", str(tmp_path / "ledger"))
    monkeypatch.setenv("FACTORY_EXPRESSION", "fetch https://example.com")
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    r = subprocess.run(
        [sys.executable, "-m", "factory.main", "run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    ledger = tmp_path / "ledger"
    assert (ledger / "orders.ndjson").exists()
    assert (ledger / "executions.ndjson").exists()
