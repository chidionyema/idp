"""The founder's governance, proven by tests that fail before the fix.

Every test here is a falsifier in the founder's sense (AGENTS.md section 9, R2): it names the
behaviour the law demands and refuses the estate if it is gone. The governance state is written
to a temporary home (ESTATE_GOVERNANCE_HOME), so a test never touches the estate's real state.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "platform" / "estate"))

from governance import (  # noqa: E402
    checks,
    executor_permission,
    founder_intake,
    freeze,
    ledger,
    provider_renewal,
    receipt,
    registry,
    relaunch,
    state_page,
    supervisor,
)


@pytest.fixture(autouse=True)
def governance_home(tmp_path, monkeypatch):
    """Every test writes its governance state into a throwaway home."""
    home = tmp_path / "state"
    monkeypatch.setenv("ESTATE_GOVERNANCE_HOME", str(home))
    return home


# ---------------------------------------------------------------- the law gate


def test_every_registered_law_has_a_check_and_a_falsifier():
    for law in registry.laws():
        assert law.get("check"), f"{law.get('id')} has no check"
        assert law.get("falsifier"), f"{law.get('id')} has no falsifier"


def test_every_falsifier_rejects_its_known_bad_fixture():
    """A gate that cannot fail is not a gate: every falsifier must FAIL."""
    for law in registry.laws():
        ok, detail = registry.run_falsifier(law, str(REPO))
        assert ok, f"{law.get('id')} cannot fail: {detail}"


def test_the_law_gate_is_green_on_this_tree():
    report = registry.evaluate_all(str(REPO))
    failing = [r["id"] for r in report["failing"]]
    assert not failing, f"the estate breaks its own laws: {failing}"


def test_a_law_id_never_impersonates_a_founder_law():
    """Governance ids are GOV-<n>; the founder's own series is LAW <n>."""
    for law in registry.laws():
        assert str(law["id"]).startswith("GOV-"), law["id"]
        claimed = law.get("founder_law")
        if claimed:
            assert str(claimed).startswith("LAW-"), claimed


def test_a_cosmetic_change_is_refused():
    """'any tiny flow where cosmetic or technical we not letting in'."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        run = lambda *a: subprocess.run(  # noqa: E731
            ["git", *a], cwd=tmp, capture_output=True, text=True, check=False
        )
        run("init", "-q", "-b", "main")
        pathlib.Path(tmp, "app.py").write_text("x = 1\n")
        run("add", "-A")
        run("commit", "-qm", "base")
        pathlib.Path(tmp, "app.py").write_text(
            "x = 1\n\n# a comment that changes nothing\n"
        )
        run("add", "-A")
        run("commit", "-qm", "head")
        ok, detail = checks.run_check(
            tmp, {"type": "diff_cosmetic", "base": "HEAD~1", "head": "HEAD"}
        )
        assert not ok, "a comment-only change passed the cosmetic gate"
        assert "behaviour" in detail


def test_a_behaviour_change_passes_the_cosmetic_gate():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        run = lambda *a: subprocess.run(  # noqa: E731
            ["git", *a], cwd=tmp, capture_output=True, text=True, check=False
        )
        run("init", "-q", "-b", "main")
        pathlib.Path(tmp, "app.py").write_text("x = 1\n")
        run("add", "-A")
        run("commit", "-qm", "base")
        pathlib.Path(tmp, "app.py").write_text("x = 2\n")
        run("add", "-A")
        run("commit", "-qm", "head")
        ok, detail = checks.run_check(
            tmp, {"type": "diff_cosmetic", "base": "HEAD~1", "head": "HEAD"}
        )
        assert ok, detail


def test_the_advisory_audit_distinguishes_a_notification_from_a_fail_open_gate():
    rows = checks.advisory_gates_in(str(REPO), ".github/workflows/ci.yml")
    assert rows, "the advisory audit found nothing to classify"
    for row in rows:
        assert row["class"] in {"fail-open", "compensated", "not-a-gate"}, row


def test_a_gate_that_fails_open_is_named_as_such():
    import tempfile

    body = {
        "name": "ci",
        "on": ["pull_request"],
        "jobs": {
            "gate": {"runs-on": "ubuntu-24.04", "steps": [{"run": "echo hi"}]},
            "downstream": {"runs-on": "ubuntu-24.04", "needs": ["gate"], "steps": []},
        },
    }
    body["jobs"]["gate"]["continue-on-error"] = True
    with tempfile.TemporaryDirectory() as tmp:
        wf = pathlib.Path(tmp, ".github/workflows")
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text(yaml.safe_dump(body))
        rows = checks.advisory_gates_in(tmp, ".github/workflows/ci.yml")
    assert any(r["class"] == "fail-open" for r in rows), rows


# ---------------------------------------------------------------- the supervisor


def test_the_first_violation_warns_and_the_second_terminates():
    first = supervisor.grade("write-without-claim", "session-a", detail="no claim")
    assert first["decision"] == "warn"
    assert "warning 1 of 1" in first["message"]
    second = supervisor.grade(
        "write-without-claim", "session-a", detail="no claim again"
    )
    assert second["decision"] == "terminate"
    assert second["locked"] is True
    assert ledger.is_locked("session-a")


def test_a_locked_session_has_no_write_path():
    """Lockdown must close the write door, not merely warn about it."""
    out = supervisor.grade(
        "frozen-path-write", "session-b", detail="wrote a frozen path"
    )
    assert out["decision"] == "warn"
    out = supervisor.grade("frozen-path-write", "session-b", detail="wrote it again")
    assert out["decision"] == "terminate"
    assert ledger.is_locked("session-b")
    state = ledger.get_session_state("session-b")
    assert state["status"] == "locked"
    assert state["proof"]
    assert state["instruction"]


def test_the_relaunch_instruction_names_the_hole_and_its_proof():
    instruction = supervisor.plug_the_hole_instruction(
        "write-without-claim", "wrote a file with no live claim", "session-c"
    )
    assert "write-without-claim" in instruction
    assert "bin/claim-gate" in instruction
    assert "receipt" in instruction


def test_the_relauch_argv_carries_the_instruction_and_no_shell():
    argv = relaunch.build_argv("PLUG THE HOLE", model="minimax", session="s1")
    assert argv[0]
    assert "PLUG THE HOLE" in " ".join(argv)
    assert "--session-id" in argv


# ---------------------------------------------------------------- the founder's prompts


def test_a_repeated_founder_prompt_is_detected():
    prompt = "the router returns a 500 when the minimax fallback chain is missing"
    founder_intake.intake(prompt, publish_to_memory=False)
    repeat = founder_intake.find_repeat(prompt)
    assert repeat is not None
    assert repeat["score"] >= 0.6


def test_a_different_founder_prompt_is_not_a_repeat():
    founder_intake.intake(
        "rotate the vault key for the laptop", publish_to_memory=False
    )
    repeat = founder_intake.find_repeat(
        "the fleet dashboard is missing the voice button"
    )
    assert repeat is None


def test_a_founder_prompt_is_classified_into_retrievable_context():
    analysis = founder_intake.analyse(
        "the router returns 500 in bin/idp-vendor-render for #7474 please fix it"
    )
    assert analysis["sentences"]
    assert analysis["entities"]["files"] == ["bin/idp-vendor-render"]
    assert analysis["entities"]["issues"] == ["#7474"]
    assert analysis["fingerprint"]


# ---------------------------------------------------------------- receipts


def test_a_receipt_carries_the_command_the_status_and_a_hash():
    got = receipt.run_receipt(["echo", "hello"], cwd=str(REPO))
    assert got["command"] == ["echo", "hello"]
    assert got["exit"] == 0
    assert got["line"] == "hello"
    assert len(got["sha256"]) == 64
    assert receipt.verify(got)["ok"]


def test_a_receipt_records_a_failure_honestly():
    got = receipt.run_receipt(["sh", "-c", "echo boom >&2; exit 3"], cwd=str(REPO))
    assert got["exit"] == 3
    assert got["sha256"]


# ---------------------------------------------------------------- the freeze


def test_a_frozen_path_is_refused_until_it_is_released():
    freeze.freeze(["platform/estate/governance/**"], approval="founder-2026-10-29")
    frozen, entry = freeze.is_frozen("platform/estate/governance/laws.yaml")
    assert frozen
    assert entry["approval"] == "founder-2026-10-29"
    assert freeze.release(
        "platform/estate/governance/**", approval="founder-2026-10-30"
    )
    frozen, _ = freeze.is_frozen("platform/estate/governance/laws.yaml")
    assert not frozen


def test_the_write_gate_refuses_a_frozen_path():
    enforce = (REPO / "bin/estate-memory-enforce").read_text()
    assert "freeze.is_frozen" in enforce
    assert "is_locked" in enforce


def test_the_merge_gate_refuses_a_frozen_path():
    assert "frozen_problems" in (REPO / "bin/claim-gate").read_text()


# ---------------------------------------------------------------- the providers


def test_a_denied_provider_loses_its_lanes_in_the_rendered_config(tmp_path):
    """A denial that only lives in a report is not a denial."""
    tree = tmp_path / "tree"
    (tree / "bin").mkdir(parents=True)
    (tree / "platform/vendors").mkdir(parents=True)
    (tree / "llm").mkdir(parents=True)
    (tree / "platform/llm").mkdir(parents=True)
    shutil.copy(REPO / "bin/idp-vendor-render", tree / "bin/idp-vendor-render")
    shutil.copy(
        REPO / "platform/vendors/consoles.yaml", tree / "platform/vendors/consoles.yaml"
    )
    for base in ("llm/config.base.yaml", "platform/llm/config.base.yaml"):
        shutil.copy(REPO / base, tree / base)
    (tree / "platform/vendors/renewals.yaml").write_text(
        yaml.safe_dump({"renewals": {"groq": {"status": "denied", "violations": 3}}})
    )
    proc = subprocess.run(
        [sys.executable, str(tree / "bin/idp-vendor-render")],
        capture_output=True,
        text=True,
        cwd=str(tree),
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rendered = (tree / "llm/config.yaml").read_text()
    assert "model_name: groq" not in rendered, "a denied provider still has lanes"
    chains = [
        line
        for line in rendered.splitlines()
        if line.strip().startswith("- ") and "[" in line
    ]
    assert not [c for c in chains if "groq" in c], (
        "a denied provider is still a fallback target"
    )


def test_every_served_minimax_group_has_its_own_fallback_chain():
    """LiteLLM matches fallbacks by group name: no chain for the group, no fallback."""
    config = yaml.safe_load((REPO / "llm/config.yaml").read_text())
    raw = config["router_settings"]["fallbacks"]
    fallbacks = {}
    for row in raw:
        if isinstance(row, dict):
            fallbacks.update(row)
    served = {
        str(model["model_name"])
        for model in config["model_list"]
        if isinstance(model, dict) and model.get("model_name")
    }
    for group in ("minimax_m27", "minimax_json", "minimax_m31f"):
        assert group in served, (
            f"{group} is not served, so the estate cannot route to it"
        )
        assert group in fallbacks, f"{group} has no fallback chain"
        assert fallbacks[group], f"{group} has an empty fallback chain"
        for hop in fallbacks[group]:
            assert hop in served, f"{group} falls back to {hop}, which serves nothing"


def test_the_renewal_record_is_committed_and_machine_readable():
    data = yaml.safe_load((REPO / "platform/vendors/renewals.yaml").read_text())
    assert "renewals" in data
    assert isinstance(data["renewals"], dict)


def test_two_violations_from_one_provider_deny_the_renewal():
    ledger.record_violation("law:LAW-001", "s1", provider="acme")
    assert provider_renewal.evaluate()["denied"] == []
    ledger.record_violation("law:LAW-001", "s2", provider="acme")
    report = provider_renewal.evaluate()
    assert "acme" in report["denied"]


# ---------------------------------------------------------------- the state page


def test_the_state_page_is_measured_not_asserted():
    facts = state_page.compute(str(REPO))
    page = state_page.render(facts)
    assert "## Laws" in page
    assert "## Claims" in page
    assert "## Lockdown" in page


def test_the_state_page_reaches_every_session_through_the_brief():
    brief = (REPO / "bin/estate-brief").read_text()
    assert "estate-state" in brief
    assert "state_section" in brief


def test_the_law_gate_is_a_required_ci_job():
    ci = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    jobs = ci["jobs"]
    assert "law-gate" in jobs
    assert "estate-law-gate" in yaml.safe_dump(jobs["law-gate"])
    assert "law-gate" in jobs["ci-success"]["needs"]
    assert not jobs["law-gate"].get("continue-on-error")
    for step in jobs["law-gate"]["steps"]:
        assert not step.get("continue-on-error")


def test_ci_success_judges_every_job():
    ci = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    jobs = ci["jobs"]
    needs = set(jobs["ci-success"]["needs"])
    after_landing = {"estate-graph-sync"}
    missing = set(jobs) - needs - after_landing - {"ci-success"}
    assert not missing, f"ci-success does not judge {sorted(missing)}"


# ---------------------------------------------------------------- the specs


def test_a_spec_is_done_only_when_its_proof_exits_zero(monkeypatch):
    """'a spec is done when the acceptance criteria pass', and the criteria are commands."""
    spec = {
        "id": "SPEC-test",
        "title": "a spec whose proof fails",
        "component": "test",
        "status": "open",
        "acceptance": ["the proof exits 0"],
        "proof": {"argv": ["false"]},
    }
    monkeypatch.setattr(registry, "specs", lambda: [spec])
    report = registry.evaluate_specs(str(REPO))
    assert report["open"], "a spec with a failing proof was called done"
    assert report["open"][0]["id"] == "SPEC-test"

    spec2 = dict(spec, id="SPEC-test-2", proof={"argv": ["true"]})
    monkeypatch.setattr(registry, "specs", lambda: [spec2])
    report = registry.evaluate_specs(str(REPO))
    assert not report["open"], "a spec with a passing proof was called open"


def test_the_law_gate_runs_as_a_command_and_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(REPO / "bin/estate-law-gate")],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-2000:]
    assert "law-gate" in proc.stdout


def test_the_state_page_file_is_json_free_markdown():
    facts = state_page.compute(str(REPO))
    page = state_page.render(facts)
    assert page.startswith("# Estate state")
    with pytest.raises(json.JSONDecodeError):
        json.loads(page)


# ------------------------------------------------- the direct executor's permission


def test_the_direct_executor_is_granted_only_on_a_green_gate():
    ok, detail = checks.check_executor_permission(str(REPO), {})
    assert ok, detail


def test_a_red_law_gate_refuses_the_direct_executor():
    report = {
        "results": [{"id": "GOV-001", "verdict": "fail", "detail": "the law is red"}]
    }
    decision = executor_permission.evaluate(
        "check-session",
        root=str(REPO),
        claim="1",
        gate_report=report,
        state={"locked": False},
        live_claims=["1"],
    )
    assert decision["granted"] is False
    assert any("red" in reason for reason in decision["reasons"])


def test_a_gate_that_reports_no_law_refuses_the_direct_executor():
    decision = executor_permission.evaluate(
        "check-session",
        root=str(REPO),
        claim="1",
        gate_report={"results": []},
        state={"locked": False},
        live_claims=["1"],
    )
    assert decision["granted"] is False
    assert any("no laws" in reason for reason in decision["reasons"])


def test_a_locked_session_is_refused_the_direct_executor():
    decision = executor_permission.evaluate(
        "check-session",
        root=str(REPO),
        claim="1",
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": True},
        live_claims=["1"],
    )
    assert decision["granted"] is False


def test_a_session_with_no_live_claim_is_refused_the_direct_executor():
    decision = executor_permission.evaluate(
        "check-session",
        root=str(REPO),
        claim="1",
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": False},
        live_claims=[],
    )
    assert decision["granted"] is False


def test_a_claim_the_register_cannot_see_is_refused_the_direct_executor():
    decision = executor_permission.evaluate(
        "check-session",
        root=str(REPO),
        claim="999",
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": False},
        live_claims=["7474"],
    )
    assert decision["granted"] is False
    assert decision["claim_verified"] is False


def test_a_session_that_names_no_claim_is_refused_the_direct_executor():
    decision = executor_permission.evaluate(
        "check-session",
        root=str(REPO),
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": False},
        live_claims=["7474"],
    )
    assert decision["granted"] is False
    assert any("no claim was named" in reason for reason in decision["reasons"])


def test_the_permission_launcher_refuses_a_session_with_no_live_claim(tmp_path):
    env = dict(os.environ, ESTATE_GOVERNANCE_HOME=str(tmp_path / "state"))
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "bin/estate-executor-permission"),
            "--session",
            "probe-locked",
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=env,
        check=False,
    )
    assert proc.returncode == 1, proc.stdout
    decision = json.loads(proc.stdout[proc.stdout.index("{") :])
    assert decision["granted"] is False
    assert decision["artifact"].endswith("probe-locked.json")


# --------------------------------------------------------- the installed launchers


def test_every_governance_launcher_is_installed_by_the_runtime_sync():
    source = (REPO / "bin/estate-runtime-sync").read_text()
    for name in (
        "estate-law-gate",
        "estate-spec-status",
        "estate-supervisor",
        "estate-freeze",
        "estate-founder-intake",
        "estate-state-page",
        "estate-provider-renewal",
        "estate-receipt",
        "estate-executor-permission",
    ):
        assert f'"{name}"' in source, f"{name} is not installed for the runtimes"


def test_the_receipt_launcher_reads_a_report_from_stdin():
    proc = subprocess.run(
        [sys.executable, str(REPO / "bin/estate-receipt"), "--has-receipt", "--stdin"],
        input="I fixed it and everything is fine.\n",
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    assert proc.returncode == 1, "a narration is not a receipt"

    proc = subprocess.run(
        [sys.executable, str(REPO / "bin/estate-receipt"), "--has-receipt", "--stdin"],
        input="ok  receipt  cmd  exit 0  sha256=abc123\n",
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    assert proc.returncode == 0, proc.stdout
