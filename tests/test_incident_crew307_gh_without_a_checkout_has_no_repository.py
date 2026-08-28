"""crew#307, 2026-08-28. An alarm that detected the fire and filed nothing.

`gh` finds the repository from the git remote of the working directory. A job with no
`actions/checkout` has no working directory to read, so every `gh` call in it exits
`fatal: not a git repository (or any of the parent directories): .git`. flux-events run
**33163766050** caught `HelmRelease/robusta/robusta status: 'Failed'` at 10:32:53Z, tried to open
the P0, died there, and opened nothing.

What made it invisible is the shape, not the typo: the step ends in `exit 1`, so the run went red
either way. From the outside -- from the checks list, from a notification -- a red run is exactly
what a working alarm looks like. The founder asked "and then what happens next"; the answer was
`fatal: not a git repository`, and no board row, for as long as anyone cared to look.

The rule: a job that calls `gh` and never checks the repository out must name the repository
itself, via `GH_REPO` in the environment or `--repo` on the call. Every workflow is walked, so a
new job cannot reintroduce it.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
GH_CALL = re.compile(r"(?<![\w/-])gh\s+(?!auth\b)[a-z-]+", re.M)


def _jobs(wf):
    # `on:` parses to True in YAML 1.1; harmless here, we only read `jobs`.
    doc = yaml.safe_load(wf.read_text()) or {}
    return (doc.get("jobs") or {}).items()


def _has_checkout(job):
    return any("actions/checkout" in str(s.get("uses", "")) for s in job.get("steps") or [])


def _env_of(job, step):
    return {**(job.get("env") or {}), **(step.get("env") or {})}


def test_there_are_workflows_to_grade():
    """A sweep that finds no files is not a sweep (crew#539: BLIND is never a pass)."""
    assert WORKFLOWS, "no workflow files found to grade"


def test_every_gh_call_in_a_checkoutless_job_names_its_repository():
    offenders = []
    for wf in WORKFLOWS:
        for job_name, job in _jobs(wf):
            if not isinstance(job, dict) or _has_checkout(job):
                continue
            for step in job.get("steps") or []:
                run = step.get("run") or ""
                calls = [c for c in GH_CALL.findall(run) if "--repo" not in run.split(c, 1)[-1].split("\n")[0]]
                if not calls:
                    continue
                if "GH_REPO" in _env_of(job, step):
                    continue
                offenders.append(
                    f"{wf.relative_to(ROOT)} job {job_name!r} step "
                    f"{step.get('name', '(unnamed)')!r}: {', '.join(sorted(set(calls)))}")
    assert not offenders, (
        "`gh` reads the repository from the checkout's git remote. These jobs never check out, so "
        "every call exits `fatal: not a git repository` -- and a step that ends in `exit 1` still "
        "paints the run red, so it looks like it worked (crew#307, run 33163766050). Add\n"
        "    GH_REPO: ${{ github.repository }}\n"
        "to the step or job env, or pass --repo on the call.\n  " + "\n  ".join(offenders))
