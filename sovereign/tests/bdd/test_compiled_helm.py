"""Compile the estate's Helm releases and assert the numbers the estate believes it set.

Binds `features/gates/compiled-helm.feature`.

WHY THIS EXISTS, in one paragraph. On 2026-09-12 a five-day-old fix (#2429) had never been applied
to the cluster. The pull request changed a COMMENT saying "cpu 500m" and left the VALUE at 1000m.
CI was green, because the YAML was valid. Reviewers read the comment and believed it. Nothing in
the estate could tell the difference, because `kustomize build` emits the HelmRelease OBJECT and
never the Deployments Helm creates from it -- so the only place the real number existed was the
running cluster, and nothing compared it to git.

`bin/idp-compile-helm` closes that: it renders every HelmRelease from git alone,
`helm template <chart> --version <pinned> -f <the values this tree holds>`, and writes one document.
The numbers below are read from that document, not from the files anyone edited.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/compiled-helm.feature")

ROOT = Path(__file__).resolve().parents[3]
COMPILER = ROOT / "bin" / "idp-compile-helm"


@pytest.fixture(scope="module")
def compiled() -> dict:
    """The compiled estate, produced once for the whole file.

    Rendering 31 charts takes minutes; doing it per scenario would make the gate too slow to run,
    and a gate that is too slow to run is a gate that gets skipped.
    """
    if not COMPILER.is_file():
        pytest.fail(f"{COMPILER} does not exist")
    out = ROOT / ".estate" / "compiled-helm.json"
    proc = subprocess.run(  # noqa: S603
        [str(COMPILER), "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=1800,
    )
    assert out.is_file(), (
        f"the compiler wrote no document:\n{proc.stdout}\n{proc.stderr}"
    )
    return json.loads(out.read_text())


@pytest.fixture()
def context() -> dict:
    return {}


def _deployments(compiled: dict):
    for r in compiled["releases"]:
        for o in r["objects"]:
            if o["kind"] in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
                for c in o["resources"]:
                    yield r["namespace"], o["name"], c


@given("the estate is compiled from git")
def compiled_from_git(context, compiled):
    context["compiled"] = compiled


@given("the estate has Helm releases")
def has_releases(context):
    assert context["compiled"]["summary"]["total"] > 0, (
        "no HelmRelease was found; the estate has 31, so the compiler is not looking where they are"
    )


@when(parsers.parse("I read the rendered {workload} in {namespace}"))
def read_workload(context, workload, namespace):
    found = [
        c
        for ns, name, c in _deployments(context["compiled"])
        if name == workload and ns == namespace
    ]
    assert found, (
        f"{namespace}/{workload} does not appear in the compiled estate. If the chart renders it, "
        "the compiler is not seeing it; if it does not, nothing declares it."
    )
    context["container"] = found[0]


@when("I compile every release")
def compile_every(context):
    summary = context["compiled"]["summary"]
    context["summary"] = summary


@then(parsers.parse("its rendered cpu request is {want}"))
def rendered_request_is(context, want):
    got = (context["container"]["requests"] or {}).get("cpu")
    assert got == want, (
        f"the compiled chart sets cpu={got!r}, not {want!r}. This is what the cluster will run; "
        "a comment or a patch that says otherwise has not changed it."
    )


@then("the rendered request equals the rendered limit")
def request_equals_limit(context):
    """Guaranteed QoS is what makes the kubelet evict this workload last, and
    require-priority-class's radio-room-set-is-guaranteed rule (crew#59 CP9, Enforce) refuses a
    container whose cpu request differs from its limit."""
    c = context["container"]
    req = (c["requests"] or {}).get("cpu")
    lim = (c["limits"] or {}).get("cpu")
    assert req == lim, f"{c['name']}: request {req} != limit {lim}"


@then(parsers.parse("every release renders, {count:d} of them"))
def every_release_renders(context, count):
    """A chart that cannot be rendered is the blind spot this gate exists to close.

    A release rendered from a stale cache, or skipped because its repository could not be reached,
    must never be counted as agreeing with git.
    """
    s = context["summary"]
    assert s["rendered"] == s["total"], (
        f"{s['failed']} of {s['total']} releases did not render, so their numbers are unknown: "
        + "; ".join(
            f"{r['namespace']}/{r['name']}: {r['error']}"
            for r in context["compiled"]["releases"]
            if r["error"]
        )
    )
    assert s["total"] >= count, (
        f"only {s['total']} releases found; the estate has at least {count}"
    )
