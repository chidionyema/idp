"""A job that trades the GitHub OIDC token for an OCI session must be allowed to mint one.

Commit 824ecee5 (2026-11-10) gave the scheduled homes drill the OCI preamble without
`id-token: write`. The action then fails with "Unable to get ACTIONS_ID_TOKEN_REQUEST_URL"
before a single home is probed, so the drill that opens and closes the critical-service
incidents measured nothing from 2026-11-10 02:43Z on. One job of thirty-four had the defect;
this refuses the next one in any workflow, not just that file.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = "oci-token-exchange-action"


def _oidc_jobs():
    for path in sorted((ROOT / ".github/workflows").glob("*.y*ml")):
        doc = yaml.safe_load(path.read_text())
        top = doc.get("permissions") or {}
        for name, job in (doc.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if any(ACTION in str(step.get("uses", "")) for step in steps):
                yield path.name, name, job.get("permissions", top)


def test_the_sweep_actually_finds_the_oidc_jobs():
    """A gate that inspects nothing cannot fail: the drill and the reference must both be seen."""
    seen = {(wf, job) for wf, job, _ in _oidc_jobs()}
    assert ("estate-homes-drill.yml", "drill") in seen, sorted(seen)
    assert ("vault-reads.yml", "audit") in seen, sorted(seen)


def test_every_job_that_exchanges_the_oidc_token_may_mint_it():
    missing = [
        f"{wf}:{job}"
        for wf, job, perms in _oidc_jobs()
        if not (
            perms == "write-all"
            or (isinstance(perms, dict) and perms.get("id-token") == "write")
        )
    ]
    assert not missing, f"jobs that use {ACTION} without id-token: write: {missing}"
