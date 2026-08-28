"""Binds features/sovereign-bus/cp0d_kini_finish_trigger.feature (crew#396 step 4).

Rung 4 incident-style checks on the wiring plus a both-ways check of the reader's grader: a
reader only ever seen refusing has never been shown to permit (LAW 45 step 3)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml
from pytest_bdd import given, scenarios, then

IDP = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(IDP))
from sovereign.engine import kini  # noqa: E402

scenarios("features/sovereign-bus/cp0d_kini_finish_trigger.feature")


@given("every status the CLI can report", target_fixture="statuses")
def _statuses() -> dict[str, dict]:
    return {
        "none": {"status": "NONE"},
        "running": {"status": "RUNNING", "progress": {"1": kini.PASS}},
        "green": {"status": "COMPLETED", "result": {"ok": True, "green": ["1"], "red": []}, "close_time": "c"},
        "red": {"status": "COMPLETED", "result": {"ok": False, "green": [], "red": ["1"]}, "close_time": "c"},
        "failed": {"status": "FAILED", "result": {}},
        "unknown": {},
    }


@then('receipt_head maps NONE, RUNNING and a green COMPLETED to "ok" and anything red to "FAIL"')
def _heads(statuses):
    heads = {k: kini.receipt_head(v, now="T") for k, v in statuses.items()}
    for k in ("none", "running", "green"):
        assert heads[k].startswith("ok kini-finish at T status="), heads[k]
    for k in ("red", "failed", "unknown"):
        assert heads[k].startswith("FAIL kini-finish at T status="), heads[k]
    assert "red=1" in heads["red"] and "red_checkpoints=1" in heads["red"]


def _grade(receipt: str, age_min: int = 5, max_age_min: int = 60) -> tuple[int, str]:
    """Run the grader embedded in bin/idp-kini-state (argv: object head JSON, body, max age,
    flag) on a receipt body whose object was last modified age_min minutes ago."""
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime

    src = (IDP / "bin/idp-kini-state").read_text()
    code = src.split("<<'PY'", 1)[1].split("\nPY", 1)[0]
    lm = format_datetime(datetime.now(timezone.utc) - timedelta(minutes=age_min), usegmt=True)
    head = json.dumps({"last-modified": lm})
    p = subprocess.run([sys.executable, "-c", code, head, receipt, str(max_age_min), ""], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


@then("bin/idp-kini-state passes a fresh green receipt and refuses a red or stale one")
def _reader_both_ways():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    fresh = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = json.dumps({"ok": True})
    rc, out = _grade(f"ok kini-finish at {fresh} status=COMPLETED green=7 red=0 finished=c\n{body}\n")
    assert rc == 0 and out.startswith("ok      kini-finish"), out
    rc, out = _grade(f"ok kini-finish at {fresh} status=NONE green=0 red=0 finished=- (never started)\n{body}\n")
    assert rc == 0, out
    rc, out = _grade(f"FAIL kini-finish at {fresh} status=COMPLETED green=6 red=1 finished=c red_checkpoints=4\n{body}\n")
    assert rc != 0 and out.startswith("FAIL    kini-finish"), out
    rc, out = _grade(f"ok kini-finish at {stale} status=COMPLETED green=7 red=0 finished=c\n{body}\n", age_min=180)
    assert rc != 0 and "min old" in out, out


@given("the workflow kini-finish.yml", target_fixture="wf")
def _wf() -> dict:
    return yaml.safe_load((IDP / ".github/workflows/kini-finish.yml").read_text())


@then("it fires on an owner's `FINISH: KINI` comment, renames the Job and arms auto-merge")
def _wf_shape(wf):
    on = wf.get("on") or wf.get(True)
    assert "issue_comment" in on and "workflow_dispatch" in on, on
    job = wf["jobs"]["request"]
    assert "startsWith(github.event.comment.body, 'FINISH: KINI')" in job["if"]
    assert "github.event.comment.user.login == github.repository_owner" in job["if"]
    run = "\n".join(s.get("run", "") for s in job["steps"])
    assert "kini-finish-$REQUEST" in run and "platform/temporal/kini-finish.yaml" in run
    assert "gh pr merge" in run and "--auto" in run
    assert "SEED_FLUX_WRITER_IDENTITY_B64" in json.dumps(job), "must push with the Flux writer key so checks run"


@then("platform/temporal renders the Job and the kini-state CronJob on the worker image and service account")
def _render():
    out = subprocess.run(["kubectl", "kustomize", str(IDP / "platform/temporal")], capture_output=True, text=True, check=True).stdout
    docs = {(d["kind"], d["metadata"]["name"]): d for d in yaml.safe_load_all(out) if d}
    # The request renames the Job to kini-finish-<run id> (crew#406), so find it by its label, not its name.
    jobs = [d for (k, _), d in docs.items() if k == "Job" and d["metadata"].get("labels", {}).get("app.kubernetes.io/name") == "kini-finish"]
    assert len(jobs) == 1, f"expected one kini-finish Job, found {[d['metadata']['name'] for d in jobs]}"
    job = jobs[0]
    spec = job["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == "sovereign-worker"
    assert spec["containers"][0]["image"].startswith("ghcr.io/chidionyema/sovereign-worker:"), spec["containers"][0]["image"]
    assert spec["containers"][0]["command"][-4:] == ["kini", "finish", "--wait", "--json"]
    cj = docs[("CronJob", "kini-state")]
    ps = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert ps["serviceAccountName"] == "sovereign-worker"
    assert ps["initContainers"][0]["image"].startswith("ghcr.io/chidionyema/sovereign-worker:")
    assert "kini receipt" in ps["initContainers"][0]["args"][0]
    assert "state/kini" in ps["containers"][0]["args"][0]


@then("oke-check.yml has job kini-state and drills/catalogue.yaml has row kini-finish")
def _wiring():
    oke = yaml.safe_load((IDP / ".github/workflows/oke-check.yml").read_text())
    assert "kini-state" in oke["jobs"], list(oke["jobs"])
    assert "bin/idp-kini-state" in json.dumps(oke["jobs"]["kini-state"])
    cat = yaml.safe_load((IDP / "drills/catalogue.yaml").read_text())
    rows = {r["name"]: r for r in cat["drills"]}
    assert rows["kini-finish"]["job"] == "kini-state" and rows["kini-finish"]["workflow"] == "oke-check.yml"


@then("`kini receipt` is a CLI subcommand")
def _cli():
    env = {**os.environ, "PYTHONPATH": str(IDP)}
    p = subprocess.run([sys.executable, "-m", "sovereign.cli", "kini", "receipt", "--help"], capture_output=True, text=True, env=env, cwd=IDP)
    assert p.returncode == 0 and "receipt" in p.stdout, p.stdout + p.stderr
