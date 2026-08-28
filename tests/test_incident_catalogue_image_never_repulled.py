"""Incident 2026-08-25 (crew#267): the catalogue ran ghcr.io/.../backstage:main with
imagePullPolicy IfNotPresent, so a new image on main changed nothing until someone ran
`kubectl rollout restart`. Rule: the tag the build writes is orderable, the ImagePolicy orders it,
the kustomization line carries the policy marker, and the branch the automation pushes to is
graded by ci and turned into an auto-merged pull request. Both ways: the bare sha tag (the old
shape) is refused by the policy filter; the build's tag is accepted and its run number extracted."""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUTOMATION = yaml.safe_load_all((ROOT / "platform/image-automation/backstage.yaml").read_text())
BY_KIND = {d["kind"]: d for d in AUTOMATION if d}
SHA = "a" * 40


def _build_tag_template() -> str:
    wf = (ROOT / ".github/workflows/build-multiarch.yml").read_text()
    m = re.search(r'-t "\$image:(main-\$\{\{ github\.run_number \}\}-\$\{\{ github\.sha \}\})"', wf)
    assert m, "build-multiarch no longer pushes the orderable main-<run>-<sha> tag"
    return m.group(1)


def test_policy_orders_the_tag_the_build_writes_and_refuses_the_bare_sha():
    tag = _build_tag_template().replace("${{ github.run_number }}", "4071").replace("${{ github.sha }}", SHA)
    ft = BY_KIND["ImagePolicy"]["spec"]["filterTags"]
    pat = re.compile(ft["pattern"].replace("(?P<", "(?P<"))
    assert pat.fullmatch(tag), (ft["pattern"], tag)
    assert pat.fullmatch(tag).group("run") == "4071" and ft["extract"] == "$run"
    assert pat.fullmatch(SHA) is None, "the bare provenance tag must not be ordered"
    assert BY_KIND["ImagePolicy"]["spec"]["policy"] == {"numerical": {"order": "asc"}}


def test_kustomization_carries_the_policy_marker():
    text = (ROOT / "platform/backstage/overlays/oke/kustomization.yaml").read_text()
    m = re.search(r'newTag: (\S+) # \{"\$imagepolicy": "flux-system:backstage:tag"\}', text)
    assert m, "newTag line has no $imagepolicy marker; image-automation-controller cannot find it"
    update = BY_KIND["ImageUpdateAutomation"]["spec"]["update"]
    assert update["strategy"] == "Setters"
    # crew#406: one automation walks ./platform; the overlay must sit under its path.
    assert "platform/backstage/overlays/oke".startswith(update["path"].removeprefix("./")), update


def test_controllers_are_installed_and_the_writer_is_a_deploy_key():
    """crew#325: the writer was the estate-agents GitHub App, which needed a person to tap Create; a day
    went by with every session calling that a founder action. A deploy key needs no person."""
    gotk = (ROOT / "clusters/oke/flux-system/gotk-components.yaml").read_text()
    deployments = {d["metadata"]["name"] for d in yaml.safe_load_all(gotk) if d and d["kind"] == "Deployment"}
    assert {"image-reflector-controller", "image-automation-controller"} <= deployments, deployments
    writer = BY_KIND["GitRepository"]
    assert writer["spec"]["url"].startswith("ssh://git@github.com/") and "provider" not in writer["spec"]
    assert writer["spec"]["secretRef"] == {"name": "flux-writer"}
    es = yaml.safe_load((ROOT / "platform/image-automation/flux-writer.yaml").read_text())
    assert set(es["spec"]["target"]["template"]["data"]) == {"identity", "identity.pub", "known_hosts"}
    assert es["spec"]["dataFrom"] == [{"extract": {"key": "flux-writer"}}]
    seed = (ROOT / ".github/workflows/vault-seed.yml").read_text()
    assert "put flux-writer identity_b64=FLUX_WRITER_IDENTITY_B64 pub=FLUX_WRITER_PUB" in seed
    assert not (ROOT / "platform/image-automation/github-app.yaml").exists(), "the App is off the writer path"
    assert BY_KIND["ImageUpdateAutomation"]["spec"]["sourceRef"]["name"] == writer["metadata"]["name"]


def test_the_automation_branch_is_graded_and_becomes_a_pull_request():
    branch = BY_KIND["ImageUpdateAutomation"]["spec"]["git"]["push"]["branch"]
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    assert branch in (ci.get("on") or ci.get(True))["push"]["branches"], "required checks would never run on the automation push"
    pr = yaml.safe_load((ROOT / ".github/workflows/image-update-pr.yml").read_text())
    assert (pr.get("on") or pr.get(True))["push"]["branches"] == [branch]
    run = pr["jobs"]["open"]["steps"][-1]["run"].strip()
    script = ROOT / run.splitlines()[-1].strip()  # crew#439: the step ends by running bin/idp-image-update-pr; the rule binds the script
    assert script.exists(), script
    run = script.read_text()
    assert "gh pr merge" in run and "--auto" in run
