"""crew#633 / crew#661 CP1 (2026-08-30): the kyverno webhook stopped answering and every pod
create in the estate was refused with an empty reason for 18 hours (tailscale-operator,
healing/estate); the Estate Mac tab and the private network sat dark behind it.

The class of mistake: a webhook failure with failurePolicy Fail that reads as a policy denial.
The only playbook that repaired it (cilium-unchain, run 33133317589) also rewrites CNI files,
so nobody dared run it. `webhooks-restart` is the narrow half. This file pins the three
properties the founder pays for: it is a playbook the runner admits, it refuses to restart
anything when the cluster's events show no webhook fault (attribute before repair), and it
carries a breaker (bounded attempts, cool-off, open state on the Deployment, loud when open).
Rung 4: runs the script against a recording kubectl; opens no socket.
"""

import os
import pathlib
import stat
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "bin/idp-oke-break-glass"
WORKFLOW = ROOT / ".github/workflows/oke-check.yml"
SRC = PLAYBOOK.read_text()


def _fake_bin(tmp_path: pathlib.Path, events: str, attempts: str = "") -> pathlib.Path:
    fake = tmp_path / "bin"
    fake.mkdir()
    log = tmp_path / "calls.log"
    (tmp_path / "events.txt").write_text(events + "\n")
    k = fake / "kubectl"
    k.write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> "{log}"\n'
        f'case "$*" in *"get events"*) cat "{tmp_path / "events.txt"}" ;;\n'
        f"  *webhooks-restart-attempts*) printf '%s' \"{attempts}\" ;;\n"
        "  *webhooks-restart-last*) date -u +%s ;; esac\n"
        "exit 0\n"
    )
    k.chmod(k.stat().st_mode | stat.S_IEXEC)
    f = fake / "flux"
    f.write_text(f'#!/bin/sh\necho "flux $*" >> "{log}"\nexit 0\n')
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return fake


def _run(fake: pathlib.Path, tmp_path: pathlib.Path) -> tuple[int, str, str]:
    env = dict(
        os.environ, PATH=f"{fake}:{os.environ['PATH']}", KUBECONFIG=str(tmp_path / "kc")
    )
    (tmp_path / "kc").write_text("apiVersion: v1\nkind: Config\n")
    p = subprocess.run(
        [str(PLAYBOOK), "webhooks-restart"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (
        p.returncode,
        p.stdout + p.stderr,
        (tmp_path / "calls.log").read_text()
        if (tmp_path / "calls.log").exists()
        else "",
    )


def test_the_runner_admits_the_playbook():
    listed = subprocess.run(
        [str(PLAYBOOK), "--list"], capture_output=True, text=True
    ).stdout
    assert "webhooks-restart" in listed.split()
    assert "webhooks-restart) pb_webhooks_restart ;;" in SRC
    assert (
        "webhooks-restart" in WORKFLOW.read_text().split("options: [")[2].split("]")[0]
    )


def test_no_fault_measured_means_nothing_is_restarted(tmp_path):
    fake = _fake_bin(
        tmp_path, "2026-08-30T06:00:00Z healing/estate Scaled up replica set"
    )
    rc, out, calls = _run(fake, tmp_path)
    assert rc != 0
    assert "no-fault-measured" in out
    assert "rollout restart" not in calls


def test_a_webhook_fault_is_restarted_and_the_cached_rows_reconciled(tmp_path):
    fake = _fake_bin(
        tmp_path,
        '2026-08-30T06:00:00Z tailscale/operator-56cf79864d Error creating: admission webhook "validate.kyverno.svc-fail" denied the request: ',
    )
    rc, out, calls = _run(fake, tmp_path)
    assert rc == 0, out
    assert "rollout restart deploy -n external-secrets" in calls
    assert "rollout restart deploy -n kyverno" in calls
    for row in ("edge", "secret-store", "tailscale", "guacamole"):
        assert f"flux reconcile kustomization {row} -n flux-system" in calls
    assert "estate.idp/webhooks-restart-attempts=1" in calls


def test_the_breaker_opens_after_the_bounded_attempts(tmp_path):
    fake = _fake_bin(
        tmp_path,
        "2026-08-30T06:00:00Z flux-system/edge failed calling webhook mutate-policy.kyverno.svc EOF",
        attempts="2",
    )
    rc, out, calls = _run(fake, tmp_path)
    assert rc != 0
    assert "BREAKER OPEN webhooks-restart" in out
    assert "breaker-open-webhooks-restart" in out
    assert "rollout restart" not in calls


def test_the_breaker_is_named_in_the_script():
    for needle in (
        "WEBHOOKS_RESTART_MAX",
        "WEBHOOKS_RESTART_COOLOFF_S",
        "estate.idp/webhooks-restart-attempts",
        "estate.idp/webhooks-restart-last",
    ):
        assert needle in SRC
