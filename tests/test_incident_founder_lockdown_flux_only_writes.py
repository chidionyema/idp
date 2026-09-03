"""Founder lockdown, 2026-09-03: "if you dont cone up with solutin then lockdown is happening"
(~/.claude/docs/founder/2026-09-03T1234Z-if-you-dont-cone-up-with-solutin-then-3aefc8e6.md).
The cluster had drifted: objects nobody's git held, written by whichever key was on a laptop
at 2 AM. The fence is admission, not a doc: platform/edge/flux-only-writes.yaml refuses every
CREATE, UPDATE and DELETE from an OCI user principal (ocid1.user.*, which is how every laptop
key, agent and person presents to OKE) and excuses exactly one, the oke-check apply workflow's
service user named once in clusters/oke/estate-config.yaml. Flux and every in-cluster
controller write as system:* and are never judged. This suite proves the four ways through
the Kyverno CLI, with the same admission identities the cluster sees."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform/edge/flux-only-writes.yaml"
ESTATE_CONFIG = ROOT / "clusters/oke/estate-config.yaml"
KEY = "ESTATE_BREAK_GLASS_USER"

# The founder's laptop key as measured on 2026-09-03 (`auth whoami` over ~/.kube/oke-estate-apikey):
# an OCI user OCID for the username, system:masters in the groups. Any other user OCID looks the same.
A_LAPTOP_KEY = (
    "ocid1.user.oc1..aaaaaaaay4rrvpfuz7rkyexkbduyc3qgvift2bm67x7zsbvsy5yzxkwzbncq"
)
FLUX = "system:serviceaccount:flux-system:kustomize-controller"

PROBE = """apiVersion: v1
kind: ConfigMap
metadata:
  name: probe
  namespace: default
data:
  written-by: a hand
"""


def _break_glass_user() -> str:
    data = yaml.safe_load(ESTATE_CONFIG.read_text())["data"]
    assert KEY in data, (
        f"{KEY} is missing from clusters/oke/estate-config.yaml (the one place it lives)"
    )
    return data[KEY]


def _rendered_policy(tmp_path: Path) -> Path:
    """Flux postBuild substitutes ${ESTATE_BREAK_GLASS_USER} from estate-config; do the same."""
    text = POLICY.read_text()
    assert "${" + KEY + "}" in text, (
        "the policy must read the break-glass identity from estate-config, never a literal"
    )
    out = tmp_path / "flux-only-writes.rendered.yaml"
    out.write_text(text.replace("${" + KEY + "}", _break_glass_user()))
    return out


def _apply(tmp_path: Path, username: str | None, groups: list[str]) -> str:
    assert shutil.which("kyverno"), (
        "BLIND: the kyverno CLI is not installed; ci.yml installs it"
    )
    res = tmp_path / "probe.yaml"
    res.write_text(PROBE)
    cmd = ["kyverno", "apply", str(_rendered_policy(tmp_path)), "--resource", str(res)]
    if username is not None:
        ui = tmp_path / f"{re.sub(r'[^a-z0-9]', '-', username.lower())[:40]}.yaml"
        ui.write_text(
            "apiVersion: cli.kyverno.io/v1alpha1\nkind: UserInfo\nmetadata:\n  name: ui\n"
            "userInfo:\n  username: %s\n  groups: [%s]\n"
            % (username, ", ".join(groups))
        )
        cmd += ["--userinfo", str(ui)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout + r.stderr


def test_a_laptop_key_in_system_masters_is_refused(tmp_path: Path) -> None:
    out = _apply(tmp_path, A_LAPTOP_KEY, ["system:masters", "system:authenticated"])
    assert "fail: 1" in out, out
    assert "refuse-writes-from-user-principals" in out


def test_the_deploy_workflow_service_user_is_the_one_excused_identity(
    tmp_path: Path,
) -> None:
    out = _apply(
        tmp_path, _break_glass_user(), ["system:masters", "system:authenticated"]
    )
    assert "pass: 1" in out and "fail: 0" in out, out


def test_flux_writes_are_never_judged(tmp_path: Path) -> None:
    out = _apply(tmp_path, FLUX, ["system:serviceaccounts", "system:authenticated"])
    assert "skip: 1" in out and "fail: 0" in out, out


def test_the_ci_render_check_carries_no_identity_and_is_not_blocked(
    tmp_path: Path,
) -> None:
    """bin/idp-kyverno-render loads every ClusterPolicy under platform/ and applies them to
    every rendered workload with no admission identity; that must stay a skip, never a fail."""
    out = _apply(tmp_path, None, [])
    assert "skip: 1" in out and "fail: 0" in out, out


def test_the_policy_is_enforced_on_every_kind_and_every_write() -> None:
    doc = yaml.safe_load(POLICY.read_text())
    assert doc["spec"]["background"] is False, (
        "a rule on request.userInfo needs background: false"
    )
    [rule] = doc["spec"]["rules"]
    [res] = [m["resources"] for m in rule["match"]["any"]]
    assert res["kinds"] == ["*"]
    assert sorted(res["operations"]) == ["CREATE", "DELETE", "UPDATE"]
    assert rule["validate"]["failureAction"] == "Enforce"
    assert (
        "flux-only-writes.yaml"
        in (ROOT / "platform/edge/kustomization.yaml").read_text()
    )


def test_the_break_glass_identity_is_a_user_ocid_named_once() -> None:
    user = _break_glass_user()
    assert user.startswith("ocid1.user.oc1.."), user
    assert user not in POLICY.read_text(), (
        "the OCID is written once, in estate-config (R70)"
    )
    edge = (ROOT / "clusters/oke/edge.yaml").read_text()
    assert "estate-config" in edge, (
        "the edge row must substitute from estate-config for the policy to render"
    )


if __name__ == "__main__":
    pytest.main([__file__])
