"""Falsifier for bin/estate-discovery: it must reject a ledger that lies and accept one that does not."""

import importlib.machinery
import importlib.util
import pathlib

P = pathlib.Path(__file__).resolve().parents[2] / "bin" / "estate-discovery"
loader = importlib.machinery.SourceFileLoader("estate_discovery", str(P))
spec = importlib.util.spec_from_loader("estate_discovery", loader)
ed = importlib.util.module_from_spec(spec)
loader.exec_module(ed)


def test_operational_with_failing_probe_is_contradicted():
    ans, _ = ed.run_probe({"path_exists": "/nonexistent/estate-discovery-falsifier"})
    assert ed.judge("OPERATIONAL", ans) == "CONTRADICTED"


def test_operational_with_no_probe_is_a_claim_without_proof():
    assert ed.judge("OPERATIONAL", None) == "CLAIM-NO-PROBE"


def test_declared_missing_but_answering_is_contradicted():
    ans, _ = ed.run_probe({"path_exists": "/"})
    assert ed.judge("DECLARED-NOT-FOUND", ans) == "CONTRADICTED"


def test_good_cases_pass():
    ans, _ = ed.run_probe({"path_exists": "/"})
    assert ed.judge("OPERATIONAL", ans) == "OK"
    assert ed.judge("RETIRED", None) == "UNPROBED-OK"


def test_unrunnable_probe_is_a_failed_probe_not_a_pass():
    ans, _ = ed.run_probe({"argv": ["/nonexistent/binary"]})
    assert ans is False
