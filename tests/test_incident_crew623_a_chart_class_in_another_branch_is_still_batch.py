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


def test_a_class_the_release_patches_in_is_read_as_the_class_the_pod_runs_under():
    """The Lago chart carries no `priorityClassName` field, so the class arrives by postRenderers.

    A walk over the release's values finds nothing -- the class is inside a YAML string -- and the
    guard charged eight continuously running pods to standing capacity while the scheduler ranked
    them as batch. Grading the shape of the file instead of the pod, again, one branch along from
    the sibling-branch defect above.

    The target here reaches every kind in the namespace. It used to read `{kind: Deployment}`, and
    that was the same defect wearing the fence's own uniform: a bare kind names no single object,
    so it counted as covering the document while reaching no StatefulSet or CronJob the chart also
    ships. Closed 2026-08-29 in _patched_classes, and the case below now holds it shut.
    """
    release = {
        "kind": "HelmRelease",
        "spec": {
            "values": {"api": {"resources": {"requests": {"cpu": "200m"}}}},
            "postRenderers": [
                {
                    "kustomize": {
                        "patches": [
                            {
                                "target": {"namespace": "lago"},
                                "patch": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: any\nspec:\n  template:\n    spec:\n      priorityClassName: platform-batch\n",
                            }
                        ]
                    }
                }
            ],
        },
    }
    assert _mod()._patched_classes(release) == {"platform-batch"}


@pytest.mark.parametrize(
    "target",
    [
        {"kind": "Deployment", "name": "lago-api"},
        {"kind": "Deployment", "labelSelector": "app=lago-api"},
        {"kind": "Deployment", "annotationSelector": "batch=yes"},
        # A bare kind is the same hole one step less obvious: it names no single object, but it
        # reaches no StatefulSet, DaemonSet or CronJob the chart ships alongside its Deployments.
        {"kind": "Deployment"},
    ],
)
def test_a_patch_that_reaches_only_some_pods_does_not_make_the_document_batch(target):
    """ "Some of the chart's pods" cannot make a whole document batch: the rest still stand.

    Without this the fence becomes the hole -- one narrowly targeted patch would excuse every
    request the chart declares.
    """
    release = {
        "kind": "HelmRelease",
        "spec": {
            "postRenderers": [
                {
                    "kustomize": {
                        "patches": [
                            {
                                "target": target,
                                "patch": "spec:\n  template:\n    spec:\n      priorityClassName: platform-batch\n",
                            }
                        ]
                    }
                }
            ]
        },
    }
    assert _mod()._patched_classes(release) == set()


def test_a_patch_naming_another_class_is_not_batch():
    """The union with the values' own classes must still be exactly {platform-batch} to count."""
    release = {
        "kind": "HelmRelease",
        "spec": {
            "postRenderers": [
                {
                    "kustomize": {
                        "patches": [
                            {
                                "target": {"namespace": "lago"},
                                "patch": "spec:\n  template:\n    spec:\n      priorityClassName: infrastructure-critical\n",
                            }
                        ]
                    }
                }
            ]
        },
    }
    assert _mod()._patched_classes(release) == {"infrastructure-critical"}


def test_a_release_with_no_post_renderers_is_unchanged():
    """Every other release in the tree must read exactly as it did before."""
    assert (
        _mod()._patched_classes({"kind": "HelmRelease", "spec": {"values": {}}})
        == set()
    )


def _not_standing(fragment):
    """Where the capacity guard puts this file's requests, and the proof it is out of the total.

    Rewritten 2026-08-29, same day, same defect class as the incident above. These two tests used to
    demand the rows appear in the BATCH bucket, which made the assertion a second copy of the
    priority-class reading rather than a check on the thing that matters. The thing that matters is
    that a suspended layer is not charged to standing capacity; how it is kept out is the guard's
    business, and it has since changed -- the same day -- to read `suspend: true` from
    clusters/oke/commerce.yaml, which is the fact about the world rather than a scheduling rank.
    So: never in standing, and in exactly one of the two exclusion buckets.
    """
    m = _mod()
    standing = [r for r in m._requests() if fragment in r[0]]
    batch = [r for r in m._requests(batch=True) if fragment in r[0]]
    off = [r for r in m._requests(off=True) if fragment in r[0]]
    assert standing == [], f"{fragment} is charged to standing capacity: {standing}"
    assert batch or off, f"{fragment} declares no CPU request the guard can see at all"
    assert not (batch and off), (
        f"{fragment} is excluded twice, so one exclusion is unread: {batch} {off}"
    )
    return batch, off
