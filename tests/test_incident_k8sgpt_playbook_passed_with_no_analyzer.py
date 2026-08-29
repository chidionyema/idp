"""2026-08-29 04:29Z, run 33233870612 (crew#503): `k8sgpt-analyze` printed
`No resources found in healing namespace` for its restart step and still said PASS. The operator
(k8sgpt-operator-controller-manager 1/1, HelmRelease InstallSucceeded 2026-08-27) had never turned
the K8sGPT object `estate` into an analyzer deployment, so there were no findings to page, and the
receipt could not say why. The playbook now prints the object's status, the secret it names, the
deployments and the operator's own log first, and an absent analyzer is a FAIL, not a green.
"""
import os
import stat
import subprocess
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"


def _run(tmp_path: Path, analyzer_present: bool) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    deploy = "deployment.apps/estate" if analyzer_present else ""
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"kubectl $*\" >> \"{log}\"\n"
        "case \"$*\" in\n"
        f"  *'get deployment -n healing -l app=estate -o name'*) echo '{deploy}' ;;\n"
        "  *logs*) echo 'ERROR reconciler: secret \"k8sgpt\" not found' ;;\n"
        "  *) echo ok ;;\n"
        "esac\n"
    )
    (bin_dir / "flux").write_text(f"#!/bin/sh\nprintf '%s\\n' \"flux $*\" >> \"{log}\"\necho ok\n")
    for f in (bin_dir / "kubectl", bin_dir / "flux"):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "k8sgpt-analyze"], capture_output=True, text=True, env=env)
    return p, (log.read_text().splitlines() if log.exists() else [])


def test_an_absent_analyzer_is_a_fail_with_the_operator_log_in_the_receipt(tmp_path):
    p, calls = _run(tmp_path, analyzer_present=False)
    assert p.returncode != 0, p.stdout
    assert "FAIL  k8sgpt-analyze  no analyzer deployment" in p.stdout, p.stdout
    assert "--- k8sgpt-operator-log" in p.stdout and 'secret "k8sgpt" not found' in p.stdout, p.stdout
    # run 33235032630: the sidecar's TLS noise drowned the reconciler; the log is the manager container only
    assert "-c manager" in p.stdout or "--- k8sgpt-describe" in p.stdout, p.stdout
    assert "--- k8sgpt-describe" in p.stdout and "--- healing-events" in p.stdout, p.stdout
    assert "--- k8sgpt-object" in p.stdout and "--- k8sgpt-secret" in p.stdout, p.stdout
    assert not any("rollout restart" in c for c in calls), calls


def test_a_present_analyzer_is_restarted_and_its_results_shown(tmp_path):
    p, calls = _run(tmp_path, analyzer_present=True)
    assert p.returncode == 0, p.stdout
    assert any("rollout restart deployment -n healing" in c for c in calls), calls
    assert "--- k8sgpt-results" in p.stdout, p.stdout
    assert not any("app.kubernetes.io/name=k8sgpt" in c for c in calls), calls


def test_flux_waits_for_the_analyzer_deployment_not_just_the_object():
    # healing-analyzer had wait: true and no healthChecks; a bare custom object counts as Current,
    # so the row was green for 29h with no analyzer running (run 33233870612)
    import yaml
    rows = [d for d in yaml.safe_load_all((IDP / "clusters/oke/platform.yaml").read_text()) if d]
    row = next(d for d in rows if d["metadata"]["name"] == "healing-analyzer")
    checks = row["spec"].get("healthChecks") or []
    assert any(c.get("kind") == "Deployment" and c.get("name") == "estate" and c.get("namespace") == "healing" for c in checks), checks
