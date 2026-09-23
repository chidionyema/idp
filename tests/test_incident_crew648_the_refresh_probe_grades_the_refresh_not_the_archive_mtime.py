"""crew#648 incident, 2026-08-30 09:0xZ: the refresh sidecar pulled the estate-state artifact
green, yet its liveness and readiness probes (`find /data -name estate-state.json -mmin -30`)
failed for eleven minutes, the pod never turned Ready, the Deployment hit
ProgressDeadlineExceeded and Flux marked the mcp Kustomization Failed (oke-check run
33303322556). `flux pull artifact` extracts files with the archive's own mtime, and
`flux push artifact` writes a reproducible tar with a fixed mtime, so an mtime-based probe
can never pass on the extracted file. Guard: the loop touches the document after every
successful pull, so the mtime means "last successful refresh", which is what the probes grade.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform" / "mcp" / "estate-mcp.yaml"


def _sidecar() -> dict:
    for doc in yaml.safe_load_all(MANIFEST.read_text()):
        if (
            doc
            and doc.get("kind") == "Deployment"
            and doc["metadata"]["name"] == "estate-mcp"
        ):
            for c in doc["spec"]["template"]["spec"]["containers"]:
                if c["name"] == "refresh-estate-state":
                    return c
    raise AssertionError(
        "refresh-estate-state sidecar is not in the estate-mcp Deployment"
    )


def test_incident_crew648_a_successful_pull_touches_the_document_before_any_probe_reads_its_mtime():
    script = "\n".join(_sidecar()["args"])
    pull = script.index(
        "flux pull artifact oci://ghcr.io/chidionyema/idp/estate-state:latest"
    )
    touch = script.index("touch /data/estate-state.json")
    assert pull < touch, (
        "the touch must follow the pull, it is the receipt of a successful refresh"
    )
    assert "if flux pull artifact" in script, (
        "the touch is conditional on the pull succeeding, never unconditional"
    )


def test_incident_crew648_every_mtime_probe_on_the_sidecar_reads_the_file_the_loop_touches():
    c = _sidecar()
    for probe in ("livenessProbe", "readinessProbe"):
        cmd = " ".join(c[probe]["exec"]["command"])
        assert "estate-state.json" in cmd and "-mmin" in cmd, (
            f"{probe} must grade the touched file's age"
        )
