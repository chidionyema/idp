"""crew#483 / crew#388, 2026-08-28: the telemetry-coverage receipt (run 33156980292, 08:45Z)
printed `pods_running=80 pods_seen=1 missing=80 backend_errors={}`. The collector answered, the
backend answered, and almost nothing landed in ClickHouse -- and nothing in CI ever printed the
collector's own logs: `pb_diagnose` tails a pod's log only when the pod is NOT ready, and both
telemetry components were Ready throughout the outage.

This adds a read-only telemetry section to `diagnose`: pod health for signoz-otel-collector and
both k8s-infra components (the agent DaemonSet, the deployment), each one's own log, the
collector's live receiver/exporter config, ClickHouse row counts for the last 15 minutes from the
same three tables telemetry-coverage.yaml queries, the OTLP endpoint every workload is told to
use, and which Deployments actually carry that env var. These tests run it against a recording
fake kubectl on PATH -- no real cluster, no network socket -- the same pattern
test_incident_crew539_break_glass_admits_the_runner_for_one_job.py uses for every other playbook.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"
MUTATING = re.compile(r"^(kubectl|flux) (delete|apply|rollout|run|reconcile|patch|create|scale|edit|replace)\b")


def _fake_path(tmp_path: Path) -> tuple[Path, Path]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return bin_dir, log


def _run_diagnose(tmp_path: Path, kubectl_script: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Writes a fake kubectl that switches on `$*`, always logs the call, runs diagnose."""
    bin_dir, log = _fake_path(tmp_path)
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n" + kubectl_script
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "diagnose"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines() if log.exists() else []
    return p, calls


DEFAULT_SWITCH = 'case "$*" in *) cat >/dev/null 2>&1; echo ok;; esac\n'


def test_telemetry_section_exists_and_prints_every_row(tmp_path):
    p, calls = _run_diagnose(tmp_path, DEFAULT_SWITCH)
    assert p.returncode == 0, p.stdout + p.stderr
    for header in (
        "--- telemetry-pods-observability",
        "--- telemetry-pods-observability-agent",
        "--- collector-log",
        "--- k8s-infra-agent-log",
        "--- k8s-infra-deployment-log",
        "--- collector-config",
        "--- clickhouse-counts-15m",
        "--- otlp-endpoint-declared",
        "--- otlp-endpoint-workloads",
    ):
        assert header in p.stdout, p.stdout
    assert [c for c in calls if MUTATING.match(c)] == [], "telemetry section must be read-only"


def test_telemetry_pods_are_read_with_o_wide_per_namespace(tmp_path):
    _, calls = _run_diagnose(tmp_path, DEFAULT_SWITCH)
    assert any("get pods -n observability -o wide" in c for c in calls)
    assert any("get pods -n observability-agent -o wide" in c for c in calls)


def test_missing_collector_pod_names_the_reason_not_silence(tmp_path):
    # no pod named *otel-collector* anywhere: the section says so instead of printing nothing,
    # which is exactly the silence a chart rename of the Deployment would otherwise cause.
    switch = (
        'case "$*" in\n'
        '  *"get pods -n observability -o jsonpath"*) printf "";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, _ = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "no pod matching *otel-collector* in observability" in p.stdout, p.stdout


def test_collector_and_agent_logs_read_all_containers_with_prefix(tmp_path):
    switch = (
        'case "$*" in\n'
        '  *"get pods -n observability -o jsonpath"*) printf "signoz-otel-collector-abc12\\n";;\n'
        '  *"get pods -n observability-agent -o jsonpath"*) printf "k8s-infra-otel-agent-x\\nk8s-infra-otel-deployment-y\\n";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, calls = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert any("logs signoz-otel-collector-abc12 -n observability --all-containers --tail=80 --prefix" in c for c in calls)
    assert any("logs k8s-infra-otel-agent-x -n observability-agent --all-containers --tail=80 --prefix" in c for c in calls)
    assert any("logs k8s-infra-otel-deployment-y -n observability-agent --all-containers --tail=80 --prefix" in c for c in calls)


def test_telemetry_logs_are_redacted(tmp_path):
    # a token or password an app printed by mistake never reaches CI output (LAW 21).
    switch = (
        'case "$*" in\n'
        '  *"get pods -n observability -o jsonpath"*) printf "signoz-otel-collector-abc12\\n";;\n'
        '  *"logs signoz-otel-collector-abc12"*) echo "auth failed password=hunter2hunter2 for user";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, _ = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "hunter2hunter2" not in p.stdout, p.stdout
    # redact() (crew#516, bin/idp-oke-break-glass) is the one redaction helper in bin/; this only
    # proves show_redacted routes through it, not its exact replacement text.
    assert "password=<REDACTED>" in p.stdout, p.stdout


def test_clickhouse_counts_query_the_three_tables_for_the_last_15_minutes(tmp_path):
    switch = (
        'case "$*" in\n'
        '  *"get pods -n observability -l clickhouse.altinity.com/chi -o jsonpath"*) printf "chi-signoz-clickhouse-cluster-0-0-0";;\n'
        '  *"get secret clickhouse-auth -n observability -o jsonpath"*) printf "aHVudGVyMg==";;\n'
        '  *"exec -n observability chi-signoz-clickhouse-cluster-0-0-0"*) echo "42";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, calls = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    execs = [c for c in calls if "exec -n observability chi-signoz-clickhouse-cluster-0-0-0" in c]
    assert len(execs) == 3, calls
    joined = "\n".join(execs)
    assert "signoz_logs.distributed_logs_v2" in joined and "- 900) * 1000000000" in joined
    assert "signoz_traces.distributed_signoz_index_v3" in joined and "INTERVAL 900 SECOND" in joined
    assert "signoz_metrics.distributed_time_series_v4" in joined and "- 900) * 1000" in joined
    for e in execs:
        assert "--user admin --password" in e and "-q" in e
    assert [c for c in calls if MUTATING.match(c)] == []


def test_missing_clickhouse_pod_names_the_reason_not_silence(tmp_path):
    switch = (
        'case "$*" in\n'
        '  *"get pods -n observability -l clickhouse.altinity.com/chi -o jsonpath"*) printf "";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, _ = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "no pod with label clickhouse.altinity.com/chi in observability" in p.stdout, p.stdout


def test_collector_config_dump_filters_to_receiver_exporter_endpoint_lines(tmp_path):
    yaml_body = (
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: signoz-otel-collector\n"
        "data:\n  otel-collector-config.yaml: |\n"
        "    receivers:\n      otlp:\n        protocols:\n          grpc:\n            endpoint: 0.0.0.0:4317\n"
        "    exporters:\n      clickhousetracesexporter:\n        datasource: tcp://signoz-clickhouse:9000\n"
        "    unrelated_noise_key: this line must not appear in the filtered dump\n"
    )
    switch = (
        'case "$*" in\n'
        '  *"get configmap -n observability -o name"*) printf "configmap/signoz-otel-collector\\n";;\n'
        '  *"get configmap signoz-otel-collector -n observability -o yaml"*) cat <<\'CFG\'\n' + yaml_body + 'CFG\n'
        ';;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, calls = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "receivers:" in p.stdout and "exporters:" in p.stdout and "endpoint: 0.0.0.0:4317" in p.stdout
    assert "clickhousetracesexporter:" in p.stdout and "datasource: tcp://signoz-clickhouse:9000" in p.stdout
    assert "unrelated_noise_key" not in p.stdout, p.stdout
    assert any("get configmap -n observability -o name" in c for c in calls)


def test_missing_collector_configmap_names_the_reason_not_silence(tmp_path):
    switch = (
        'case "$*" in\n'
        '  *"get configmap -n observability -o name"*) printf "";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, _ = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "no ConfigMap matching *otel-collector* in observability" in p.stdout, p.stdout


def test_otlp_endpoint_is_read_from_the_live_helmrelease_and_workloads_are_filtered_to_the_ones_that_carry_it(tmp_path):
    switch = (
        'case "$*" in\n'
        '  *"get helmrelease k8s-infra -n observability -o jsonpath"*) printf "k8s-infra otelCollectorEndpoint: signoz-otel-collector.observability.svc:4317\\n";;\n'
        # matched on OTEL_EXPORTER_OTLP_ENDPOINT rather than "get deploy -A -o jsonpath": the
        # existing stalled-deployments row (pb_diagnose) also runs `get deploy -A -o jsonpath=...`
        # and must not be intercepted by this fixture.
        '  *"OTEL_EXPORTER_OTLP_ENDPOINT"*) printf "llm/litellm\\thttp://signoz-otel-collector.observability.svc:4318\\nobservability/signoz-otel-collector\\t\\n";;\n'
        '  *) cat >/dev/null 2>&1; echo ok;;\nesac\n'
    )
    p, calls = _run_diagnose(tmp_path, switch)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "signoz-otel-collector.observability.svc:4317" in p.stdout
    assert "llm/litellm" in p.stdout and "http://signoz-otel-collector.observability.svc:4318" in p.stdout
    assert "observability/signoz-otel-collector\t" not in p.stdout, "a Deployment with no OTLP env var is not listed"
    assert any("get helmrelease k8s-infra -n observability -o jsonpath" in c for c in calls)


def test_telemetry_section_runs_after_the_existing_diagnose_rows(tmp_path):
    # the pre-existing diagnose content (nodes, kustomizations, warnings) still runs; the
    # telemetry section is an addition, not a replacement.
    p, _ = _run_diagnose(tmp_path, DEFAULT_SWITCH)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--- nodes" in p.stdout and "--- warnings" in p.stdout
    assert p.stdout.index("--- warnings") < p.stdout.index("--- telemetry-pods-observability")


def test_list_and_playbook_case_are_unchanged():
    # this is a section inside `diagnose`, not a new playbook: --list gets no new name from this
    # change. (crew#516, merged after this branch, added architect-doctor independently -- the
    # canonical --list assertion lives in test_incident_crew539_..., this only checks this PR
    # didn't add one of its own.)
    listed = subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True).stdout.split()
    assert "telemetry" not in listed
    assert listed.count("diagnose") == 1
