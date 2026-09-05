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
FOUNDER_KEY = "ESTATE_FOUNDER_USER"

# The founder's laptop key as measured on 2026-09-03 (`auth whoami` over ~/.kube/oke-estate-apikey):
# an OCI user OCID for the username, system:masters in the groups. Any other user OCID looks the same.
A_LAPTOP_KEY = (
    "ocid1.user.oc1..aaaaaaaay4rrvpfuz7rkyexkbduyc3qgvift2bm67x7zsbvsy5yzxkwzbncq"
)
FLUX = "system:serviceaccount:flux-system:kustomize-controller"

FLUX_PROBE = """apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: platform
  namespace: flux-system
  annotations:
    reconcile.fluxcd.io/requestedAt: "2026-09-05T01:30:00Z"
spec:
  interval: 10m
  path: ./platform
  prune: true
  sourceRef: { kind: GitRepository, name: flux-system }
"""

PROBE = """apiVersion: v1
kind: ConfigMap
metadata:
  name: probe
  namespace: default
data:
  written-by: a hand
"""


def _config_user(key: str) -> str:
    data = yaml.safe_load(ESTATE_CONFIG.read_text())["data"]
    assert key in data, (
        f"{key} is missing from clusters/oke/estate-config.yaml (the one place it lives)"
    )
    return data[key]


def _break_glass_user() -> str:
    return _config_user(KEY)


def _founder_user() -> str:
    return _config_user(FOUNDER_KEY)


def _rendered_policy(tmp_path: Path) -> Path:
    """Flux postBuild substitutes both identities from estate-config; do the same."""
    text = POLICY.read_text()
    for key in (KEY, FOUNDER_KEY):
        assert "${" + key + "}" in text, (
            f"the policy must read {key} from estate-config, never a literal"
        )
        text = text.replace("${" + key + "}", _config_user(key))
    out = tmp_path / "flux-only-writes.rendered.yaml"
    out.write_text(text)
    return out


def _apply(
    tmp_path: Path,
    username: str | None,
    groups: list[str],
    *,
    probe: str = PROBE,
    operation: str | None = None,
) -> str:
    assert shutil.which("kyverno"), (
        "BLIND: the kyverno CLI is not installed; ci.yml installs it"
    )
    res = tmp_path / "probe.yaml"
    res.write_text(probe)
    cmd = ["kyverno", "apply", str(_rendered_policy(tmp_path)), "--resource", str(res)]
    if operation is not None:
        # The CLI applies every resource as a CREATE unless request.operation is set; the
        # founder exception below only exists on UPDATE, so the verb has to be stated.
        vals = tmp_path / "values.yaml"
        vals.write_text(
            "apiVersion: cli.kyverno.io/v1alpha1\nkind: Value\nmetadata:\n  name: values\n"
            "globalValues:\n  request.operation: %s\n" % operation
        )
        cmd += ["--values-file", str(vals)]
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


def test_the_founder_may_force_a_flux_reconcile(tmp_path: Path) -> None:
    """Founder break-glass 2026-09-05: `flux reconcile` is an UPDATE of the
    reconcile.fluxcd.io/requestedAt annotation on a Flux object. The lockdown refused it, so
    during an incident he could not apply the fix git already held."""
    out = _apply(
        tmp_path,
        _founder_user(),
        ["system:masters", "system:authenticated"],
        probe=FLUX_PROBE,
        operation="UPDATE",
    )
    assert "pass: 1" in out and "fail: 0" in out, out


def test_the_founders_hole_is_update_of_flux_objects_and_nothing_else(
    tmp_path: Path,
) -> None:
    """Three conditions, all required: his identity, the UPDATE verb, a Flux toolkit group.
    Drop any one and the lockdown still refuses him, so the exception cannot become drift."""
    groups = ["system:masters", "system:authenticated"]
    creating_a_flux_object = _apply(
        tmp_path, _founder_user(), groups, probe=FLUX_PROBE, operation="CREATE"
    )
    assert "fail: 1" in creating_a_flux_object, creating_a_flux_object
    deleting_a_flux_object = _apply(
        tmp_path, _founder_user(), groups, probe=FLUX_PROBE, operation="DELETE"
    )
    assert "fail: 1" in deleting_a_flux_object, deleting_a_flux_object
    updating_anything_else = _apply(
        tmp_path, _founder_user(), groups, probe=PROBE, operation="UPDATE"
    )
    assert "fail: 1" in updating_anything_else, updating_anything_else


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


def test_the_break_glass_identities_are_user_ocids_named_once() -> None:
    for user in (_break_glass_user(), _founder_user()):
        assert user.startswith("ocid1.user.oc1.."), user
        assert user not in POLICY.read_text(), (
            "the OCID is written once, in estate-config (R70)"
        )
    assert _break_glass_user() != _founder_user()
    edge = (ROOT / "clusters/oke/edge.yaml").read_text()
    assert "estate-config" in edge, (
        "the edge row must substitute from estate-config for the policy to render"
    )


if __name__ == "__main__":
    pytest.main([__file__])
