"""Incident (crew#458 row 3, 2026-08-27): estate-mcp could not leave the colima VM because
catalog/estate.db was produced only by bin/db-gen on the founder Mac and mounted from the checkout.
bin/idp-estate-db-push builds the database from the inventory the cloud render already holds and
ships it, with the two other read-only inputs the Mac compose mounted (catalog-info.yaml, crew
STATE.md), as one OCI artifact via `flux push artifact`; estate-mcp's init container pulls it.

Rule: --dry-run builds the artifact directory from the three inputs and pushes nothing; a missing
input is BLIND (exit 2), never an artifact with a hole in it.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-estate-db-push"
SU = shutil.which("sqlite-utils") or str(ROOT / ".venv" / "bin" / "sqlite-utils")


def _inputs(tmp_path, rows=3):
    inv = tmp_path / "inventory.json"
    inv.write_text(json.dumps({"at": "2026-08-27T13:01:19Z", "findings": [],
                               "rows": [{"id": f"repo:r{i}", "kind": "repo", "path": f"/x/r{i}", "root": "/x"} for i in range(rows)]}))
    cat = tmp_path / "catalog-info.yaml"
    cat.write_text("# inventory taken: 2026-08-27T13:01:19Z\napiVersion: backstage.io/v1alpha1\nkind: Component\n")
    state = tmp_path / "STATE.md"
    state.write_text("# STATE\n")
    return {"INV": str(inv), "CATALOG": str(cat), "STATE_MD": str(state), "SU": SU}


def _run(env, *args):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, check=False,
                          env={**os.environ, **env})


@pytest.mark.skipif(not (os.path.exists(SU) and shutil.which("flux") and shutil.which("jq")),
                    reason="needs sqlite-utils, flux and jq")
def test_dry_run_builds_the_three_inputs_and_pushes_nothing(tmp_path):
    out = _run(_inputs(tmp_path), "--dry-run")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "dry-run estate-db: 3 assets, would push oci://ghcr.io/chidionyema/idp/estate-db:latest" in out.stdout
    for name in ("estate.db", "catalog-info.yaml", "STATE.md"):
        assert name in out.stdout, name


@pytest.mark.skipif(not (shutil.which("flux") and shutil.which("jq")), reason="needs flux and jq")
def test_a_missing_input_is_blind_not_a_partial_artifact(tmp_path):
    env = _inputs(tmp_path)
    os.remove(env["STATE_MD"])
    out = _run(env, "--dry-run")
    assert out.returncode == 2 and "BLIND" in out.stdout and "STATE.md" in out.stdout, out.stdout + out.stderr
