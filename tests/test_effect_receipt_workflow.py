"""Falsifier for .github/workflows/effect-receipt.yml (idp#8759, producer half).

The workflow is ONE issuer of a three-issuer proof, so these tests pin what it must
never do: certify from the Greenlane's own workflow, write the three-receipt comment,
or accept a source-plane (GitHub) target as production.
"""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WF = REPO / ".github" / "workflows" / "effect-receipt.yml"
SOURCE_HOSTS = (
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
    "gist.githubusercontent.com",
)


def _doc() -> dict:
    return yaml.safe_load(WF.read_text())


def _script() -> str:
    steps = _doc()["jobs"]["attest"]["steps"]
    return "\n".join(s.get("run", "") for s in steps)


def test_it_is_dispatch_only_so_no_push_can_sign() -> None:
    triggers = _doc().get(True) or _doc().get("on")
    assert set(triggers) == {"workflow_dispatch"}


def test_it_holds_the_oidc_token_permission_and_nothing_wider() -> None:
    perms = _doc()["permissions"]
    assert perms["id-token"] == "write"
    assert perms == {"contents": "read", "id-token": "write", "issues": "write"}


def test_it_signs_with_the_agreed_predicate_type_keylessly() -> None:
    script = _script()
    assert "cosign attest-blob" in script
    assert "--type https://meridianlabs.cloud/effect/v1" in script
    assert "--key" not in script


def test_it_refuses_every_source_plane_host_as_a_target() -> None:
    script = _script()
    for host in SOURCE_HOSTS:
        assert host in script
    assert "ERR_PROXY_GREEN_SUBSTITUTION" in script


def test_it_posts_a_part_never_the_three_receipt_comment() -> None:
    script = _script()
    assert "EPISTEMIC-EFFECT-PART-V1" in script
    assert "EPISTEMIC-EFFECT-V1\\n" not in script
    assert "receipts:[$b[0]]" in script


def test_it_is_not_the_greenlane_workflow() -> None:
    assert _doc()["name"] == "effect-receipt"
    triggers = _doc().get(True) or _doc().get("on")
    assert "workflow_run" not in triggers and "workflow_call" not in triggers


def test_every_action_is_pinned_to_a_commit_sha() -> None:
    for step in _doc()["jobs"]["attest"]["steps"]:
        uses = step.get("uses")
        if uses:
            ref = uses.split("@")[1].split()[0]
            assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref)
