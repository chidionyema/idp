"""crew#280: ai.estate.sovereign-worker and ai.estate.cockpit were installed from
/tmp/claude-501/wt-idp-oke, a session worktree, so the jobs died with it (LAW 46).
The installer must refuse a temporary checkout and accept the permanent one.
Rung 4, incident test. No job is loaded: the allow case names a label that has no template.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[1] / "bin" / "idp-install-launchd"
pytestmark = pytest.mark.skipif(shutil.which("envsubst") is None, reason="envsubst missing")


def run(root: str):
    return subprocess.run([str(INSTALLER), "no-such-job"], env={**os.environ, "IDP_ROOT": root},
                          capture_output=True, text=True)


import tempfile

TEMP_ROOTS = [
    str(Path(tempfile.gettempdir()) / "claude-501" / "wt-idp-oke"),   # the real incident path shape
    str(Path("/private") / "tmp" / "x"),
    str(Path.home() / "idp" / ".wt-280-x"),                            # a session worktree under the checkout
]


@pytest.mark.parametrize("root", TEMP_ROOTS)
def test_incident_crew280_refuses_a_temporary_checkout(root):
    r = run(root)
    assert r.returncode == 2 and "refusing" in r.stdout


def test_incident_crew280_accepts_the_permanent_checkout():
    r = run(str(INSTALLER.parents[1]).replace("/.wt-280-launchd", ""))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "loaded" not in r.stdout  # filter matched no template, nothing was bootstrapped
