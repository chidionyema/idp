"""The six features, bound to the code that has to satisfy them.

These are the estate's own Gherkin files, executed. A feature that cannot
run is prose; this binding makes each sentence a test that fails when the
behaviour is missing.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time

import pytest
import yaml
from pytest_bdd import given as _given
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then as _then
from pytest_bdd import when as _when

from efda.contract import artifact_address, build_artifact, validate_artifact
from efda.executor import decide, execute
from efda.packs import baseline_pack, pack_spec
from efda.reasoning import reason
from efda.reconciler import reconcile
from efda.store import ArtifactStore, RedisClient
from efda.synth import corpus_from_artifacts, synthesize
from efda.validation import validate_pack

from efda_fake_kube import FakeKube, workload
from efda_fake_redis import FakeRedisServer

scenarios("../features/efda")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(REPO, "platform", "efda")


# Every step is a cfparser step: {placeholders} are fields, everything else --
# quotes included -- is literal. The default parser is a regex, where a
# placeholder would have to be spelled (?P<name>...), and a feature file is
# not the place to learn that.
def given(text):
    return _given(parsers.parse(text))


def when(text):
    return _when(parsers.parse(text))


def then(text):
    return _then(parsers.parse(text))


# ---------------------------------------------------------------- fixtures
@pytest.fixture()
def world():
    return {}


@pytest.fixture()
def sink(world):
    server = FakeRedisServer()
    world["sink"] = server
    yield server
    server.stop()


# ---------------------------------------------------------------- helpers
def wrapper_env(world, runner_id, tmp_path=None, **extra):
    server = world.get("sink")
    env = dict(os.environ)
    env.update(
        {
            "EFDA_REDIS_HOST": server.host if server else "127.0.0.1",
            "EFDA_REDIS_PORT": str(server.port) if server else "1",
            "EFDA_RUNNER_ID": runner_id,
            "EFDA_COMPONENT_ID": "efda-test-agent",
            "EFDA_COMPONENT_CLASS": "efda-test-agent",
            "EFDA_COMPONENT_KIND": "agent",
            "EFDA_CLUSTER": "oke",
            "EFDA_NAMESPACE": "default",
            "EFDA_WRITER_IDENTITY": "spiffe://estate/efda-wrapper",
            "EFDA_CHECKPOINT_INTERVAL": "1",
            "PYTHONPATH": REPO,
        }
    )
    if tmp_path is not None:
        env["EFDA_STATE_FILE"] = str(tmp_path / "state.json")
        env["EFDA_WAL_DIR"] = str(tmp_path / "wal")
    env.update(extra)
    return env


def start_wrapper(world, runner_id, tmp_path, **extra):
    """Start the wrapper over a child that exits when we say it does.

    The child records one completed step in the state file, the way a real
    component would: the checkpoint carries progress, not just a heartbeat.
    """
    exit_file = tmp_path / f"exit-{runner_id}"
    stdout_path = tmp_path / f"stdout-{runner_id}.txt"
    stderr_path = tmp_path / f"stderr-{runner_id}.txt"
    stdout_handle = open(stdout_path, "w", encoding="utf-8")
    stderr_handle = open(stderr_path, "w", encoding="utf-8")
    env = wrapper_env(world, runner_id, tmp_path, **extra)
    script = (
        'printf \'{"completed_steps": ["step_a"]}\' > "$EFDA_STATE_FILE"; '
        f'while [ ! -f "{exit_file}" ]; do sleep 0.2; done; exit $(cat "{exit_file}")'
    )
    process = subprocess.Popen(  # noqa: S603 -- the command is the point
        [sys.executable, "-m", "efda", "wrapper", "--", "sh", "-c", script],
        env=env,
        cwd=REPO,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    world["process"] = process
    world["exit_file"] = exit_file
    world["runner_id"] = runner_id
    world["stdout_path"] = stdout_path
    world["stderr_path"] = stderr_path
    return process


def stdout_text(world):
    try:
        with open(world["stdout_path"], "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def wait_for_ready(world):
    """The wrapper announces readiness once its signal handlers are armed."""
    return wait_for(lambda: "efda_wrapper_ready=true" in stdout_text(world))


def artifact_for(sink, runner_id):
    for key in sink.data:
        if not key.startswith("efda:evidence:") or not key.endswith(":artifact"):
            continue
        artifact = json.loads(sink.data[key])
        if (artifact.get("identity") or {}).get("runner_id") == runner_id:
            return artifact
    return None


def wait_for(predicate, timeout=25.0, interval=0.2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


def cel_rule_holds(rule, obj):
    """Evaluate the tiny CEL subset the estate's CRD rules use.

    Supports ``!has(self.x)``, ``self.x != 'y'``, ``has(self.x)`` and ``||``.
    """
    for clause in rule.split("||"):
        clause = clause.strip()
        match = re.match(r"^!has\(self\.([A-Za-z0-9_]+)\)$", clause)
        if match:
            if match.group(1) in obj:
                return False
            continue
        match = re.match(r"^has\(self\.([A-Za-z0-9_]+)\)$", clause)
        if match:
            if match.group(1) not in obj:
                return False
            continue
        match = re.match(r"^self\.([A-Za-z0-9_]+)\s*!=\s*'([^']*)'$", clause)
        if match:
            if obj.get(match.group(1)) == match.group(2):
                return False
            continue
        raise AssertionError(f"the test cannot evaluate this CEL clause: {clause!r}")
    return True


# ------------------------------------------------------------------- L1
@given("the Redis checkpoint sink is running")
def _sink_is_running(world, sink):
    assert sink.data is not None


@given("the efda wrapper is installed")
def _wrapper_is_installed():
    result = subprocess.run(  # noqa: S603 -- fixed argv
        [sys.executable, "-m", "efda", "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPATH=REPO),
    )
    assert result.returncode == 0, result.stderr


@given('a wrapper-managed process is running with runner_id "{runner_id}"')
def _wrapper_running(world, tmp_path, runner_id):
    start_wrapper(world, runner_id, tmp_path)
    assert wait_for_ready(world), "the wrapper never announced readiness"


@when("the process makes progress for 31 seconds")
def _process_progresses(world):
    # The production tick is 30s; the test runs the same code with a 1s
    # interval so the behaviour under test is the tick, not the wall clock.
    key = f"efda:ckpt:{world['runner_id']}"
    assert wait_for(lambda: world["sink"].data.get(key)), "no checkpoint was written"


@then('the checkpoint key "{key}" exists')
def _checkpoint_key_exists(world, key):
    # The signal is asynchronous: the checkpoint lands when the wrapper
    # handles it, not when the signal is sent.
    assert wait_for(lambda: key in world["sink"].data), f"{key} never appeared"


@then("the checkpoint holds at least one completed step")
def _checkpoint_has_steps(world):
    key = f"efda:ckpt:{world['runner_id']}"
    checkpoint = json.loads(world["sink"].data[key])
    assert checkpoint["completed_steps"]


@when("the wrapper receives SIGTERM")
def _sigterm(world):
    world["process"].send_signal(signal.SIGTERM)


@then("the process exits with code 143")
def _exit_143(world):
    world["process"].wait(timeout=20)
    assert world["process"].returncode == 143


@given('the checkpoint for "{runner_id}" holds the steps "step_a" and "step_b"')
def _checkpoint_holds_steps(world, tmp_path, runner_id):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"completed_steps": ["step_a", "step_b"]}))
    key = f"efda:ckpt:{runner_id}"
    assert wait_for(
        lambda: (
            json.loads(world["sink"].data[key])["completed_steps"]
            == ["step_a", "step_b"]
            if key in world["sink"].data
            else False
        )
    ), "the checkpoint never carried the two steps"


@when("the wrapper is SIGKILLed")
def _sigkill(world):
    world["process"].kill()
    world["process"].wait(timeout=10)


@then('a partial artifact exists for "{runner_id}"')
def _partial_artifact(world, runner_id):
    artifact = wait_for(lambda: artifact_for(world["sink"], runner_id))
    assert artifact, "no artifact was written for the killed wrapper"


@then('the artifact\'s failure_class is "{failure_class}"')
def _artifact_failure_class(world, failure_class):
    artifact = artifact_for(world["sink"], world["runner_id"])
    assert artifact["failure_boundary"]["failure_class"] == failure_class


@then('the checkpoint for "{runner_id}" still holds "{step}"')
def _checkpoint_still_holds(world, runner_id, step):
    key = f"efda:ckpt:{runner_id}"
    checkpoint = json.loads(world["sink"].data[key])
    assert step in checkpoint["completed_steps"]


@given("the Redis checkpoint sink is stopped")
def _sink_stopped(world):
    world["sink"].stop()


@when("the process is killed")
def _process_killed(world):
    world["process"].kill()
    world["process"].wait(timeout=10)


@then('a local WAL entry exists for "{runner_id}"')
def _wal_entry(world, tmp_path, runner_id):
    wal = tmp_path / "wal"
    assert wait_for(lambda: wal.exists() and list(wal.glob("*.jsonl"))), (
        "the WAL holds no entry"
    )


@then("when the sink returns the WAL drains the artifact")
def _wal_drains(world, tmp_path):
    server = world["sink"]
    revived = FakeRedisServer(port=server.port)
    try:
        store = ArtifactStore(
            RedisClient(revived.host, revived.port), str(tmp_path / "wal")
        )
        drained = store.wal_drain_all()
        assert drained, "the WAL drained nothing"
        for key in drained:
            assert key in revived.data
    finally:
        revived.stop()


# ------------------------------------------------------------------- L2
@when("the agent exits with code 1")
def _agent_exits(world):
    world["exit_file"].write_text("1")
    world["process"].wait(timeout=20)


@then('an artifact exists for "{runner_id}"')
def _artifact_exists(world, runner_id):
    artifact = wait_for(lambda: artifact_for(world["sink"], runner_id))
    assert artifact, "no artifact was written"


@then("the artifact validates against the agent schema")
def _artifact_validates(world):
    artifact = artifact_for(world["sink"], world["runner_id"])
    assert validate_artifact(artifact) == []
    with open(
        os.path.join(REPO, "efda", "schemas", "diagnostic-artifact-agent.json"),
        encoding="utf-8",
    ) as handle:
        schema = json.load(handle)
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema is not None:
        jsonschema.validate(artifact, schema)
    else:
        for field in schema["required"]:
            assert field in artifact, field


@then("the artifact's integrity.writer_identity names a spiffe identity")
def _writer_identity(world):
    artifact = artifact_for(world["sink"], world["runner_id"])
    assert artifact["integrity"]["writer_identity"].startswith("spiffe://")


@then('the artifact\'s address is "{address}"')
def _artifact_address(world, address):
    artifact = artifact_for(world["sink"], world["runner_id"])
    assert artifact_address(artifact["identity"]) == address


@given("the registry CRDs are installed")
def _crds_installed():
    for name in (
        "componentregistration.yaml",
        "skillpack.yaml",
        "coveragereport.yaml",
        "diagnosticreport.yaml",
        "remediationartifact.yaml",
    ):
        assert os.path.exists(os.path.join(PLATFORM, "crds", name))


@when('a controller declares the status phase "{phase}"')
def _controller_declares(world, phase):
    with open(
        os.path.join(PLATFORM, "crds", "componentregistration.yaml"), encoding="utf-8"
    ) as handle:
        crd = yaml.safe_load(handle)
    rules = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]["properties"][
        "status"
    ]["x-kubernetes-validations"]
    status = {"phase": phase}
    world["crd_rules"] = rules
    world["crd_status"] = status
    world["crd_refused"] = not all(
        cel_rule_holds(rule["rule"], status) for rule in rules
    )


@then("the write is refused")
def _write_refused(world):
    assert world["crd_refused"], (
        "the CRD rule accepted a Failed status with no artifact reference"
    )


@then('the refusal names "{field}"')
def _refusal_names(world, field):
    messages = " ".join(rule.get("message", "") for rule in world["crd_rules"])
    assert field in messages


@given('a runner "{runner_id}" has no artifact')
def _runner_without_artifact(world, runner_id):
    assert artifact_for(world["sink"], runner_id) is None


@when('the supervisor attempts to relaunch "{runner_id}"')
def _relaunch(world, runner_id, tmp_path):
    process = start_wrapper(world, runner_id, tmp_path, EFDA_RESUME="1")
    process.wait(timeout=20)
    world["relaunch_stdout"] = stdout_text(world)
    world["relaunch_code"] = process.returncode


@then("the relaunch is refused")
def _relaunch_refused(world):
    assert world["relaunch_code"] == 75, world["relaunch_stdout"]
    assert "action=refused" in world["relaunch_stdout"]


@then("a SCHEMA_VIOLATION artifact is created")
def _violation_artifact(world):
    artifact = wait_for(lambda: artifact_for(world["sink"], world["runner_id"]))
    assert artifact, "the refusal wrote no artifact"
    assert artifact["failure_boundary"]["failure_class"] == "schema_violation"


@then("the task is routed to human review")
def _routed_to_human(world):
    artifact = artifact_for(world["sink"], world["runner_id"])
    assert artifact["routing"]["routed_to"] == "human_review"


# ------------------------------------------------------------------- L3
@given("the registry reconciler runs against a cluster with one annotated workload")
def _cluster(world):
    world["kube"] = FakeKube(
        workloads=[workload("observed-001", component_class="efda-test-workload")],
        namespaces={"default": {"efda.estate/enforced": "true"}},
    )


@when("the reconciler runs")
def _reconcile(world):
    world["summary"] = reconcile(world["kube"], namespace="efda-system")


@then("a ComponentRegistration exists for the observed workload")
def _registration_exists(world):
    registrations = world["kube"].list("componentregistrations", all_namespaces=True)
    assert len(registrations) == 1
    assert registrations[0]["spec"]["componentClass"] == "efda-test-workload"


@then('its status.coverageState is "{state}"')
def _coverage_state(world, state):
    registrations = world["kube"].list("componentregistrations", all_namespaces=True)
    assert registrations[0]["status"]["coverageState"] == state


@then("its status.packRef is not empty")
def _pack_ref(world):
    registrations = world["kube"].list("componentregistrations", all_namespaces=True)
    assert registrations[0]["status"]["packRef"]


@then("a SkillPack exists for its component class")
def _skillpack_exists(world):
    packs = world["kube"].list("skillpacks", all_namespaces=True)
    assert packs
    assert pack_spec(packs[0])["componentClass"] == "efda-test-workload"


@then("a CoverageReport exists")
def _coverage_report(world):
    report = world["kube"].get("coveragereports", "latest", namespace="efda-system")
    assert report is not None


@then("it counts the observed components")
def _counts(world):
    report = world["kube"].get("coveragereports", "latest", namespace="efda-system")
    assert report["spec"]["counts"]["observed"] == 1


@then("it lists the components that are not compliant")
def _non_compliant(world):
    report = world["kube"].get("coveragereports", "latest", namespace="efda-system")
    assert "nonCompliant" in report["spec"]


@then("the registry snapshot names every registered component class")
def _snapshot(world):
    snapshot = world["kube"].get(
        "configmaps", "efda-registry-snapshot", namespace="efda-system"
    )
    assert "efda-test-workload" in snapshot["data"]["registry.json"]


@given("a ComponentRegistration for a workload that no longer exists")
def _orphan(world):
    reconcile(world["kube"], namespace="efda-system")
    world["kube"].workloads = []


@then('that registration\'s status.coverageState is "{state}"')
def _orphan_state(world, state):
    registrations = world["kube"].list("componentregistrations", all_namespaces=True)
    assert registrations[0]["status"]["coverageState"] == state


@then("it is listed as not compliant")
def _orphan_not_compliant(world):
    report = world["kube"].get("coveragereports", "latest", namespace="efda-system")
    assert report["spec"]["nonCompliant"]


# ------------------------------------------------------------------- L4
@given("a corpus of observed failure artifacts")
def _corpus(world):
    world["artifacts"] = [
        build_artifact(
            component_id="efda-test-agent",
            component_class="efda-test-agent",
            component_kind="agent",
            runner_id=f"efda-test-run-{index:03d}",
            failure_class="exit_nonzero",
            attempted_operation="run_to_completion",
            invariant_broken="exit_zero",
            triggering_step="process_exit",
            capture_method="supervisor_wrapper",
            payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:x"}],
            cluster="oke",
            namespace="default",
        )
        for index in range(4)
    ] + [
        build_artifact(
            component_id="efda-test-agent",
            component_class="efda-test-agent",
            component_kind="agent",
            runner_id=f"efda-test-run-neg-{index:03d}",
            failure_class="oomkill",
            attempted_operation="run_to_completion",
            invariant_broken="exit_zero",
            triggering_step="process_exit",
            capture_method="supervisor_wrapper",
            payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:x"}],
            cluster="oke",
            namespace="default",
        )
        for index in range(3)
    ]
    world["corpus"] = corpus_from_artifacts(world["artifacts"])


@given('no SkillPack exists for the class "{component_class}"')
def _no_pack(world, component_class):
    world["component_class"] = component_class
    assert world.get("packs", []) == []


@when("the baseline generator runs")
def _baseline(world):
    world["pack"] = baseline_pack(world["component_class"])


@then('a SkillPack exists with coverageTier "{tier}"')
def _pack_tier(world, tier):
    assert pack_spec(world["pack"])["coverageTier"] == tier


@then("it carries at least ten technology-agnostic signatures")
def _many_signatures(world):
    assert len(pack_spec(world["pack"])["signatures"]) >= 10


@then("every signature has a confidence base of at most 0.50")
def _low_confidence(world):
    assert all(
        s["confidenceBase"] <= 0.50 for s in pack_spec(world["pack"])["signatures"]
    )


@then("its execution budget is the lowest tier")
def _lowest_budget(world):
    budget = pack_spec(world["pack"])["executionBudget"]
    assert budget["maxCpuMillicores"] == 100
    assert budget["maxMemoryMib"] == 128
    assert budget["maxWallClockMs"] == 2000
    assert budget["maxRegexComplexity"] == "low"


@then("every signature may only report")
def _report_only(world):
    assert all(
        s["remediation"]["tier"] == "T0" for s in pack_spec(world["pack"])["signatures"]
    )


@when('the synthesizer runs for the class "{component_class}"')
def _synthesize(world, component_class):
    world["candidate"] = synthesize(world["corpus"], component_class)


@then("a candidate pack exists")
def _candidate_exists(world):
    assert world["candidate"]["spec"]["signatures"]


@then("it is tagged with the factory that generated it")
def _factory_tag(world):
    assert world["candidate"]["spec"]["generatedBy"] == "factory-synthesis@v1"


@then("it records the digest of the corpus it came from")
def _corpus_digest(world):
    digest = world["candidate"]["spec"]["signatures"][0]["provenance"]["corpusDigest"]
    assert digest.startswith("sha256:")


@given("a candidate whose signature fires on every artifact")
def _always_fires(world):
    world["candidate"] = synthesize(world["corpus"], "efda-test-agent")
    for signature in world["candidate"]["spec"]["signatures"]:
        signature["matchLogic"] = "true"


@given("a candidate whose signature asks a question that mutates state")
def _mutating_question(world):
    world["candidate"] = synthesize(world["corpus"], "efda-test-agent")
    for signature in world["candidate"]["spec"]["signatures"]:
        signature["diagnosticQuestions"] = ["delete the pod"]


@given("a candidate whose match logic exceeds its wall clock budget")
def _ignores_budget(world):
    world["candidate"] = synthesize(world["corpus"], "efda-test-agent")
    for signature in world["candidate"]["spec"]["signatures"]:
        signature["matchLogic"] = 'failure_boundary.failure_class matches "(a+)+$"'


@when("the validator runs")
def _validate(world):
    world["report"] = validate_pack(world["candidate"], world["corpus"])


@then("the candidate is rejected")
def _rejected(world):
    assert not world["report"]["ok"]


@then("the report names the precision floor")
def _names_precision(world):
    failures = " ".join(
        f for result in world["report"]["signatures"] for f in result["failures"]
    )
    assert "precision" in failures


@then("the report names the blast radius")
def _names_blast(world):
    failures = " ".join(
        f for result in world["report"]["signatures"] for f in result["failures"]
    )
    assert "read-only" in failures


@then("the report names the budget breach")
def _names_budget(world):
    failures = " ".join(
        f for result in world["report"]["signatures"] for f in result["failures"]
    )
    assert "budget" in failures.lower()


# ------------------------------------------------------------------- L5
@given('an artifact for the class "{component_class}"')
def _artifact_for_class(world, component_class):
    world["artifact"] = build_artifact(
        component_id=component_class,
        component_class=component_class,
        component_kind="agent",
        runner_id="efda-test-run-020",
        failure_class="exit_nonzero",
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[
            {"kind": "checkpoint", "uri": "efda:ckpt:x"},
            {"kind": "log_tail", "uri": "efda:log:x"},
            {"kind": "pod_state", "uri": "efda:pod:x"},
        ],
        cluster="oke",
        namespace="default",
    )


@given("a specialist SkillPack for that class")
def _pack_for_class(world):
    pack = baseline_pack(world["artifact"]["identity"]["component_class"])
    # A specialist pack has earned its confidence; the baseline pack has not.
    pack["spec"]["coverageTier"] = "specialist"
    for signature in pack["spec"]["signatures"]:
        signature["confidenceBase"] = 0.6
    world["pack"] = pack


@when("the reasoning layer runs")
def _reason(world):
    world["report"] = reason(world["artifact"], world["pack"])


@then('the report\'s status is "{status}"')
def _report_status(world, status):
    assert world["report"]["status"] == status, world["report"]["warnings"]


@then("the report names a cause")
def _report_cause(world):
    assert world["report"]["cause"]


@then("the report's confidence is at least 0.5")
def _report_confidence(world):
    assert world["report"]["confidence"] >= 0.5


@then("the report cites at least one evidence reference")
def _report_evidence(world):
    assert world["report"]["evidenceRefs"]


@then("the report names the pack it came from")
def _report_pack(world):
    assert world["report"]["packRef"].startswith("efda-test-agent-v0@")


@given("an artifact whose evidence is thin")
def _thin_evidence(world):
    world["artifact"] = build_artifact(
        component_id="efda-test-agent",
        component_class="efda-test-agent",
        component_kind="agent",
        runner_id="efda-test-run-021",
        failure_class="exit_nonzero",
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:x"}],
        cluster="oke",
        namespace="default",
    )


@then("the report lists the questions that were asked")
def _report_questions(world):
    assert "questionsAsked" in world["report"]


@given("an artifact whose own assessment claims a cause nothing supports")
def _uncorroborated(world):
    world["artifact"] = build_artifact(
        component_id="efda-test-agent",
        component_class="efda-test-agent",
        component_kind="agent",
        runner_id="efda-test-run-022",
        failure_class="exit_nonzero",
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[
            {"kind": "checkpoint", "uri": "efda:ckpt:x"},
            {"kind": "log_tail", "uri": "efda:log:x"},
            {"kind": "pod_state", "uri": "efda:pod:x"},
        ],
        hypotheses=[
            {
                "rank": 1,
                "cause": "the disk filled up",
                "confidence": 0.9,
                "source": "component",
            }
        ],
        cluster="oke",
        namespace="default",
    )


@then('the report warns "{warning}"')
def _report_warns(world, warning):
    assert any(warning in item for item in world["report"]["warnings"]), world[
        "report"
    ]["warnings"]


@then("the report does not name that cause")
def _report_excludes(world):
    assert world["report"]["cause"] != "the disk filled up"


@given("an artifact whose payload was changed after it was written")
def _tampered(world):
    world["artifact"] = build_artifact(
        component_id="efda-test-agent",
        component_class="efda-test-agent",
        component_kind="agent",
        runner_id="efda-test-run-023",
        failure_class="exit_nonzero",
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:x"}],
        cluster="oke",
        namespace="default",
    )
    world["artifact"]["raw_evidence"]["payloads"][0]["uri"] = "efda:tampered"


@given("a pack whose match logic exceeds its wall clock budget")
def _over_budget(world):
    world["pack"] = baseline_pack("efda-test-agent")
    world["pack"]["spec"]["signatures"] = [
        {
            "id": "runaway",
            "symptom": "never ends",
            "matchLogic": 'failure_boundary.failure_class matches "(a+)+$"',
            "cause": "runaway",
            "confidenceBase": 0.9,
        },
        {
            "id": "honest",
            "symptom": "the honest one",
            "matchLogic": 'failure_boundary.failure_class == "exit_nonzero"',
            "cause": "the process exited non-zero",
            "confidenceBase": 0.35,
        },
    ]


@then("the report records the budget breach")
def _report_breach(world):
    assert world["report"]["budgetBreaches"]


@then("the reasoning layer moves to the next signature")
def _next_signature(world):
    assert world["report"]["signatureId"] == "honest"


# ------------------------------------------------------------------- L6
@given("the executor's allowlist")
def _allowlist(world):
    world["allowlist"] = {"version": "v1", "actions": []}


@given('a report whose signature is tier "{tier}"')
def _report_tier(world, tier):
    world["report"] = {
        "signatureId": "sig-1",
        "componentClass": "efda-test-agent",
        "confidence": 0.9,
        "remediation": {"tier": tier, "safetyProof": "risk=low"},
    }


@given('a report whose signature is tier "T1" and has no safety proof')
def _report_no_proof(world):
    world["report"] = {
        "signatureId": "sig-1",
        "componentClass": "efda-test-agent",
        "confidence": 0.9,
        "remediation": {"tier": "T1", "safetyProof": ""},
    }


@given('a report whose signature is tier "T1" with a safety proof')
def _report_with_proof(world):
    world["report"] = {
        "signatureId": "sig-1",
        "componentClass": "efda-test-agent",
        "confidence": 0.9,
        "remediation": {"tier": "T1", "safetyProof": "risk=low;rollback=defined"},
    }


@given('a report whose signature is tier "T1" with a safety proof and confidence 0.84')
def _report_below_the_gate(world):
    world["report"] = {
        "signatureId": "sig-1",
        "componentClass": "efda-test-agent",
        "confidence": 0.84,
        "remediation": {"tier": "T1", "safetyProof": "risk=low;rollback=defined"},
    }


@given('a report whose signature is tier "T1" with a safety proof and confidence 0.9')
def _report_above_the_gate(world):
    world["report"] = {
        "signatureId": "sig-1",
        "componentClass": "efda-test-agent",
        "confidence": 0.9,
        "remediation": {"tier": "T1", "safetyProof": "risk=low;rollback=defined"},
    }


@given("the allowlist is empty")
def _allowlist_empty(world):
    world["allowlist"] = {"version": "v1", "actions": []}


@given("the allowlist names that signature")
def _allowlist_names(world):
    world["allowlist"] = {
        "version": "v1",
        "actions": [
            {
                "signatureId": "sig-1",
                "componentClass": "efda-test-agent",
                "tier": "T1",
                "action": {
                    "type": "annotate",
                    "target": {
                        "kind": "deployment",
                        "namespace": "default",
                        "name": "probe",
                    },
                    "annotations": {"efda.estate/remediated": "true"},
                },
                "rollback": {
                    "type": "annotate",
                    "target": {
                        "kind": "deployment",
                        "namespace": "default",
                        "name": "probe",
                    },
                    "previousAnnotations": {},
                },
                "rollbackTested": True,
            }
        ],
    }


@given("the allowlist names that signature with a rollback")
def _allowlist_names_with_rollback(world):
    _allowlist_names(world)


@when("the executor runs")
def _execute(world):
    world["decision"] = decide(world["report"], world["allowlist"])
    world["kube"] = FakeKube()
    world["artifact"] = execute(world["decision"], world["kube"])


@then("no action is taken")
def _no_action(world):
    assert world["decision"]["outcome"] != "EXECUTE"


@then('the executor logs "{reason}"')
def _logs(world, reason):
    assert reason in world["decision"]["reason"], world["decision"]["reason"]


@then("the executor logs the confidence gate")
def _logs_confidence(world):
    assert "0.85" in world["decision"]["reason"], world["decision"]["reason"]


@then("the action is applied")
def _applied(world):
    assert world["decision"]["outcome"] == "EXECUTE"
    assert world["artifact"]["spec"]["outcome"] == "REMEDIATION_APPLIED"


@then("a RemediationArtifact records the action, the pre-state and the rollback point")
def _remediation_artifact(world):
    spec = world["artifact"]["spec"]
    assert spec["action"]["type"] == "annotate"
    assert spec["preState"]["appliedAnnotations"] == {"efda.estate/remediated": "true"}
    assert spec["rollbackPoint"]["type"] == "annotate"
