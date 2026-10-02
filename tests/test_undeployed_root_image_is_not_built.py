"""The repo-root image (ghcr.io/chidionyema/idp) is deployed nowhere, so CI never builds or publishes it."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bin_dockerfiles_does_not_list_the_root_image():
    out = subprocess.run(
        ["bin/dockerfiles"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    names = [line.split()[0] for line in out.splitlines() if line.strip()]
    assert names and "idp" not in names


def test_factory_ci_has_no_publish_job():
    assert "publish:" not in (ROOT / ".github/workflows/factory-ci.yml").read_text()
