"""Incident 2026-08-28 (crew#539, oke-check diagnose 33172481714): robusta-runner sat in
Init:CrashLoopBackOff for 5h; the init log read
`cp: preserving times for '/venv-writable/.': Operation not permitted`. The chart's hardenedFs
init (`runner.yaml`, chart 0.48.0) copies site-packages with `cp -a`, which after a successful
copy sets the times of the emptyDir root; the pod runs as uid 1000 with every capability dropped,
and the kubelet creates the emptyDir root-owned, so utimes is refused and `cp` exits 1.
Rule: the estate's patch overrides the init command and never asks cp to preserve attributes."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _runner_patch():
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/robusta/robusta.yaml").read_text()) if d]
    hr = next(d for d in docs if d["kind"] == "HelmRelease")
    for p in hr["spec"]["postRenderers"][0]["kustomize"]["patches"]:
        if p["target"].get("name") == "robusta-runner":
            return yaml.safe_load(p["patch"])
    raise AssertionError("no robusta-runner Deployment patch")


def _setup_venv():
    inits = _runner_patch()["spec"]["template"]["spec"]["initContainers"]
    return next(c for c in inits if c["name"] == "setup-venv")


def test_setup_venv_command_is_overridden() -> None:
    c = _setup_venv()
    assert c.get("command"), "no command override: the chart's `cp -a` runs and fails on utimes of the emptyDir root"


def test_setup_venv_copy_preserves_no_attributes() -> None:
    script = " ".join(_setup_venv()["command"])
    assert "cp " in script and "/venv-writable/" in script
    for flag in ("-a", "-p", "--preserve", "--archive"):
        assert f" {flag}" not in script, f"cp {flag} sets times on a root-owned emptyDir as uid 1000: refused"


def test_setup_venv_still_copies_the_chart_source() -> None:
    script = " ".join(_setup_venv()["command"])
    assert "/venv/lib/python" in script and "site-packages" in script, "the override must copy what the chart copies"
