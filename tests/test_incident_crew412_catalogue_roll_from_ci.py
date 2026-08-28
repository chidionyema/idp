"""crew#412, 2026-08-28: idp#564 (c6e6026) pinned the right portal image at 11:00Z and the serving
ReplicaSet was still catalogue-8647bbdc59 seventy minutes later; login-drill 33168523304 stayed red
("catalogue holds 0 founder-surface entities"). The estate could retry a HelmRelease from CI
(helm-retry) and could read the cluster (diagnose), but had no path to make Flux apply a
Kustomization now -- the founder surface waited on the reconcile interval and on the next oke-check
happening to notice (LAW 20, LAW 31). `catalogue-roll` is that path, and this file holds it to the
shape that makes it an answer rather than a nudge: it reconciles the backstage Kustomization with
its source, waits on the rollout, and prints the image the Deployment serves.
"""
import os
import stat
import subprocess
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"


def _run(playbook: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), playbook], capture_output=True, text=True, env=env)
    return p, (log.read_text().splitlines() if log.exists() else [])


def test_catalogue_roll_is_a_named_playbook():
    out = subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True, check=True).stdout
    assert "catalogue-roll" in out.split(), out


def test_it_reconciles_the_backstage_kustomization_with_its_source(tmp_path):
    p, calls = _run("catalogue-roll", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    ks = [c for c in calls if c.startswith("flux reconcile kustomization backstage")]
    assert ks, f"never reconciled the backstage Kustomization: {calls}"
    assert "--with-source" in ks[0], ks[0]


def test_it_waits_on_the_rollout_and_prints_the_served_image(tmp_path):
    """A reconcile that returns before the pods roll is the state crew#412 was already in: the
    Kustomization Applied, the old ReplicaSet serving. The run is only an answer when it waited
    on the rollout and printed the image the Deployment holds afterwards."""
    _, calls = _run("catalogue-roll", tmp_path)
    assert any(("rollout status deploy/catalogue -n backstage" in c) for c in calls), calls
    assert any("get deploy catalogue -n backstage" in c and "containers[0].image" in c for c in calls), calls


def test_it_touches_nothing_but_the_portal(tmp_path):
    """The door is open for one job; the playbook that rolls the portal never deletes, patches or
    scales anything, in any namespace."""
    _, calls = _run("catalogue-roll", tmp_path)
    for c in calls:
        for verb in ("delete", "patch", "scale", "apply", "edit", "replace", "create"):
            assert f" {verb} " not in f" {c} ", c
        if c.startswith("kubectl") and " -n " in c:
            assert " -n backstage" in c, c
