"""One image failing to publish must never cancel another image's release.

Incident: 2026-09-27. build-multiarch runs 12962 and 12967 built voice-router for amd64 and arm64,
then backstage's merge row failed (no digests) and the matrix's default fail-fast cancelled
voice-router's `imagetools create` mid-step. No main-<run>-<sha> tag was ever pushed, so the
newsroom's Deployment (idp#4475) pointed at an image that does not exist.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "build-multiarch.yml"
)


def test_every_matrix_job_in_the_image_pipeline_lets_its_rows_finish():
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    matrixed = {n: j for n, j in jobs.items() if "matrix" in j.get("strategy", {})}
    assert {"build", "merge"} <= set(matrixed)
    for name, job in matrixed.items():
        assert job["strategy"].get("fail-fast") is False, name
