"""Incident 2026-08-27/28 (crew#267, crew#503, crew#554): every oke-check apply's installation step died on
`gh: A JSON web token could not be decoded (HTTP 401)` (runs 33120447702, 33124277054). The JWT was sound:
run 33098034984 measured the same token answering 200 under `Authorization: Bearer` and 401 under gh's
`Authorization: token`. With no installation id in the vault, ExternalSecret flux-system/github-app never
rendered, Kustomization alerts-github never became Ready, Kustomization drills (the drill-dispatcher
CronJob, crew#554 CP3) never reconciled, and no App-dispatched drill ran. The fix lived in idp#441 behind
an unrelated red row; this file carries it on its own."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "bin" / "idp-github-app"


def test_the_script_still_parses() -> None:
    r = subprocess.run(["bash", "-n", str(APP)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
