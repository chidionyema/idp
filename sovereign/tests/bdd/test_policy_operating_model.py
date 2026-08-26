"""Binds features/policy/operating-model-offline.feature (crew#286, crew#297). Steps run
bin/policy-test (conftest over the real fixtures) and bin/pr-report; nothing is mocked."""
import os
import re
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/policy/operating-model-offline.feature")

IDP = Path(__file__).resolve().parents[3]


@pytest.fixture
def state() -> dict:
    return {}


@given("policy/fixtures/opmodel-ok.json")
def _fixture_present() -> None:
    assert (IDP / "policy" / "fixtures" / "opmodel-ok.json").is_file()


@when("bin/policy-test runs")
def _policy_test(state: dict) -> None:
    state["run"] = subprocess.run(["bash", str(IDP / "bin" / "policy-test")], capture_output=True, text=True)
    rows = {}
    for line in state["run"].stdout.splitlines():
        m = re.match(r"(opmodel-[\w-]+\.json)\s+(\d)\s+(\d)\s", line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    state["rows"] = rows


@then("the opmodel-ok row is 0 and every other opmodel-* row is 1")
def _rows(state: dict) -> None:
    rows = state["rows"]
    assert rows.get("opmodel-ok.json", (None, None))[1] == 0, state["run"].stdout
    refusals = {k: v for k, v in rows.items() if k not in ("opmodel-ok.json", "opmodel-drill-added-in-pr.json")}
    assert len(refusals) >= 5 and all(v[1] == 1 for v in refusals.values()), rows


@then("no row's exit code differs from the one it expects")
def _no_surprise(state: dict) -> None:
    assert state["run"].returncode == 0 and all(w == g for w, g in state["rows"].values()), state["run"].stdout


@given("the reusable workflow .github/workflows/operating-model-gate.yml")
def _wf(state: dict) -> None:
    state["wf"] = (IDP / ".github" / "workflows" / "operating-model-gate.yml").read_text()


@when("the job is evaluated for a push event")
def _push() -> None:
    pass


@then("the job carries if: github.event_name == 'pull_request' so main stays green")
def _guard(state: dict) -> None:
    assert re.search(r"^\s+if: github\.event_name == 'pull_request'\s*$", state["wf"], re.M), state["wf"]


@given("IDP_ROOT names a directory with no policy/ dir")
def _no_policy(state: dict, tmp_path: Path) -> None:
    state["env"] = {**os.environ, "IDP_ROOT": str(tmp_path)}


@when("bin/pr-report runs")
def _pr_report(state: dict) -> None:
    state["run"] = subprocess.run(["bash", str(IDP / "bin" / "pr-report"), "1"], env=state["env"], capture_output=True, text=True)


@then("it exits 2 with a line starting BLIND")
def _blind(state: dict) -> None:
    r = state["run"]
    assert r.returncode == 2 and r.stdout.startswith("BLIND"), r.stdout + r.stderr
