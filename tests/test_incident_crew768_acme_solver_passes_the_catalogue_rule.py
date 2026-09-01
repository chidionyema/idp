"""crew#768 (2026-09-01): the Telegram door served the Traefik placeholder certificate for
twelve hours. cert-manager mints a Service and an HTTPRoute per HTTP-01 challenge, both
labelled ``acme.cert-manager.io/http01-solver``; the Kyverno rule ``service-names-its-entity``
(Enforce since 2026-08-29) refused them because neither carries a catalogue label, so no edge
certificate could renew. Guard: the exception in ``platform/edge`` names that label for both
kinds, so the rule can never refuse a challenge again."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCEPTION = ROOT / "platform" / "edge" / "catalogue-entity-exception.yaml"
SOLVER_LABEL = "acme.cert-manager.io/http01-solver"


def _exception_entries():
    doc = yaml.safe_load(EXCEPTION.read_text())
    assert doc["kind"] == "PolicyException"
    assert doc["metadata"]["namespace"] == "kyverno", (
        "Kyverno honours exceptions from kyverno only"
    )
    names = {
        (e["policyName"], tuple(e["ruleNames"])) for e in doc["spec"]["exceptions"]
    }
    assert ("require-catalogue-entity", ("service-names-its-entity",)) in names
    return [entry["resources"] for entry in doc["spec"]["match"]["any"]]


def test_incident_crew768_acme_solver_service_and_httproute_are_excepted():
    covered = set()
    for res in _exception_entries():
        labels = (res.get("selector") or {}).get("matchLabels") or {}
        if labels.get(SOLVER_LABEL) == "true":
            covered.update(res["kinds"])
    assert {"Service", "HTTPRoute"} <= covered, (
        f"{EXCEPTION.relative_to(ROOT)} must except Service and HTTPRoute carrying "
        f"{SOLVER_LABEL}=true, else every HTTP-01 challenge is refused at admission"
    )


def test_incident_crew768_solver_exception_is_not_pinned_to_one_namespace():
    for res in _exception_entries():
        labels = (res.get("selector") or {}).get("matchLabels") or {}
        if labels.get(SOLVER_LABEL) == "true":
            assert "namespaces" not in res, "a Certificate can live in any namespace"
