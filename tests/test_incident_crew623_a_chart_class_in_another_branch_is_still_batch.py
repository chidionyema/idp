"""Incident 2026-08-29 (crew#623, LAW 8): the money layer's event bus was refused by the capacity
budget -- `platform/ requests 5.10 cores on paper (budget 5.0)`, with
`platform/event-bus/nats.yaml:HelmRelease/nats 0.10` named among the fattest. The NATS pod runs
under PriorityClass platform-batch, and platform-batch requests are deliberately kept out of that
paper total: they are seated by preempting the balloon, whose request the sum already counts.

The guard could not see it. It carried `in_batch` down the document from whichever node held
`priorityClassName`, which is right for a raw Deployment -- one pod spec holds the class and the
containers -- and wrong for a HelmRelease, where the chart decides where each field goes. The NATS
chart takes the class at `podTemplate.merge.spec.priorityClassName` and the requests at
`container.merge.resources`: two sibling branches, neither beneath the other. So the guard graded
the shape of the YAML tree rather than the pod, charged a batch pod to standing capacity, and would
have refused any future chart that puts its two fields anywhere but nested.

The fix reads the class per document for a HelmRelease. The fence must not become the hole, so a
release that names more than one class is not waved through: the tests below pin both directions.
"""

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mod():
    path = ROOT / "tests" / "test_incident_crew584_capacity_requests_need_proof.py"
    spec = importlib.util.spec_from_file_location("capacity_guard", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_a_class_in_a_sibling_branch_is_still_read():
    """The exact shape the NATS chart uses, and the one the old guard could not see."""
    doc = {
        "kind": "HelmRelease",
        "spec": {
            "values": {
                "podTemplate": {
                    "merge": {"spec": {"priorityClassName": "platform-batch"}}
                },
                "container": {"merge": {"resources": {"requests": {"cpu": "100m"}}}},
            }
        },
    }
    assert _mod()._sole_class(doc) == {"platform-batch"}


@pytest.mark.parametrize(
    "classes,expected",
    [
        (["platform-batch"], {"platform-batch"}),
        (
            ["platform-batch", "infrastructure-critical"],
            {"platform-batch", "infrastructure-critical"},
        ),
        ([], set()),
    ],
)
def test_every_class_in_the_document_is_returned_not_the_first(classes, expected):
    """A release with a batch worker and a critical one must not be waved through as batch: the
    caller only trusts the answer when it is exactly {platform-batch}."""
    doc = {
        "kind": "HelmRelease",
        "spec": {
            "values": {f"c{i}": {"priorityClassName": c} for i, c in enumerate(classes)}
        },
    }
    assert _mod()._sole_class(doc) == expected


def test_an_empty_class_name_is_not_a_class():
    """`priorityClassName: ""` is what a chart's default values carry when the field is unset --
    reading it as a class would make every such chart look like it had named one."""
    assert _mod()._sole_class({"a": {"priorityClassName": ""}}) == set()


def test_the_event_bus_is_counted_as_batch_and_not_as_standing_capacity():
    """The live tree, not a fixture: the thing the incident was about."""
    m = _mod()
    src = "platform/event-bus/nats.yaml"
    assert any(src in row[0] for row in m._requests(batch=True)), (
        "the NATS request is not in the batch list; the class is no longer being read"
    )
    assert not any(src in row[0] for row in m._requests()), (
        "the NATS request is back in the standing-capacity total, which is what broke the budget"
    )


def test_the_budget_still_holds_with_the_money_layer_in_the_tree():
    m = _mod()
    total = sum(r[2] for r in m._requests())
    assert total <= m.CPU_BUDGET_CORES, (
        f"{total:.2f} cores on paper, budget {m.CPU_BUDGET_CORES}"
    )
