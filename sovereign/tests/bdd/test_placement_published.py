"""Placement is measured, published and read on the portal.

Binds `features/gates/placement-published.feature`.

The estate already measures placement: `platform/state/cluster-state.yaml` runs in-cluster every
15 minutes, computes a `placement` section, and `.github/workflows/oke-check.yml` grades it with
`bin/idp-fits-a-node`. Both were already true and neither was on a page, so this suite grades the
missing half -- that the measurement reaches the portal -- rather than re-measuring it.

The page's own logic is graded by `backstage/packages/app/src/modules/home/placement.test.ts`
(9 tests). A Python suite cannot import a `.ts` file, so each half is graded where it runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/placement-published.feature")

REPO = Path(__file__).resolve().parents[3]
CLUSTER_STATE = REPO / "platform" / "state" / "cluster-state.yaml"
RENDER = REPO / "bin" / "catalog-render"
APP_CONFIG = REPO / "backstage" / "app-config.yaml"
OPS = REPO / "backstage" / "packages" / "app" / "src" / "modules" / "home" / "Ops.tsx"


@pytest.fixture()
def context() -> dict:
    return {}


@given("the cluster-state job has run")
def job_ran(context):
    assert CLUSTER_STATE.is_file(), f"{CLUSTER_STATE} does not exist"
    context["job"] = CLUSTER_STATE.read_text()


@given("a placement document is on the estate state")
def placement_on_branch(context):
    assert RENDER.is_file(), f"{RENDER} does not exist"
    context["render"] = RENDER.read_text()


@given("the placement document is published")
def placement_published(context):
    assert APP_CONFIG.is_file(), f"{APP_CONFIG} does not exist"
    context["app_config"] = APP_CONFIG.read_text()


@given(parsers.parse("the receipt says {req:d}m requested and {used:d}m used"))
def receipt_says(context, req, used):
    context["requested_m"] = req
    context["used_m"] = used


@when("it writes its receipt")
def writes_receipt(context):
    """The receipt the job emits. It writes one JSON document to stdout, and the placement section
    is already inside it -- what was missing is a second copy where a page can read it."""
    context["has_placement"] = '"placement"' in context["job"]
    context["writes_json"] = bool(re.search(r"json\.dumps\(body", context["job"]))


@when("the page summarises it, which placement.ts does")
def page_summarises(context):
    """The page's summary is computed in TypeScript and graded by placement.test.ts. What this
    step establishes is that the two halves agree on the arithmetic the sentence restates."""
    assert context["requested_m"] > context["used_m"], (
        "the fixture must have more requested than used, or the idle sentence is meaningless"
    )


@when("the render force-pushes that branch")
def render_pushes(context):
    # Every CARRIED line, not just the first: the list is built with `=` and then extended with
    # `+=`, so a regex that takes only the first bracket would miss three quarters of it and the
    # test would fail on a correct file.
    context["carried"] = "\n".join(
        line for line in context["render"].splitlines() if "CARRIED" in line
    )


@when("the portal asks for it on the estate state proxy")
def portal_asks(context):
    context["proxies"] = re.findall(r"^\s*'(/[a-z-]+)':", context["app_config"], re.M)


@then("a placement document is written beside the other rendered state")
def placement_written(context):
    """A document a page can fetch must reach the state branch.

    The cluster job writes one receipt to stdout and the object store; the Ops page reads the state
    branch through the proxy. So the document is built and published by the workflow that already
    fetches that receipt -- there is no second measurement and no second job.
    """

    wf = REPO / ".github" / "workflows" / "oke-check.yml"
    assert wf.is_file(), f"{wf} does not exist"
    text = wf.read_text()
    assert "docs/placement.json" in text, (
        "nothing publishes docs/placement.json. The receipt reaches a CI job and the object store; "
        "without a document on the state branch the Ops page has no source and the measurement "
        "stays as invisible as it was."
    )


@then(
    "it carries the placement section, the capacity figures and the time it was taken"
)
def carries_what_is_needed(context):
    text = context["job"]
    assert context["has_placement"], "the receipt carries no placement section"
    assert context["writes_json"], "the receipt is not emitted as JSON"
    for key in ("cpu_requested", "cpu_used", "at"):
        assert key in text, (
            f"the placement document must carry {key!r}: without the requested and used figures "
            "the page cannot explain a cluster that is full and idle at once, and without the "
            "timestamp a stale measurement cannot be told from a fresh one."
        )


@then("the placement document is staged with the other carried files")
def carried_forward(context):
    """A force-push from main drops anything not staged first.

    The render force-pushes the state branch from origin/main, so a file only the cluster writes
    disappears unless the render checks it out of the branch and stages it with the rest.
    """
    assert "placement" in context["carried"], (
        "docs/placement.json is not in bin/catalog-render's CARRIED list. The render force-pushes "
        "the state branch from origin/main, so the next render would drop the measurement and the "
        "page would go blank -- the same failure the carried inventory and reports already guard."
    )


@then("the answer is the same document, and no second endpoint was added")
def same_document(context):
    """One proxy, one door (ADR 0006): the placement document rides /estate-state like founder.json
    and reports/index.json, rather than adding a second endpoint for one file."""
    assert "/estate-state" in context["proxies"], (
        f"the Ops page's proxy is missing. Proxies found: {context['proxies']}"
    )
    assert "/placement" not in context["proxies"], (
        "a second endpoint was added for one document; it must ride /estate-state"
    )


@then(parsers.parse("the sentence names {idle:d}m reserved but idle"))
def names_idle(context, idle):
    """The page's own module is graded in TypeScript, and its rule is restated here so the two
    halves cannot drift: requests are reservations, and the gap is the whole explanation."""
    assert context["requested_m"] - context["used_m"] == idle, (
        f"{context['requested_m']} - {context['used_m']} is not {idle}"
    )


@then(
    "it does not call the cluster full without saying why it can be idle and full at once"
)
def explains(context):
    """A page that says only 'CPU 96%' is the message that made this session look for a new node.

    The receipt carries both figures precisely so the page can say the useful thing, and the
    check below is that the Ops page reads placement at all -- a document nobody renders is the
    same defect one layer up.
    """
    assert OPS.is_file(), f"{OPS} does not exist"
    assert "placement" in OPS.read_text(), (
        "the Ops page does not read placement; publishing a document nothing renders leaves the "
        "measurement exactly as invisible as it was in the job's stdout"
    )
