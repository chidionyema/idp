"""telegram-agent-doctor is the one door any agent can call about a Telegram agent.

The founder's standing requirement (2026-10-28): "it needs to be seamless for any agent to
monitor live, diagnose and resolve any issues with any telegram agent/otto." These tests pin the
three things that door has to get right -- it names the FIRST broken link, it never turns an
unreadable source into a failure, and it repairs through the estate's own intent layer.

No cluster, no network, no executor: the walk takes a probe, so a test drives it with a fake.
"""

from __future__ import annotations

import json as jsonlib
import os
import runpy
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "platform/estate/libexec/telegram-agent-doctor.py"
INTENT = ROOT / "platform/estate/intents/telegram-agent.doctor.yaml"

DOCTOR_MODULE = runpy.run_path(str(DOCTOR), run_name="telegram_agent_doctor")


def _agent(link_ids, **overrides):
    agent = {
        "id": "test-agent",
        "title": "a Telegram agent",
        "source": "platform/otto-gateway/OWNER.yaml",
        "links": [
            {
                "id": link_id,
                "kind": "http",
                "url": "https://x/healthz",
                "expect": 200,
                "what": "link {}".format(link_id),
                "fix": {
                    "intent": "flux-reconcile",
                    "args": {
                        "kind": "kustomization",
                        "name": "row",
                        "namespace": "flux-system",
                    },
                },
            }
            for link_id in link_ids
        ],
    }
    agent.update(overrides)
    return agent


def test_the_first_broken_link_is_named_and_the_links_after_it_are_not_probed():
    """Given a chain whose third link is broken, when the doctor walks it, then the third link
    is named as the first broken one and the fourth link is never read -- a chain that broke at
    link three cannot be judged at link four."""
    probed = []

    def probe(link):
        probed.append(link["id"])
        if link["id"] == "third":
            return "FAIL", "it is broken"
        return "ok", "it answered"

    report = DOCTOR_MODULE["walk"](
        _agent(["first", "second", "third", "fourth"]), probe
    )

    assert report["first_broken"]["id"] == "third"
    assert probed == ["first", "second", "third"]


def test_a_source_that_cannot_be_read_is_blind_and_never_a_failure():
    """Given a link whose source cannot be read, when the doctor walks it, then the link is
    BLIND -- not a failure and not a pass. An unreadable source is not zero."""

    def probe(link):
        return "BLIND", "the cluster did not answer in 25s"

    report = DOCTOR_MODULE["walk"](_agent(["first", "second"]), probe)

    assert report["first_broken"] is None
    assert report["first_blind"]["id"] == "first"
    assert report["links"][0]["status"] == "BLIND"


def test_a_blind_link_does_not_hide_a_broken_link_later_in_the_chain():
    """Given the cluster is dark for one link and a later link is broken, when the doctor
    walks the chain, then the broken link is still named -- blind is not a reason to stop."""

    def probe(link):
        if link["id"] == "first":
            return "BLIND", "the cluster did not answer in 25s"
        return "FAIL", "it is broken"

    report = DOCTOR_MODULE["walk"](_agent(["first", "second"]), probe)

    assert report["first_broken"]["id"] == "second"
    assert report["first_blind"]["id"] == "first"


def test_the_heal_runs_the_declared_fix_through_the_intent_layer_and_re_reads_the_link():
    """Given a broken link, when the doctor heals it, then the fix it declares is the intent
    that runs -- with that intent's args -- and the link is read again afterwards."""
    healed = []

    def healer(intent, args):
        healed.append((intent, dict(args)))
        return "INTENT-20261028-000000-abc123", "ok", "exit 0: reconciled"

    def probe(link):
        return "FAIL", "it is broken"

    row = _agent(["first"])["links"][0]
    result = DOCTOR_MODULE["heal"](None, row, healer, probe)

    assert healed == [
        (
            "flux-reconcile",
            {"kind": "kustomization", "name": "row", "namespace": "flux-system"},
        )
    ]
    assert result["receipt"] == "INTENT-20261028-000000-abc123"
    assert result["after"] == "FAIL"


def test_the_registry_names_only_doors_that_exist_and_manifests_that_exist():
    """Given the registry the doctor walks, when it is checked against the repository, then
    every declared fix is a real intent, every declared source manifest is a real file, and the
    intent that fronts the doctor exists and points at this script. A registry that names a fix
    nobody can run is a registry that lies."""
    registry = DOCTOR_MODULE["TELEGRAM_AGENTS"]
    assert registry, "the doctor has no agents to look after"

    for agent in registry:
        assert agent["id"] and agent["title"] and agent["links"]
        assert (ROOT / agent["source"]).exists(), agent["source"]
        for link in agent["links"]:
            fix = link["fix"]
            assert fix["intent"] == "flux-reconcile"
            assert (
                ROOT / "platform/estate/intents" / (fix["intent"] + ".yaml")
            ).exists()

    assert INTENT.exists()
    assert INTENT.read_text(encoding="utf-8").count("telegram-agent-doctor.py") == 1

    for plane in DOCTOR_MODULE["SCHEDULED_PLANES"]:
        assert (ROOT / ".github/workflows" / plane["workflow"]).exists(), plane[
            "workflow"
        ]


def test_the_scheduled_plane_is_read_and_never_graded_again():
    """Given the estate's own fifteen-minute SLA tick, when the doctor reports, then the
    tick's verdict is read and shown as context -- and it does NOT become a broken link of a
    Telegram agent, because that tick grades the layers under the Ottos too. One set of rows,
    two planes: the scheduled one and the callable one."""

    def scheduled(workflow):
        return "FAIL", "the last tick of {} was red".format(workflow)

    report = DOCTOR_MODULE["diagnose"](
        [_agent(["first"])], lambda link: ("ok", "answered"), scheduled=scheduled
    )
    assert report["scheduled"][0]["workflow"] == "otto-parity.yml"
    assert report["scheduled"][0]["status"] == "FAIL"
    assert report["counts"]["broken"] == 0
    assert report["agents"][0]["first_broken"] is None
    assert "the scheduled plane" in DOCTOR_MODULE["render"](report)


def test_the_doctor_covers_every_telegram_agent_the_estate_declares():
    """Given the estate's one Telegram bot owner, when the registry is read, then the door
    covers it, and the agent whose token is removed is declared out rather than silently
    dropped."""
    ids = {agent["id"] for agent in DOCTOR_MODULE["TELEGRAM_AGENTS"]}
    assert "otto-gateway" in ids
    assert "otto-golden" in ids
    assert "jit-broker" in ids

    declared_out = {entry["id"] for entry in DOCTOR_MODULE["DECLARED_OUT"]}
    assert "hermes-agent" in declared_out


def test_the_report_names_the_agent_and_the_counts_and_the_exit_code_separates_blind_from_broken():
    """Given one broken agent and one blind agent, when the report is summarised, then the
    counts say so and the doctor exits 1 for a broken link -- a blind link alone exits 3."""

    def probe(link):
        return "FAIL", "broken"

    broken = DOCTOR_MODULE["diagnose"]([_agent(["first"])], probe)
    assert broken["counts"]["broken"] == 1
    assert broken["counts"]["healthy"] == 0
    assert broken["agents"][0]["first_broken"]["id"] == "first"
    text = DOCTOR_MODULE["render"](broken)
    assert "FIRST BROKEN LINK: first" in text
    assert "FIX: flux-reconcile" in text

    def blind_probe(link):
        return "BLIND", "the cluster did not answer in 25s"

    blind = DOCTOR_MODULE["diagnose"]([_agent(["first"])], blind_probe)
    assert blind["counts"]["broken"] == 0
    assert blind["counts"]["blind"] == 1
    assert "FIRST UNREADABLE LINK" in DOCTOR_MODULE["render"](blind)


def test_a_tick_that_is_running_now_is_not_reported_as_never_run():
    """Given the scheduled tick's last run is still running, when the doctor reads the
    scheduled plane, then it says the tick has not concluded yet -- NOT that the workflow
    has never run. MEASURED 2026-10-29: a running tick has a null conclusion, so the API
    answer was empty and the doctor said 'otto-parity.yml has never run' about a workflow
    that ticks every fifteen minutes. An empty answer is not evidence of absence."""
    status, detail = DOCTOR_MODULE["probe_workflow"](
        "otto-parity.yml",
        run=lambda intent, args, timeout: (
            0,
            "in_progress\t\n",
            "",
            "INTENT-20261029-000000-abc123",
        ),
    )

    assert status == "BLIND"
    assert "has never run" not in detail
    assert "not concluded yet" in detail


def test_a_workflow_with_no_runs_at_all_is_reported_as_never_run():
    """Given the API answers with no run at all, when the doctor reads the scheduled plane,
    then it says the workflow has never run -- the one case where that sentence is true."""
    status, detail = DOCTOR_MODULE["probe_workflow"](
        "otto-parity.yml", run=lambda intent, args, timeout: (0, "", "", "")
    )

    assert status == "BLIND"
    assert "has never run" in detail


def _intent_step(agent="all", heal="no", json_mode="no"):
    """The intent's own step, with the placeholders the executor fills in."""
    intent = yaml.safe_load(INTENT.read_text(encoding="utf-8"))
    cmd = intent["steps"][0]["cmd"]
    return (
        cmd.replace("{{agent}}", agent)
        .replace("{{heal}}", heal)
        .replace("{{json}}", json_mode)
    )


def _run_intent_step(tmp_path, doctor_exit=0, doctor_stdout="", json_mode="no"):
    """Run the intent's step against a stubbed python3, so the door's own exit semantics are
    measured with no cluster, no network and no doctor."""
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub = stub_dir / "python3"
    stub.write_text(
        "#!/bin/sh\ncat <<'STDOUT'\n{}\nSTDOUT\nexit {}\n".format(
            doctor_stdout, doctor_exit
        ),
        encoding="utf-8",
    )
    stub.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = str(stub_dir) + os.pathsep + env["PATH"]
    return subprocess.run(
        ["bash", "-c", _intent_step(json_mode=json_mode)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_the_door_answers_even_when_the_doctor_found_a_broken_link(tmp_path):
    """Given the doctor found a broken link and exited 1, when the intent's step runs, then
    the door exits 0 and says what it found. A doctor's finding is not a failure of the door:
    the estate's policy refuses a verb whose 30-day not-ok rate passes 0.8
    (platform/estate/bin/estate-execute), and a door that exited on its verdict would be
    refused exactly when the estate is broken."""
    done = _run_intent_step(tmp_path, doctor_exit=1)

    assert done.returncode == 0, done.stderr
    assert "verdict: FAIL" in done.stdout
    assert "first broken link" in done.stdout


def test_the_door_answers_even_when_the_estate_is_dark(tmp_path):
    """Given the doctor could not read a source and exited 3, when the intent's step runs,
    then the door exits 0 and says BLIND. Blind is a reading of the estate, not a failure of
    the door -- and it is the state the founder needs the door for most."""
    done = _run_intent_step(tmp_path, doctor_exit=3)

    assert done.returncode == 0, done.stderr
    assert "verdict: BLIND" in done.stdout


def test_the_door_fails_when_the_doctor_itself_could_not_run(tmp_path):
    """Given the doctor could not be run at all (no python, no script, a crash), when the
    intent's step runs, then the door exits non-zero and says so on stderr. A door that
    cannot fail is not a door: this is the one case where the intent must not answer 0."""
    done = _run_intent_step(tmp_path, doctor_exit=127)

    assert done.returncode == 127
    assert "the doctor itself failed" in done.stderr


def test_json_mode_keeps_stdout_a_pure_json_document(tmp_path):
    """Given json=true, when the intent's step runs, then stdout parses as JSON and the
    verdict line goes to stderr -- another agent consumes the document without having to
    strip a line of prose off it."""
    done = _run_intent_step(
        tmp_path,
        doctor_exit=0,
        doctor_stdout=jsonlib.dumps(
            {"counts": {"healthy": 1, "broken": 0, "blind": 0}}
        ),
        json_mode="yes",
    )

    assert done.returncode == 0, done.stderr
    assert jsonlib.loads(done.stdout)["counts"]["healthy"] == 1
    assert "verdict:" not in done.stdout
    assert "verdict: OK" in done.stderr
