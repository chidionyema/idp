"""2026-08-29 01:05Z: idp#648 moved the portal's namespace.yaml between two Flux rows. The old row
pruned Namespace/backstage; the delete hung in Terminating (break-glass diagnose 33227202858:
`backstage-namespace ... timeout waiting for: [Namespace/backstage status: 'Terminating']`, 46 min);
every row behind it cascaded and catalogue.<zone> answered 404. The estate could read the cluster
and roll the portal from CI but had no path to clear a stuck namespace, and diagnose did not even
print that one was stuck. idp#686 makes the prune impossible; this file holds the repair and the
instrument: `namespace-unstick` clears finalizers on the leftover objects only (never the
namespace, never a delete) and reconciles the rows that recreate it; diagnose prints every
Terminating namespace with its conditions.
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
    # kubectl stub: one Terminating namespace, one leftover object carrying a finalizer
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"kubectl $*\" >> \"{log}\"\n"
        "case \"$*\" in\n"
        "  *api-resources*) echo externalsecrets.external-secrets.io ;;\n"
        "  *'get ns -o jsonpath'*Terminating*) echo backstage ;;\n"
        "  *'get externalsecrets.external-secrets.io -n backstage'*finalizers*) echo ExternalSecret/backstage-env ;;\n"
        "  *) echo ok ;;\n"
        "esac\n"
    )
    (bin_dir / "flux").write_text(f"#!/bin/sh\nprintf '%s\\n' \"flux $*\" >> \"{log}\"\necho ok\n")
    for f in (bin_dir / "kubectl", bin_dir / "flux"):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), playbook], capture_output=True, text=True, env=env)
    return p, (log.read_text().splitlines() if log.exists() else [])


def test_namespace_unstick_is_a_named_playbook():
    out = subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True, check=True).stdout
    assert "namespace-unstick" in out.split()
    wf = (IDP / ".github" / "workflows" / "oke-check.yml").read_text()
    assert "namespace-unstick" in wf, "the playbook is not dispatchable from Actions"


def test_it_clears_finalizers_on_the_leftover_object_and_never_deletes(tmp_path):
    p, calls = _run("namespace-unstick", tmp_path)
    assert any("patch externalsecret/backstage-env -n backstage" in c and '"finalizers":null' in c for c in calls), calls
    for c in calls:
        assert " delete " not in f" {c} ", c
        assert not ("patch ns" in c or "patch namespace" in c), c
    assert any("reconcile kustomization backstage-namespace" in c for c in calls), calls
    assert any("reconcile kustomization backstage " in c for c in calls), calls
    assert "--- conditions backstage" in p.stdout, p.stdout


def test_diagnose_prints_the_terminating_namespaces(tmp_path):
    p, _ = _run("diagnose", tmp_path)
    assert "--- namespaces-terminating" in p.stdout, p.stdout
