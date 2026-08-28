"""crew#570, 2026-08-28: three hours of the alerting stack being down, and the instrument that
was supposed to name why printed the pod's name and stopped.

`robusta` blocked `monitoring`, `monitoring`+`robusta` blocked `monitoring-rules` and `chaos`, so
alertmanager was 404 and the Watchdog dead-man's switch had never fired. The break-glass
`diagnose` playbook ran (run 33167947182) and printed:

    --- pods-not-running
    robusta  robusta-runner-6c9995fd89-tcbvg  0/1  Init:ImageInspectError  0             3h32m
    robusta  robusta-runner-7d55bd7b6d-5r9xl  0/1  Init:Error              4 (117s ago)  3m35s

and never described either pod or read a line of its log, because both selectors it feeds the
describe-and-tail loop with require `status.phase == "Running"` -- and a pod whose INIT container
crash-loops is `Pending`, not `Running`. The answer (`Back-off restarting failed container
setup-venv`) was only in the cluster's events, which nothing correlated to the pod.

A diagnostic that names a broken pod and cannot say why is the proxy this estate keeps grading.
These tests run the real playbook against a recording kubectl that reports exactly that pod.
"""
import os
import stat
import subprocess
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"

NS, POD = "robusta", "robusta-runner-7d55bd7b6d-5r9xl"
# The selector idp#584 settled on for a pod that never started. A pod whose init container
# crash-loops never reaches Running, so neither the Ready-condition nor the Failed selector sees it.
PENDING_SELECTOR = "status.phase=Pending"


def _fake_cluster(tmp_path: Path) -> tuple[Path, Path]:
    """A kubectl that records every call and answers the pod selectors like the real cluster did
    at 11:43Z: no Running-but-unready pod, no Failed pod, one pod stuck in Init:Error."""
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    kubectl = bin_dir / "kubectl"
    kubectl.write_text(
        "#!/bin/sh\n"
        f'printf \'%s\\n\' "kubectl $*" >> "{log}"\n'
        'case "$*" in\n'
        f'  *"{PENDING_SELECTOR}"*-o\\ jsonpath*) echo "{NS} {POD}" ;;\n'
        '  *jsonpath*) : ;;\n'
        '  *) echo ok ;;\n'
        'esac\n'
        "exit 0\n"
    )
    kubectl.chmod(kubectl.stat().st_mode | stat.S_IEXEC)
    for tool in ("flux", "helm"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "{tool} $*" >> "{log}"\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return bin_dir, log


def _diagnose(tmp_path: Path) -> tuple[subprocess.CompletedProcess, str]:
    bin_dir, log = _fake_cluster(tmp_path)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "diagnose"], capture_output=True, text=True, env=env,
                       timeout=300)
    return p, (log.read_text() if log.exists() else "")


def test_a_pod_stuck_in_init_is_described(tmp_path):
    """The fault was in the pod's own events. Nothing printed them."""
    p, calls = _diagnose(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert f"describe pod {POD} -n {NS}" in calls, (
        "diagnose listed the pod under pods-not-running and never described it:\n" + calls)


def test_a_pod_stuck_in_init_has_its_log_read(tmp_path):
    p, calls = _diagnose(tmp_path)
    assert f"logs {POD} -n {NS} --all-containers" in calls or \
           f"logs '{POD}' -n '{NS}' --all-containers" in calls, calls


def test_the_previous_attempt_is_read_too(tmp_path):
    """A container that is between crash-loop attempts has an empty current log; the words that
    name the fault are in the previous one."""
    _, calls = _diagnose(tmp_path)
    previous = [c for c in calls.splitlines() if "--previous" in c and POD in c]
    assert previous, "no --previous read; a crash-loop's current log is usually empty:\n" + calls


def test_diagnose_stays_read_only(tmp_path):
    """LAW 38 and the reason diagnose is the one playbook that needs no argument: widening what
    it reads must not widen what it touches."""
    p, calls = _diagnose(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    banned = [c for c in calls.splitlines()
              if any(f"kubectl {v} " in c or f"flux {v} " in c
                     for v in ("delete", "apply", "patch", "scale", "edit", "replace", "rollout",
                               "reconcile", "create", "run"))]
    assert banned == [], banned
