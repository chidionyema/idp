"""The founder's Otto reference (docs/founder/otto.md) cites source files; if a cited
fact leaves its file, the doc has drifted and this fails — the page is fixed, never trusted."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "founder" / "otto.md"


def test_doc_exists_and_names_the_three_subjects():
    text = DOC.read_text()
    for needle in ("Otto", "Backstage", "Telegram pin", "crew/issues/761"):
        assert needle in text, f"otto.md no longer covers: {needle}"


def test_cited_gateway_facts_still_hold():
    gateway = (ROOT / "platform" / "hermes-agent" / "gateway.yaml").read_text()
    assert "ghcr.io/chidionyema/hermes-agent" in gateway
    assert "langfuse-web.observability.svc:3000" in gateway
    assert "founder-telegram" in gateway


def test_cited_backstage_door_still_holds():
    zone = (ROOT / "clusters" / "oke" / "estate-config.yaml").read_text()
    assert "ESTATE_ZONE: mumchimp.com" in zone
    assert "catalogue.mumchimp.com" in DOC.read_text()


def test_cited_coverage_probe_still_exists():
    assert (ROOT / "platform" / "observability" / "telemetry-coverage.yaml").exists()
    assert (ROOT / "bin" / "idp-telemetry-coverage").exists()
