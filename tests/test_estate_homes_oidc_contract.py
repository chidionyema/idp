"""Regression contract for scheduled OCI drill GitHub OIDC permissions.

Failure: 43181846037/job/131059462475, missing ACTIONS_ID_TOKEN_REQUEST_URL.
The token is scoped to the drill job, never the unrelated Chronos observer.
"""
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/estate-homes-drill.yml"


def _valid(text: str) -> bool:
    jobs = yaml.safe_load(text)["jobs"]
    drill = jobs["drill"].get("permissions", {})
    chronos = jobs["chronos"].get("permissions", {})
    return (
        drill.get("id-token") == "write"
        and drill.get("contents") == "read"
        and drill.get("issues") == "write"
        and "id-token" not in chronos
    )


def test_scheduled_oci_exchange_has_job_scoped_oidc_and_issue_permissions():
    assert _valid(WORKFLOW.read_text()), (
        "OCI exchange cannot obtain ACTIONS_ID_TOKEN_REQUEST_URL unless "
        "the drill job grants id-token: write; keep Chronos least-privileged"
    )


@pytest.mark.parametrize("bad", ["read", "none", "chronos"])
def test_oidc_permission_mutations_fail_closed(bad):
    source = WORKFLOW.read_text()
    assert _valid(source)
    if bad == "read":
        mutated = source.replace("      id-token: write", "      id-token: read", 1)
    elif bad == "none":
        mutated = "\n".join(line for line in source.splitlines() if not line.strip().startswith("id-token:")) + "\n"
    else:
        mutated = source.replace("      actions: read", "      id-token: write\n      actions: read", 1)
    assert mutated != source
    assert not _valid(mutated)
