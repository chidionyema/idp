"""The compiled estate is published and read on the portal.

Binds `features/gates/compiled-helm-published.feature`.

`bin/idp-compile-helm` renders every HelmRelease from git and `test_compiled_helm.py` grades the
numbers it produces. This file grades the half that makes it worth having: that the document is
produced on every pull request, reaches the state branch the portal reads, and is rendered by a
page -- because a measurement nobody reads is how a five-day-old fix stays invisible.

The page's own logic is graded by `backstage/packages/app/src/modules/home/compiled.test.ts`; a
Python suite cannot import a `.ts` file, so each half is graded where it runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/compiled-helm-published.feature")

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / ".github" / "workflows" / "ci.yml"
RENDER = ROOT / "bin" / "catalog-render"
APP_CONFIG = ROOT / "backstage" / "app-config.yaml"
OPS = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home" / "Ops.tsx"


@pytest.fixture()
def context() -> dict:
    return {}


@given("the estate's CI workflow")
def ci_workflow(context):
    assert CI.is_file(), f"{CI} does not exist"
    context["ci"] = CI.read_text()


@given("the compiled document is written by CI")
def written_by_ci(context):
    assert RENDER.is_file(), f"{RENDER} does not exist"
    context["render"] = RENDER.read_text()


@given("the compiled document names a workload and its rendered requests")
def document_shape(context):
    """The document's contract: a release record carries the objects it rendered, and each object
    carries the container resources the chart decided. Without those fields a page cannot show a
    disagreement, which is the only thing this document is for."""
    compiler = ROOT / "bin" / "idp-compile-helm"
    assert compiler.is_file(), f"{compiler} does not exist"
    text = compiler.read_text()
    for field in ('"requests"', '"limits"', '"resources"'):
        assert field in text, (
            f"the compiled document does not carry {field}; a page cannot show the rendered number "
            "without it, and the rendered number is the whole point"
        )


@given("the compiled document is published")
def document_published(context):
    """The document reaches the branch the portal reads, which is what makes it visible at all."""
    assert APP_CONFIG.is_file(), f"{APP_CONFIG} does not exist"
    context["app_config"] = APP_CONFIG.read_text()


@when("a pull request is opened")
def pr_opened(context):
    context["runs_compiler"] = "idp-compile-helm" in context["ci"]


@when("the render force-pushes the estate state")
def render_pushes(context):
    context["carried"] = "\n".join(
        line for line in context["render"].splitlines() if "CARRIED" in line
    )


@when("the portal shows it")
def portal_shows(context):
    assert APP_CONFIG.is_file(), f"{APP_CONFIG} does not exist"
    context["app_config"] = APP_CONFIG.read_text()


@then("the workflow runs bin/idp-compile-helm")
def runs_compiler(context):
    assert context["runs_compiler"], (
        "ci.yml does not run bin/idp-compile-helm. The compiler existing is not enough: a gate that "
        "runs by hand is the manual reading this was built to replace."
    )


@then("a release that does not render fails the run")
def unrendered_fails(context):
    """The compiler exits 2 when it cannot render, and CI must treat that as a failure.

    Eleven of the estate's 33 charts failed to render when this was written, and the first version
    of the compiler exited 0 anyway -- a gate that reports success while blind is worse than none.
    """
    ci = context["ci"]
    idx = ci.find("idp-compile-helm")
    assert idx >= 0, "ci.yml does not run the compiler"
    tail = ci[idx : idx + 2000]
    assert "exit 1" in tail, (
        "the CI step runs the compiler and does not fail on its non-zero exit; an unrendered chart "
        "would pass as an empty estate"
    )


@then("the compiled document is carried with the other rendered state")
def carried(context):
    assert "compiled-helm" in context["carried"], (
        "docs/compiled-helm.json is not in bin/catalog-render's CARRIED list. That render "
        "force-pushes the state branch from origin/main, so the document CI writes would be dropped "
        "and the page would have nothing to read."
    )


@then("the portal reads it through the proxy it already has")
def portal_reads(context):
    assert "/estate-state" in context["app_config"], (
        "the /estate-state proxy is missing; the compiled document rides it like founder.json"
    )
    assert "/compiled" not in context["app_config"], (
        "a second endpoint was added for one document; it must ride /estate-state (ADR 0006)"
    )


@then("a workload whose comment and value disagree appears with the rendered value")
def disagreement_visible(context):
    assert OPS.is_file(), f"{OPS} does not exist"
    assert "compiled" in OPS.read_text(), (
        "the Ops page does not read the compiled estate. Publishing a document nothing renders "
        "leaves the disagreement exactly as invisible as it was in a CI job's log -- which is the "
        "failure this feature exists to close."
    )


@then("the number shown is the one the chart renders, never the one the file claims")
def rendered_not_claimed(context):
    """The page must read the compiled document, not the values files.

    A page that read `platform/observability/langfuse-values.yaml` would have shown 500m on
    2026-09-12 because the COMMENT said so, while the value and the cluster said 1000m. Reading the
    compiled document is what makes the displayed number the true one.
    """
    src = OPS.read_text()
    assert "langfuse-values" not in src, (
        "the Ops page reads a values file directly; it must read the compiled document instead, or "
        "it will show the claim rather than the rendered truth"
    )
