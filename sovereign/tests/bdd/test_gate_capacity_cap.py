"""Binds features/gates/capacity-cap.feature (crew#281, crew#289, crew#297). Steps run conftest
for real against policy/node_pool.rego over policy/fixtures/capacity-{under,over}-cap.json."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/capacity-cap.feature")

IDP = Path(__file__).resolve().parents[3]
FIXTURES = IDP / "policy" / "fixtures"
HOURS = 730


def _conftest(path: Path) -> subprocess.CompletedProcess:
    exe = shutil.which("conftest")
    assert exe, "conftest is not installed; the bdd job installs it"
    return subprocess.run([exe, "test", str(path), "-p", str(IDP / "policy"), "-n", "main", "--no-color"],
                          capture_output=True, text=True)


def _estimate(cap: dict) -> float:
    paid_ocpu = max(0, cap["ocpus"] - cap["free"]["ocpus"])
    paid_gb = max(0, cap["memory_gb"] - cap["free"]["memory_gb"])
    return round((paid_ocpu * cap["price_usd_hr"]["ocpu"] + paid_gb * cap["price_usd_hr"]["memory_gb"]) * HOURS, 2)


@pytest.fixture
def state() -> dict:
    return {}


@given("the node pool is 4 OCPU and 24 GB with 2 OCPU and 12 GB free")
def _under(state: dict) -> None:
    cap = json.loads((FIXTURES / "capacity-under-cap.json").read_text())["capacity"]
    assert (cap["ocpus"], cap["memory_gb"], cap["free"]["ocpus"], cap["free"]["memory_gb"]) == (4, 24, 2, 12)
    state["cap"] = cap


@given("Oracle's A1 price list is USD 0.01 per OCPU-hour and USD 0.0015 per GB-hour")
def _prices(state: dict) -> None:
    assert state["cap"]["price_usd_hr"] == {"ocpu": 0.01, "memory_gb": 0.0015}


@given("the node pool is 8 OCPU and 48 GB with the same free allowance and prices")
def _over(state: dict) -> None:
    cap = json.loads((FIXTURES / "capacity-over-cap.json").read_text())["capacity"]
    assert (cap["ocpus"], cap["memory_gb"], cap["free"]["ocpus"], cap["free"]["memory_gb"]) == (8, 48, 2, 12)
    assert cap["price_usd_hr"] == {"ocpu": 0.01, "memory_gb": 0.0015}
    state["cap"] = cap


@given("a capacity input without price_usd_hr or without monthly_cap_usd")
def _blind_inputs(state: dict, tmp_path: Path) -> None:
    base = json.loads((FIXTURES / "capacity-under-cap.json").read_text())
    state["blind"] = []
    for field in ("price_usd_hr", "monthly_cap_usd"):
        d = json.loads(json.dumps(base))
        del d["capacity"][field]
        p = tmp_path / f"no-{field}.json"
        p.write_text(json.dumps(d))
        state["blind"].append((field, p))


@when(parsers.re(r"conftest tests (?P<fixture>policy/fixtures/\S+) against policy/"))
def _run(state: dict, fixture: str) -> None:
    state["run"] = _conftest(IDP / fixture)


@when("conftest tests it against policy/")
def _run_blind(state: dict) -> None:
    state["runs"] = [(field, _conftest(p)) for field, p in state["blind"]]


@then("the estimate is USD 27.74 a month and the gate passes")
def _passes(state: dict) -> None:
    assert _estimate(state["cap"]) == 27.74
    r = state["run"]
    assert r.returncode == 0 and "0 failures" in r.stdout, r.stdout + r.stderr


@then("the gate refuses with an estimate of USD 83.22 a month and the words FOUNDER ACTION")
def _refuses(state: dict) -> None:
    assert _estimate(state["cap"]) == 83.22
    r = state["run"]
    assert r.returncode != 0 and "USD 83.22" in r.stdout and "FOUNDER ACTION" in r.stdout, r.stdout + r.stderr


@then("the gate refuses and names the missing field")
def _blind(state: dict) -> None:
    for field, r in state["runs"]:
        assert r.returncode != 0 and "FAIL" in r.stdout, f"{field}: {r.stdout}{r.stderr}"
        assert field in r.stdout or ("price row" in r.stdout and field == "price_usd_hr"), f"{field}: {r.stdout}"
