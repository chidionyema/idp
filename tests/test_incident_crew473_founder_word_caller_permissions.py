"""Incident 2026-08-27 (crew#473): every `founder-word` run on main ended in startup_failure
(six runs 09:10Z-09:28Z, https://github.com/chidionyema/idp/actions/workflows/founder-word.yml).
GitHub refuses a caller that grants less than the reusable workflow it calls asks for:
operating-model-gate.yml asks `pull-requests: write` (it posts the deny lines as a comment);
founder-word.yml granted `pull-requests: read`. So a `DENY: <word>` from the founder never
re-judged anything, and nobody saw it because a startup failure has no job and no log line.

Rule: a workflow that `uses:` a local reusable workflow grants, at the top level and on the
calling job, at least every permission the reusable workflow declares. Rung 4, one test per bug.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
RANK = {"none": 0, "read": 1, "write": 2}


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text())


def _needs(reusable: dict) -> dict:
    need = dict(reusable.get("permissions") or {})
    for job in (reusable.get("jobs") or {}).values():
        for scope, level in (job.get("permissions") or {}).items():
            if RANK[level] > RANK.get(need.get(scope, "none"), 0):
                need[scope] = level
    return need


def test_every_local_caller_grants_what_the_reusable_gate_asks_for():
    need = _needs(_load("operating-model-gate.yml"))
    assert need.get("pull-requests") == "write", need
    short = []
    for path in sorted(WF.glob("*.yml")):
        wf = _load(path.name)
        for job_name, job in (wf.get("jobs") or {}).items():
            if job.get("uses") != "./.github/workflows/operating-model-gate.yml":
                continue
            top = wf.get("permissions") or {}
            grant = dict(top) if isinstance(top, dict) else {}
            if isinstance(job.get("permissions"), dict):
                grant = job["permissions"]
            for scope, level in need.items():
                if RANK.get(grant.get(scope, "none"), 0) < RANK[level]:
                    short.append(f"{path.name}:{job_name} grants {scope}={grant.get(scope, 'none')}, gate needs {level}")
    assert not short, short
