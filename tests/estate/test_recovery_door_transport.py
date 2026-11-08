"""The recovery door must survive OCI's 4096-character Run Command limit (#7525).

MEASURED 2026-10-30. OCI refused the recovery door's own request shape:

    InvalidParameter: content.source.text size must be between 1 and 4096

platform/oci/recovery/host-repair.sh is 10231 bytes and gzip+base64 of it is 4749 bytes: both
over the limit. So the transport is chunked, and the chunking has to be RIGHT -- the chunks are
appended to one file on the host, in order, and the host decodes them and runs the script as
root. Two ways to get that wrong, both invisible in a diff:

  * a request over the limit      -> OCI refuses the whole door again
  * chunks out of order or lost   -> the host decodes garbage, or a truncated script

So the falsifier here runs the real transport against a fake `oci` that EXECUTES the shell it
is handed, in a sandbox, and then checks the bytes that came out the other end. Nothing is
mocked above the OCI CLI boundary: the helper's own subprocess calls, its payload encoding, its
command text and its exit-code parsing are all the real ones.

This is the falsifier, not the fix: against a helper that inlines the script, or that does not
run it as root, or that loses a chunk, these fail.
"""

from __future__ import annotations

import base64
import gzip
import importlib.util
import json
import os
import subprocess
import sys

import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
HELPER_PATH = REPO / "platform" / "oci" / "recovery" / "run-command.py"
WORKFLOW = REPO / ".github" / "workflows" / "recovery-data.yml"
HOST_REPAIR = REPO / "platform" / "oci" / "recovery" / "host-repair.sh"
DATA_VOLUMES = REPO / "platform" / "oci" / "recovery" / "data-volumes.sh"
CLOUD_INIT = REPO / "platform" / "oci" / "cloud-init" / "recovery-host.yaml"

MAX_CONTENT = 4096


def _load_helper():
    spec = importlib.util.spec_from_file_location("run_command_helper", HELPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = _load_helper()


# ---------------------------------------------------------------- the fake oci


FAKE_OCI = '''#!/usr/bin/env python3
"""A fake `oci` that executes the Run Command body it is handed, in a sandbox."""
import json, os, subprocess, sys

SANDBOX = {sandbox!r}
BIN = {bin!r}

args = sys.argv[1:]


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


if args[:3] == ["compute", "instance", "list"]:
    print("ocid1.instance.oc1.test.recovery")
    sys.exit(0)

if args[:3] == ["instance-agent", "plugin", "list"]:
    print(os.environ.get("FAKE_PLUGIN_STATUS", "RUNNING"))
    sys.exit(0)

if args[:3] == ["instance-agent", "command-execution", "list"]:
    if opt("--lifecycle-state") == "ACCEPTED":
        print(os.environ.get("FAKE_ACCEPTED_COMMANDS", "[]"))
    else:
        print(os.environ.get("FAKE_IN_PROGRESS_COMMANDS", "[]"))
    sys.exit(0)

if args[:3] == ["instance-agent", "command", "create"]:
    content = json.loads(opt("--content"))
    text = content["source"]["text"]
    assert len(text) <= 4096, "the fake refuses an over-long body, like OCI does"
    index = len(os.listdir(os.path.join(SANDBOX, "outputs"))) + 1
    cid = "cmd-%03d" % index
    # Rewrite the host paths into the sandbox and run the body for real.
    rewritten = text.replace("/var/tmp/", os.path.join(SANDBOX, "var", "tmp") + "/")
    env = dict(os.environ)
    env["PATH"] = BIN + os.pathsep + env["PATH"]
    proc = subprocess.run(
        ["bash", "-c", rewritten], capture_output=True, text=True, env=env, cwd=SANDBOX
    )
    out = proc.stdout + ("\\n" + proc.stderr if proc.stderr else "")
    with open(os.path.join(SANDBOX, "outputs", cid), "w") as fh:
        fh.write(out)
    with open(os.path.join(SANDBOX, "bodies.txt"), "a") as fh:
        fh.write(json.dumps({{"id": cid, "text": text}}) + "\\n")
    print(cid)
    sys.exit(0)

if args[:3] == ["instance-agent", "command-execution", "get"]:
    query = opt("--query", "")
    cid = opt("--command-id")
    if "lifecycle-state" in query:
        print("SUCCEEDED")
        sys.exit(0)
    path = os.path.join(SANDBOX, "outputs", cid)
    sys.stdout.write(open(path).read() if os.path.exists(path) else "")
    sys.exit(0)

sys.stderr.write("fake oci: unsupported call %r\\n" % (args,))
sys.exit(1)
'''

FAKE_SUDO = """#!/bin/sh
# A fake sudo: drop the sudo-only flags and run the command as the caller.
while [ $# -gt 0 ]; do
  case "$1" in
    -n|-H|-E) shift ;;
    *) break ;;
  esac
done
exec "$@"
"""


def _sandbox(tmp_path: Path) -> tuple[Path, Path]:
    """Build the fake oci, the fake sudo and the sandbox directories."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sandbox = tmp_path / "sandbox"
    (sandbox / "outputs").mkdir(parents=True)
    (sandbox / "var" / "tmp").mkdir(parents=True)

    oci = bin_dir / "oci"
    oci.write_text(FAKE_OCI.format(sandbox=str(sandbox), bin=str(bin_dir)))
    oci.chmod(0o755)

    sudo = bin_dir / "sudo"
    sudo.write_text(FAKE_SUDO)
    sudo.chmod(0o755)
    return bin_dir, sandbox


def _run_helper(
    tmp_path: Path, script: Path, mode: str = "repair"
) -> tuple[int, str, Path]:
    bin_dir, sandbox = _sandbox(tmp_path)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    proc = subprocess.run(
        [
            sys.executable,
            str(HELPER_PATH),
            "--script",
            str(script),
            "--mode",
            mode,
            "--compartment",
            "ocid1.compartment.oc1.test",
            "--run-id",
            "test",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout + proc.stderr, sandbox


def _bodies(sandbox: Path) -> list[str]:
    path = sandbox / "bodies.txt"
    if not path.exists():
        return []
    return [
        json.loads(line)["text"]
        for line in path.read_text().splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------- the tests


def test_the_real_host_script_fits_the_limit_when_chunked() -> None:
    """The measured script (10231 bytes) must produce requests OCI accepts."""
    for script in (HOST_REPAIR, DATA_VOLUMES):
        payload = helper.encode_payload(script.read_bytes())
        chunks = helper.plan_chunks(payload, helper.DEFAULT_CHUNK_SIZE)
        for index, chunk in enumerate(chunks):
            text = helper.chunk_command(chunk, first=index == 0)
            assert len(text) <= MAX_CONTENT, (
                f"{script.name} chunk {index} is {len(text)} characters; OCI refuses above "
                f"{MAX_CONTENT}"
            )
    repair_chunks = helper.plan_chunks(
        helper.encode_payload(HOST_REPAIR.read_bytes()), helper.DEFAULT_CHUNK_SIZE
    )
    assert len(repair_chunks) > 1, (
        "host-repair.sh must be split: it is 10231 bytes and gzip+base64 of it is 4749, both "
        "over OCI's 4096-character limit"
    )


def test_the_encoding_is_deterministic() -> None:
    """The same script must always encode to the same bytes, or the tests lie."""
    script = b"#!/usr/bin/env bash\necho estate\n" * 50
    first = helper.encode_payload(script)
    second = helper.encode_payload(script)
    assert first == second
    container = base64.b64decode(first)
    assert container[4:8] == b"\x00\x00\x00\x00", "the gzip mtime must be zeroed"


def test_the_report_slices_carry_explicit_markers() -> None:
    """The instance agent adds its own newlines; the slice bytes cannot be guessed."""
    command = helper.slice_command(0)
    assert helper.SLICE_OPEN in command
    assert helper.SLICE_CLOSE in command
    assert "\\n" not in command, (
        "the markers must not carry a newline of their own, or every slice would start with "
        "one and the reassembled report would not be the host's bytes"
    )
    captured = "<<SLICE>>line one\nline two<<END>>\n"
    assert helper.parse_slice(captured) == "line one\nline two"
    assert helper.parse_slice("no markers here") == ""


def test_the_final_command_compresses_the_report_on_the_host() -> None:
    """The report must travel compressed, or the door costs one command per 900 bytes."""
    body = helper.final_command("repair")
    assert "gzip -c" in body, body
    assert "base64" in body, body
    assert "report_b64_bytes=" in body, body
    assert "tr -d" in body, (
        "GNU base64 wraps its output at 76 columns; the newlines must be stripped or the "
        "reassembled payload will not decode"
    )


def test_the_slices_carry_the_compressed_report_not_the_raw_text() -> None:
    """One protocol, one place: the slices read what the final command wrote."""
    body = helper.slice_command(0)
    assert helper.REPORT_B64_PATH in body, body
    assert helper.REPORT_PATH not in body, body
    later = helper.slice_command(helper.SLICE_BYTES)
    assert helper.REPORT_B64_PATH in later, later


def test_the_report_travels_compressed_so_the_door_costs_a_few_commands() -> None:
    """Measured: a 15675-byte report took 18 raw slices, one agent poll each, about an hour.

    The compressed report must cost a handful of commands, or every governed door use
    risks the 120-minute CI job timeout.
    """
    report = ("estate-router: unit active=enabled\n" * 600).encode()[:15675]
    assert len(report) == 15675
    payload = helper.encode_report(report)
    slices = (len(payload) + helper.SLICE_BYTES - 1) // helper.SLICE_BYTES
    assert slices <= 6, (
        f"the door must cost a handful of Run Commands, not {slices} "
        f"({len(payload)} compressed bytes)"
    )
    assert helper.decode_report(payload) == report


def test_the_compressed_report_round_trips_through_the_slice_protocol() -> None:
    """The report the founder reads must be the host's bytes, through the real markers."""
    report = bytes(range(256)) * 60
    payload = helper.encode_report(report)
    pieces = []
    for offset in range(0, len(payload), helper.SLICE_BYTES):
        captured = (
            helper.SLICE_OPEN
            + payload[offset : offset + helper.SLICE_BYTES]
            + helper.SLICE_CLOSE
        )
        pieces.append(helper.parse_slice(captured))
    assert helper.decode_report("".join(pieces)) == report


def test_the_slices_reassemble_the_report_byte_for_byte(tmp_path: Path) -> None:
    """The report the founder reads must be the host's bytes, not a marker-laced copy."""
    body = "".join(f"estate line {i} " + "-" * 40 + "\n" for i in range(60))
    report = tmp_path / "report.txt"
    report.write_text(body)
    pieces = []
    for offset in range(0, len(body), helper.SLICE_BYTES):
        captured = (
            helper.SLICE_OPEN
            + body[offset : offset + helper.SLICE_BYTES]
            + helper.SLICE_CLOSE
        )
        pieces.append(helper.parse_slice(captured))
    assert "".join(pieces) == body, "the reassembled report must equal the host's bytes"
    assert helper.parse_slice(helper.SLICE_OPEN + body + helper.SLICE_CLOSE) == body


def test_the_chunks_reassemble_the_script_byte_for_byte() -> None:
    """The payload the host decodes must be the script, not a prefix or a scramble."""
    script = os.urandom(500)
    payload = helper.encode_payload(script)
    chunks = helper.plan_chunks(payload, 16)
    assert len(chunks) > 2, "the fixture must actually be split"
    assert helper.reassemble(chunks) == payload
    assert gzip.decompress(base64.b64decode(helper.reassemble(chunks))) == script


def test_the_first_chunk_truncates_and_the_rest_append() -> None:
    """Order is the protocol: the file is written once, then appended, in order."""
    payload = helper.encode_payload(os.urandom(500))
    chunks = helper.plan_chunks(payload, 100)
    assert " > /var/tmp/estate-payload.b64" in helper.chunk_command(
        chunks[0], first=True
    )
    assert " >> /var/tmp/estate-payload.b64" in helper.chunk_command(
        chunks[1], first=False
    )
    for chunk in chunks[1:]:
        assert " > " not in helper.chunk_command(chunk, first=False)


def test_the_transport_runs_the_script_on_the_host_and_reports_its_exit_code(
    tmp_path: Path,
) -> None:
    """End to end against the fake oci: the script runs, its output comes back, its code is ours."""
    script = tmp_path / "host-script.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'echo "MODE=$1"\n'
        'for i in $(seq 1 40); do echo "filler line $i ----------------"; done\n'
        "exit 7\n"
    )
    code, output, _sandbox_dir = _run_helper(tmp_path, script, mode="repair")

    assert code == 7, f"the helper must exit with the script's own code: {output}"
    assert "MODE=repair" in output, f"the host's output must come back: {output}"
    assert "filler line 40" in output, f"the whole report must come back: {output}"
    assert "host exit=7" in output, output


def test_the_transport_runs_the_script_as_root_through_sudo(tmp_path: Path) -> None:
    """The host's Run Command agent is `ocarun`, not root; the script must be elevated."""
    script = tmp_path / "host-script.sh"
    script.write_text("#!/usr/bin/env bash\necho whoami\n")
    _code, _output, sandbox = _run_helper(tmp_path, script, mode="identify")
    bodies = _bodies(sandbox)
    assert bodies, "no Run Command body was sent"
    finals = [b for b in bodies if "exit=$rc" in b]
    assert finals, f"no body ran the script: {bodies}"
    final = finals[0]
    assert "-n bash /var/tmp/host-script.sh identify" in final, final
    assert "sudo" in final, f"the script must be run through sudo: {final}"
    assert "exit=$rc" in final, (
        f"the host must report the script's own exit code: {final}"
    )


def test_the_host_scripts_elevate_themselves_before_the_instance_principal_export() -> (
    None
):
    """data-volumes.sh must be root before it asks for instance-principal auth."""
    text = DATA_VOLUMES.read_text()
    elevate = text.index('exec sudo -n bash "$0" "$@"')
    export = text.index("export OCI_CLI_AUTH=instance_principal")
    assert elevate < export, (
        "the elevation must come before the instance-principal export"
    )

    repair = HOST_REPAIR.read_text()
    elevate = repair.index('exec sudo -n bash "$0" "$@"')
    first_privileged = repair.index("systemctl ")
    assert elevate < first_privileged, (
        "host-repair.sh must elevate itself before it touches systemd: Run Command executes as "
        "ocarun, not root"
    )


def test_the_workflow_calls_the_helper_and_builds_no_run_command_body_itself() -> None:
    """One place builds the Run Command, and that place is the tested helper."""
    text = WORKFLOW.read_text()
    assert "platform/oci/recovery/run-command.py" in text, text
    assert "--content" not in text, "the workflow must not build a Run Command body"
    assert "sourceType" not in text, "the workflow must not build a Run Command body"
    assert "instance-agent command create" not in text, text
    for mode in ("identify", "copy", "repair"):
        assert mode in text, f"the {mode} mode must survive the rewrite"


def test_no_workflow_builds_a_run_command_body_anymore() -> None:
    """The door is opened by the helper; a second builder is a second copy to drift."""
    for path in sorted((REPO / ".github" / "workflows").glob("*.y*ml")):
        assert "instance-agent command create" not in path.read_text(), path


def test_cloud_init_enables_each_unit_independently() -> None:
    """One failing unit must not abort the rest, and the timer must be enabled (2026-10-30)."""
    text = CLOUD_INIT.read_text()
    assert "estate-router.service, estate-tunnel.service" not in text, (
        "the combined systemctl enable --now aborted on the first failing unit and left "
        "estate-router-refresh.timer disabled"
    )
    for unit in (
        "estate-router.service",
        "estate-tunnel.service",
        "estate-router-refresh.timer",
    ):
        assert f"systemctl enable --now {unit}" in text, (
            f"{unit} is not enabled on its own"
        )
    runcmd = text.split("runcmd:", 1)[1]
    enables = [
        line
        for line in runcmd.splitlines()
        if "systemctl enable --now" in line and not line.strip().startswith("#")
    ]
    assert len(enables) == 3, f"each unit gets its own enable: {enables}"


def test_the_repair_enables_the_refresh_timer_on_the_live_host() -> None:
    """The live host's timer was active=inactive enabled=static: nothing scheduled it."""
    text = HOST_REPAIR.read_text()
    assert "systemctl enable --now estate-router-refresh.timer" in text, text


def test_recovery_host_census_launches_only_from_governed_main():
    """An unreviewed lane must never mint the OCI token for host Run Command."""
    workflow = WORKFLOW.read_text()
    assert "  push:\n    branches: [main]\n" in workflow
    assert "      - .github/workflows/recovery-data.yml" in workflow
    assert "      - platform/oci/recovery/data-volumes.sh" in workflow
    assert "    if: github.ref == 'refs/heads/main'" in workflow
    assert "MODE: ${{ inputs.mode || 'identify' }}" in workflow
    assert workflow.index("    if: github.ref == 'refs/heads/main'") < workflow.index(
        "      - name: OCI session token from the GitHub OIDC token"
    )
    assert "  pull_request:" not in workflow
    assert "  pull_request_target:" not in workflow


def test_recovery_identify_never_silently_succeeds_without_all_three_volumes():
    """No disks on AD-2 cannot be recorded as a recovered AD-1 database."""
    source = DATA_VOLUMES.read_text()
    assert 'case "$MODE" in' in source
    assert "identify|copy)" in source
    assert 'if [ "$MODE" = copy ]; then' in source
    assert source.index('if [ "$MODE" = copy ]; then') < source.index('command -v zstd')
    assert 'seen=0' in source
    assert 'seen=$((seen + 1))' in source
    assert 'if [ "$seen" -lt 3 ]; then' in source
    assert "FAIL    data-volumes  only %s of 3 required data volumes" in source
    assert "mountpoint -q" in source
    assert "findmnt -no OPTIONS" in source
    assert "was already mounted writable or unreadable" in source
    assert "mount -o ro,noload" in source
    assert "mount -o ro" in source


def test_volume_census_rejects_unrecognised_mode_before_any_oci_access():
    """The real host script must refuse malformed dispatch before touching cloud."""
    run = subprocess.run(
        ["bash", str(DATA_VOLUMES), "unexpected-mode"],
        capture_output=True, text=True, timeout=5,
    )
    assert run.returncode == 64, (run.stdout, run.stderr)
    assert "invalid mode unexpected-mode" in run.stderr


def test_oci_cli_call_is_hard_bounded_and_fails_blind(monkeypatch):
    """A single OCI read cannot hold a GitHub runner for an hour."""
    observed = []

    def hang(argv, **kwargs):
        observed.append((argv, kwargs.get("timeout")))
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(helper, "_oci_binary", lambda: "/usr/bin/oci")
    monkeypatch.setattr(helper.subprocess, "run", hang)
    with pytest.raises(helper.TransportError, match="45-second per-call deadline"):
        helper._oci(["instance-agent", "command-execution", "get"], what="polling")
    assert observed[0][1] == 45


def test_unclaimed_oci_command_times_out_with_command_id_and_last_state(monkeypatch):
    """Pending is a state, not successful host execution."""
    clock = [0.0]

    monkeypatch.setattr(helper.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(helper.time, "sleep", lambda duration: clock.__setitem__(0, clock[0] + duration))
    monkeypatch.setattr(helper, "_oci", lambda *args, **kwargs: "PENDING")
    with pytest.raises(helper.TransportError) as error:
        helper.wait_for_command("cmd-042", "recovery-1", poll_seconds=2, wait_timeout=5)
    detail = str(error.value)
    assert "cmd-042" in detail and "recovery-1" in detail
    assert "last_state=PENDING" in detail
    assert clock[0] == 5.0


def test_unexpected_oci_state_is_blind_not_success(monkeypatch):
    monkeypatch.setattr(helper, "_oci", lambda *args, **kwargs: "UNKNOWN")
    with pytest.raises(helper.TransportError, match="unexpected lifecycle"):
        helper.wait_for_command("cmd-043", "recovery-1", 2, 30)


def test_failed_oci_poll_preserves_command_identity(monkeypatch):
    def refused(*args, **kwargs):
        raise helper.TransportError("Abort: instance agent unreachable")
    monkeypatch.setattr(helper, "_oci", refused)
    with pytest.raises(helper.TransportError) as error:
        helper.wait_for_command("cmd-044", "recovery-1", 2, 30)
    assert "cmd-044" in str(error.value)
    assert "unreachable" in str(error.value)


def test_known_terminal_oci_states_preserve_failure_semantics(monkeypatch):
    for state in ("SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELED"):
        monkeypatch.setattr(helper, "_oci", lambda *args, state=state, **kwargs: state)
        assert helper.wait_for_command("cmd-045", "recovery-1", 1, 3) == state


def test_identify_is_bounded_without_shortening_copy_or_repair():
    workflow = WORKFLOW.read_text()
    assert "if [ \"$MODE\" = identify ]; then probe_budget=180; fi" in workflow
    assert "probe_budget=3600" in workflow
    assert '  schedule:\n    - cron: "19 7 * * *"' in workflow
    assert "MODE: ${{ inputs.mode || 'identify' }}" in workflow
    assert '--wait-timeout "$probe_budget"' in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow


def test_recovery_failure_reporter_has_independent_least_privilege_and_no_oci():
    """A down agent never suppresses a P0, and a reporter cannot mint OCI auth."""
    workflow = WORKFLOW.read_text()
    reporter = workflow.split("\n  report-recovery-failure:", 1)
    assert len(reporter) == 2
    assert "needs: [run]" in reporter[1]
    assert "always()" in reporter[1]
    assert "needs.run.result != 'success'" in reporter[1]
    assert "github.ref == 'refs/heads/main'" in reporter[1]
    assert "      issues: write" in reporter[1]
    assert "id-token: write" not in reporter[1]
    assert "OCI session token from the GitHub OIDC token" not in reporter[1]
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in reporter[1]
    assert "OCI_RECOVERY_RUN:" in reporter[1]
    assert "gh api -X POST" in reporter[1]
    assert "issues/7387/comments" in reporter[1]
    assert 'comments=$(gh api' in reporter[1]
    assert 'echo "BLIND recovery issue history unreadable"' in reporter[1]
    assert "cancel-in-progress: false" in reporter[1]
    # Never create duplicate incident authority or infer that red means recovered.
    assert "issues -X POST" not in reporter[1]
    assert "Do not mutate data volumes" in reporter[1]


def test_disabled_oci_agent_plugin_refuses_transport_before_any_command(
    tmp_path: Path, monkeypatch
) -> None:
    """A healthy VM does not imply that its Run Command agent is running."""
    script = tmp_path / "identify.sh"
    script.write_text("#!/bin/sh\necho should-not-run\n")
    monkeypatch.setenv("FAKE_PLUGIN_STATUS", "STOPPED")
    code, output, sandbox = _run_helper(tmp_path, script, mode="identify")
    assert code == 70, output
    assert "plugin_status=STOPPED" in output
    assert "no script submitted" in output
    assert _bodies(sandbox) == [], "No payload chunk may reach an inactive agent"


def test_running_agent_plugin_is_independently_confirmed_before_submission(
    tmp_path: Path, monkeypatch
) -> None:
    script = tmp_path / "identify.sh"
    script.write_text("#!/bin/sh\necho confirmed-plugin\n")
    monkeypatch.setenv("FAKE_PLUGIN_STATUS", "RUNNING")
    code, output, sandbox = _run_helper(tmp_path, script, mode="identify")
    assert code == 0, output
    assert "plugin_status=RUNNING" in output
    assert "confirmed-plugin" in output
    assert _bodies(sandbox), "Expected the real command transport to execute"


def test_oci_agent_plugin_query_is_specific_to_the_target_instance(monkeypatch):
    recorded = []

    def fake_oci(args, *, what):
        recorded.append(args)
        return "INVALID"

    monkeypatch.setattr(helper, "_oci", fake_oci)
    with pytest.raises(helper.TransportError, match="INVALID"):
        helper.require_run_command_plugin("compartment-1", "instance-1")
    argv = recorded[0]
    assert argv[:3] == ["instance-agent", "plugin", "list"]
    assert argv[argv.index("--instanceagent-id") + 1] == "instance-1"
    assert argv[argv.index("--compartment-id") + 1] == "compartment-1"
    assert argv[argv.index("--name") + 1] == "Compute Instance Run Command"


def test_outstanding_accepted_oci_command_blocks_new_dispatch(
    tmp_path: Path, monkeypatch
) -> None:
    """Five in-flight slots cannot be consumed by repeated blind probes."""
    script = tmp_path / "identify.sh"
    script.write_text("#!/bin/sh\necho must-not-run\n")
    monkeypatch.setenv("FAKE_PLUGIN_STATUS", "RUNNING")
    monkeypatch.setenv("FAKE_ACCEPTED_COMMANDS", json.dumps(["cmd-unfinished-1"]))
    code, output, sandbox = _run_helper(tmp_path, script, mode="identify")
    assert code == 70, output
    assert "pre-existing ACCEPTED command" in output
    assert "cmd-unfinished-1" in output
    assert "no new script submitted" in output
    assert _bodies(sandbox) == []


def test_outstanding_running_oci_command_also_blocks_dispatch(
    tmp_path: Path, monkeypatch
) -> None:
    script = tmp_path / "identify.sh"
    script.write_text("#!/bin/sh\necho must-not-run\n")
    monkeypatch.setenv("FAKE_PLUGIN_STATUS", "RUNNING")
    monkeypatch.setenv("FAKE_IN_PROGRESS_COMMANDS", json.dumps(["cmd-running-2"]))
    code, output, sandbox = _run_helper(tmp_path, script, mode="identify")
    assert code == 70, output
    assert "pre-existing IN_PROGRESS command" in output
    assert _bodies(sandbox) == []


def test_unreadable_oci_command_queue_is_blind(monkeypatch):
    def malformed(args, *, what):
        return "{}"
    monkeypatch.setattr(helper, "_oci", malformed)
    with pytest.raises(helper.TransportError, match="invalid ACCEPTED OCI command list"):
        helper.require_idle_command_queue("compartment", "instance")


def test_empty_oci_command_queue_is_idle(monkeypatch):
    """OCI emits an empty body, not `[]`, when a lifecycle has no commands."""
    calls = []

    def empty(args, *, what):
        calls.append(args)
        return ""

    monkeypatch.setattr(helper, "_oci", empty)
    helper.require_idle_command_queue("compartment", "instance")
    assert len(calls) == 2


def test_idle_oci_queue_preflight_uses_exact_instance_and_read_only_list(monkeypatch):
    calls = []

    def empty(args, *, what):
        calls.append(args)
        return "[]"

    monkeypatch.setattr(helper, "_oci", empty)
    helper.require_idle_command_queue("compartment-7", "instance-7")
    assert len(calls) == 2
    assert [args[args.index("--lifecycle-state")+1] for args in calls] == [
        "ACCEPTED", "IN_PROGRESS"
    ]
    for argv in calls:
        assert argv[:3] == ["instance-agent", "command-execution", "list"]
        assert argv[argv.index("--instance-id")+1] == "instance-7"
        assert argv[argv.index("--compartment-id")+1] == "compartment-7"
        assert "--all" in argv
        assert "create" not in argv and "cancel" not in argv
