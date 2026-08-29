"""crew#631 CP6: a change to platform/observability/langfuse* cannot merge on an old or missing
verdict. The gate reads the newest completed verdict-langfuse.yml run on main and grades its
verdict file with probes.verdict.grade; a change off the surface passes and says so.
The fake `gh` reads its answers from files, never from a quoted shell string (2026-08-29 CP2: a
printf inside the fake stripped the single quotes the real tool returns)."""

import json
import os
import subprocess
import time
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
GATE = IDP / "bin" / "idp-verdict-fresh"
LANGFUSE = "platform/observability/langfuse.yaml"


def verdict(age_s, outcome="PASS", digest="sha256:abc"):
    done = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - age_s))
    return {
        "verdict_id": "v1",
        "check_id": "langfuse",
        "target": "langfuse.example",
        "commit_sha": "0" * 40,
        "artifact_digest": digest,
        "config_revision": "3",
        "nonce": "n1",
        "started_at": done,
        "completed_at": done,
        "ttl_seconds": 3600,
        "outcome": outcome,
        "assertions": [
            {"name": "a", "expected": "1", "actual": "1", "ok": outcome == "PASS"}
        ],
        "evidence_ref": "https://example/run/1",
        "prover_id": "estate-ci",
        "prover_run_id": "1",
        "sig": "deadbeef",
    }


def fake_gh(tmp, run, verdict_obj):
    """A gh that answers the runs query from run.json and `run download` from verdict.json."""
    d = tmp / "bin"
    d.mkdir()
    (tmp / "run.json").write_text(json.dumps(run) if run else "null")
    if verdict_obj is not None:
        (tmp / "verdict.json").write_text(json.dumps(verdict_obj))
    (d / "gh").write_text(
        "#!/usr/bin/env bash\n"
        'case "$1" in\n'
        f'  api) cat "{tmp}/run.json";;\n'
        '  run) while [ $# -gt 0 ]; do [ "$1" = -D ] && dest=$2; shift; done;\n'
        f'       [ -f "{tmp}/verdict.json" ] && cp "{tmp}/verdict.json" "$dest/verdict.json"; exit 0;;\n'
        "  *) echo unexpected gh $* >&2; exit 9;;\n"
        "esac\n"
    )
    (d / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", GITHUB_REPOSITORY="o/r")
    return env


def run_gate(env, *args):
    r = subprocess.run(
        [str(GATE), "langfuse", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return r.returncode, r.stdout.strip()


RUN = {"id": 42, "conclusion": "success", "head_sha": "0" * 40, "updated_at": "now"}


def test_a_change_off_the_surface_passes_without_asking_github(tmp_path):
    env = fake_gh(tmp_path, None, None)  # any gh call would answer null -> BLIND
    rc, out = run_gate(env, "--changed", "bin/idp-ci", "docs/x.md")
    assert rc == 0 and out.startswith("ok"), out
    assert "no langfuse file" in out


def test_a_fresh_pass_verdict_lets_a_langfuse_change_through(tmp_path):
    env = fake_gh(tmp_path, RUN, verdict(120))
    rc, out = run_gate(env, "--changed", LANGFUSE)
    assert rc == 0 and out.startswith("ok"), out
    assert "run 42" in out and "sha256:abc" in out


def test_an_expired_verdict_refuses_the_change_and_names_the_command(tmp_path):
    env = fake_gh(tmp_path, RUN, verdict(3601))
    rc, out = run_gate(env, "--changed", LANGFUSE)
    assert rc == 1 and out.startswith("FAIL"), out
    assert "expired" in out and "gh workflow run verdict-langfuse.yml" in out


def test_a_fail_verdict_and_an_unsigned_one_refuse(tmp_path):
    env = fake_gh(tmp_path, RUN, verdict(10, outcome="FAIL"))
    rc, out = run_gate(env, "--changed", LANGFUSE)
    assert rc == 1 and "FAIL" in out, out
    v = verdict(10)
    v.pop("sig")
    (tmp_path / "u").mkdir()
    env = fake_gh(tmp_path / "u", RUN, v)
    rc, out = run_gate(env, "--changed", LANGFUSE)
    assert rc == 1 and "no signature" in out, out


def test_no_prover_run_is_blind_not_green(tmp_path):
    env = fake_gh(tmp_path, None, None)
    rc, out = run_gate(env, "--changed", LANGFUSE)
    assert rc == 2 and out.startswith("BLIND"), out


def test_the_context_is_required_on_main_and_the_job_carries_that_name():
    rs = json.loads(
        (IDP / "platform/github/ruleset.idp.required-checks.json").read_text()
    )
    ctx = [c["context"] for c in rs["rules"][0]["parameters"]["required_status_checks"]]
    assert "verify/verdict-fresh" in ctx
    ci = yaml.safe_load((IDP / ".github/workflows/ci.yml").read_text())
    job = ci["jobs"]["verdict-fresh"]
    assert job["name"] == "verify/verdict-fresh"
    assert job["if"] == "github.event_name == 'pull_request'"
    assert "bin/idp-verdict-fresh langfuse --changed" in job["steps"][-1]["run"]


def test_repo_rulesets_compares_the_required_contexts_not_only_rule_types():
    s = (IDP / "bin/repo-rulesets").read_text()
    assert "{type}]}" not in s, (
        "a hand-edited required-check list read as ok on 2026-08-29"
    )
    assert s.count("{type,parameters}]}") == 2
