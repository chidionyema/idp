"""A Gateway API backendRef may name a router object instead of a workload.

`otto-gateway/telegram-mirror.yaml` puts a `traefik.io/TraefikService` behind the Telegram
route so otto keeps answering Telegram while the JIT broker gets a fire-and-forget copy. The
availability gate walks backendRefs looking for a Deployment, found none with that name -- there
can never be one -- and turned main red with `BLIND ... no kustomization renders a Deployment for
it`, while both real backends were already graded `ok`. These pin the resolution so the next
router object does not repeat it.
"""

import importlib.util
import os

_SPEC = importlib.util.spec_from_loader(
    "availability_gate",
    importlib.machinery.SourceFileLoader(
        "availability_gate",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "bin",
            "idp-availability-gate",
        ),
    ),
)
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def _ts(name, ns, spec):
    return {
        "kind": "TraefikService",
        "metadata": {"name": name, "namespace": ns},
        "spec": spec,
    }


def _index(*objs):
    return {(o["metadata"]["namespace"], o["metadata"]["name"]): o for o in objs}


def test_a_plain_service_reference_is_returned_untouched():
    assert gate.traefik_backends("otto-gateway", "otto-gateway", {}) == [
        ("otto-gateway", "otto-gateway")
    ]


def test_a_mirror_resolves_to_the_service_that_answers_the_caller():
    """Traefik discards the mirrored response, so the mirror cannot change what the caller gets.
    Grading it here would fail the surface for something the surface does not depend on."""
    tsvcs = _index(
        _ts(
            "otto-and-the-jit-broker",
            "otto-gateway",
            {
                "mirroring": {
                    "name": "otto-gateway",
                    "port": 8080,
                    "mirrors": [
                        {"name": "jit-broker", "namespace": "jit", "port": 8080}
                    ],
                }
            },
        )
    )
    assert gate.traefik_backends("otto-gateway", "otto-and-the-jit-broker", tsvcs) == [
        ("otto-gateway", "otto-gateway")
    ]


def test_a_weighted_split_resolves_to_every_service_that_carries_traffic():
    """Unlike a mirror, every leg of a weighted split answers real callers."""
    tsvcs = _index(
        _ts(
            "blue-and-green",
            "edge",
            {
                "weighted": {
                    "services": [
                        {"name": "blue", "port": 80},
                        {"name": "green", "namespace": "staging", "port": 80},
                    ]
                }
            },
        )
    )
    assert gate.traefik_backends("edge", "blue-and-green", tsvcs) == [
        ("edge", "blue"),
        ("staging", "green"),
    ]


def test_a_router_naming_another_router_is_followed_to_the_workload():
    tsvcs = _index(
        _ts("outer", "edge", {"mirroring": {"name": "inner", "port": 80}}),
        _ts(
            "inner", "edge", {"weighted": {"services": [{"name": "real", "port": 80}]}}
        ),
    )
    assert gate.traefik_backends("edge", "outer", tsvcs) == [("edge", "real")]


def test_a_router_that_names_itself_ends_rather_than_hangs():
    tsvcs = _index(
        _ts("ouroboros", "edge", {"mirroring": {"name": "ouroboros", "port": 80}})
    )
    assert gate.traefik_backends("edge", "ouroboros", tsvcs) == []
