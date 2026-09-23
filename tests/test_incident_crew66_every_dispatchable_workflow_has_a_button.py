"""crew#66, founder 2026-08-28: "founder does not remember commands or run scripts" and "we are
underutilising backstage". Every workflow a person could dispatch by hand is a button on the
portal's Create page, and the buttons are generated from the workflows, never typed.

The incident this guards: a dispatchable workflow lands (or an input changes) and the portal keeps
offering the old set, so the founder is back to the Actions tab and a command. The check runs on
the tree in CI (`bin/idp-portal-buttons --check`) and here, and it is proved red both ways: a tree
with a workflow and no button fails, and a button with no workflow behind it fails.

No sockets: the generator reads .github/workflows and writes backstage/templates/founder-actions.
"""

import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "idp-portal-buttons"
WORKFLOWS = ROOT / ".github" / "workflows"
BUTTONS = ROOT / "backstage" / "templates" / "founder-actions"
CONFIGS = [
    ROOT / "backstage" / "app-config.yaml",
    ROOT / "backstage" / "app-config.container.yaml",
]


def _run(root, *args):
    return subprocess.run(
        [sys.executable, str(root / "bin" / "idp-portal-buttons"), *args],
        capture_output=True,
        text=True,
    )


def _dispatchable():
    out = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        doc = yaml.safe_load(path.read_text())
        on = doc.get("on") or doc.get(True) or {}
        if isinstance(on, dict) and "workflow_dispatch" in on:
            out.append(path)
    return out


SYNTHETIC = """# button: Synthetic inputs
# founder: A workflow with every input shape the generator maps.
name: Synthetic inputs
on:
  workflow_dispatch:
    inputs:
      mode:
        description: which mode
        type: choice
        options: [check, apply]
        default: check
      dry_run:
        type: boolean
        default: true
      reason:
        description: why
        required: true
jobs:
  noop:
    runs-on: ubuntu-latest
    steps:
      - run: "true"
"""


def _mini_tree(tmp_path, workflows, synthetic=False):
    """A copy of the repo shape with only the named workflows, buttons generated fresh."""
    root = tmp_path / "tree"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "bin").mkdir()
    shutil.copy(GEN, root / "bin" / "idp-portal-buttons")
    for wf in workflows:
        shutil.copy(wf, root / ".github" / "workflows" / wf.name)
    if synthetic:
        (root / ".github" / "workflows" / "synthetic.yml").write_text(SYNTHETIC)
    assert _run(root).returncode == 0
    return root


def test_the_committed_buttons_match_the_workflows():
    r = _run(ROOT, "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (
        f"ok      portal-buttons: {len(_dispatchable())} dispatchable workflow(s)"
        in r.stdout
    )


def test_every_button_dispatches_a_real_workflow_on_main():
    names = {p.name for p in _dispatchable()}
    assert names, "no dispatchable workflow found; the generator would be BLIND"
    seen = set()
    for tpl in sorted(BUTTONS.glob("*/template.yaml")):
        doc = yaml.safe_load(tpl.read_text())
        assert doc["kind"] == "Template" and doc["spec"]["type"] == "founder-action", (
            tpl
        )
        (step,) = doc["spec"]["steps"]
        assert step["action"] == "github:actions:dispatch", tpl
        assert step["input"]["workflowId"] in names, (
            f"{tpl} dispatches a workflow that does not exist"
        )
        assert step["input"]["branchOrTagName"] == "main", tpl
        seen.add(step["input"]["workflowId"])
    assert seen == names, f"buttons and workflows differ: {sorted(seen ^ names)}"


def test_choice_inputs_become_drop_downs_and_defaults_survive(tmp_path):
    """The founder never types a value a workflow already knows: choices are enums, defaults stay,
    a required input with no default is required on the form, a boolean is a tick box."""
    root = _mini_tree(tmp_path, [], synthetic=True)
    doc = yaml.safe_load(
        (
            root
            / "backstage"
            / "templates"
            / "founder-actions"
            / "synthetic"
            / "template.yaml"
        ).read_text()
    )
    (page,) = doc["spec"]["parameters"]
    props = page["properties"]
    assert (
        props["mode"]["enum"] == ["check", "apply"]
        and props["mode"]["default"] == "check"
    )
    assert props["dry_run"]["type"] == "boolean" and props["dry_run"]["default"] is True
    # the input's sentence is the form label (crew#612: the key is never shown to a person)
    assert props["reason"]["title"] == "why" and page["required"] == ["reason"]
    assert doc["spec"]["steps"][0]["input"]["workflowInputs"] == {
        k: "${{ parameters." + k + " }}" for k in ("mode", "dry_run", "reason")
    }
    assert doc["metadata"]["description"].startswith(
        "A workflow with every input shape"
    )


def test_the_portal_loads_the_buttons_in_both_configs():
    for cfg in CONFIGS:
        targets = [
            loc.get("target", "")
            for loc in (yaml.safe_load(cfg.read_text()).get("catalog") or {}).get(
                "locations"
            )
            or []
        ]
        assert any(
            t.endswith("templates/founder-actions/*/template.yaml") for t in targets
        ), cfg


def test_a_workflow_without_a_button_is_red(tmp_path):
    wfs = _dispatchable()[:2]
    root = _mini_tree(tmp_path, wfs)
    shutil.rmtree(root / "backstage" / "templates" / "founder-actions" / wfs[0].stem)
    r = _run(root, "--check")
    assert r.returncode == 1 and "MISSING" in r.stdout, r.stdout


def test_a_button_without_a_workflow_is_red(tmp_path):
    wfs = _dispatchable()[:2]
    root = _mini_tree(tmp_path, wfs)
    (root / ".github" / "workflows" / wfs[0].name).unlink()
    r = _run(root, "--check")
    assert r.returncode == 1 and "STRAY" in r.stdout, r.stdout


def test_a_changed_input_is_red_until_regenerated(tmp_path):
    root = _mini_tree(tmp_path, [], synthetic=True)
    wf = root / ".github" / "workflows" / "synthetic.yml"
    wf.write_text(
        wf.read_text().replace(
            "options: [check, apply]", "options: [check, apply, destroy]"
        )
    )
    r = _run(root, "--check")
    assert r.returncode == 1 and "STALE" in r.stdout, r.stdout
