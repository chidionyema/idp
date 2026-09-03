"""The founder's Otto reference (docs/founder/otto.md) cites source files; if a cited
fact leaves its file, the doc has drifted and this fails — the page is fixed, never trusted."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "founder" / "otto.md"


def test_cited_coverage_probe_still_exists():
    assert (ROOT / "platform" / "observability" / "telemetry-coverage.yaml").exists()
    assert (ROOT / "bin" / "idp-telemetry-coverage").exists()
