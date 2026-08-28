"""crew#539, 2026-08-28: the cluster could not heal itself and nobody had a kube path.

coredns died behind the Cilium chain, Flux could not resolve github.com, the merged revert
(idp#514) never reached the cluster. Runners are outside control_plane_allowed_cidrs and the
laptop session token is retired (crew#345). The fix is a break-glass mode on oke-check: the
runner's /32 is admitted through tofu for one job, ONE named playbook runs, the list is restored
on every exit path. These tests run the playbooks against a recording kubectl/flux and read the
rebuild script's break-glass branch for the two properties that make it safe.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"
REBUILD = IDP / "bin" / "idp-oke-rebuild"
WORKFLOW = IDP / ".github" / "workflows" / "oke-check.yml"
MUTATING = re.compile(r"^(kubectl|flux) (delete|apply|rollout|run|reconcile|patch|create|scale|edit|replace)\b")


def _fake_path(tmp_path: Path) -> tuple[Path, Path]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return bin_dir, log


def _run(playbook: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess, list[str]]:
    bin_dir, log = _fake_path(tmp_path)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), playbook], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines() if log.exists() else []
    return p, calls


def test_diagnose_is_read_only(tmp_path):
    p, calls = _run("diagnose", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert calls, "diagnose read nothing"
    assert [c for c in calls if MUTATING.match(c)] == []


def test_cilium_unchain_removes_the_release_before_the_cni_config_and_ends_with_flux(tmp_path):
    p, calls = _run("cilium-unchain", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    joined = "\n".join(calls)
    order = [
        joined.index("delete helmrelease -n kube-system cilium"),
        joined.index("apply -f -"),                       # the cni-unchain DaemonSet
        joined.index("rollout restart deploy/coredns"),
        joined.index("reconcile source git flux-system"),
        joined.index("reconcile kustomization flux-system"),
    ]
    assert order == sorted(order), calls
    assert "delete ds cni-unchain -n kube-system" in joined, "the privileged helper is not left on the cluster"


def test_cni_cleanup_helper_runs_on_the_host_network():
    """run 33132419902: with the chained config left behind, cilium-cni fails every new sandbox,
    so a helper on the pod network can never start. hostNetwork pods call no CNI."""
    src = PLAYBOOK.read_text()
    helper = src[src.index("name: cni-unchain"):src.index("YAML\n", src.index("name: cni-unchain"))]
    assert "hostNetwork: true" in helper


def test_unknown_playbook_is_refused_and_list_names_both(tmp_path):
    p, _ = _run("rm-rf-everything", tmp_path)
    assert p.returncode == 64
    listed = subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True).stdout.split()
    assert listed == ["diagnose", "cilium-unchain"]


def test_rebuild_break_glass_restores_the_list_on_every_exit_path():
    src = REBUILD.read_text()
    branch = src[src.index("--break-glass)"):src.index("--teardown-rebuild)")]
    assert 'ORIG_CIDRS="$OKE_ALLOWED_CIDRS"' in branch
    assert "trap bg_revoke EXIT" in branch and 'export OKE_ALLOWED_CIDRS="$ORIG_CIDRS"' in branch
    assert branch.index("trap bg_revoke EXIT") < branch.index('export OKE_ALLOWED_CIDRS="$ORIG_CIDRS, \\"$EGRESS/32\\""')
    assert '[ -n "${OCI_CI:-}" ] ||' in branch, "a laptop must be refused (crew#345)"
    assert "--list | tr ' ' '\\n' | grep -qx \"$PLAYBOOK\"" in branch, "only a named playbook runs"


def test_workflow_offers_break_glass_with_a_named_playbook():
    wf = WORKFLOW.read_text()
    assert "surge-finish, break-glass]" in wf
    assert "options: [diagnose, cilium-unchain]" in wf
    assert "BREAK_GLASS_PLAYBOOK: ${{ inputs.playbook || 'diagnose' }}" in wf


def test_dns_probe_pod_passes_the_cluster_pod_security_policies():
    """runs 33133317589 and 33134611331: the unchain landed but `dns-answers` failed because kyverno
    refused the `kubectl run` probe pod — first require-run-as-nonroot / require-ro-rootfs /
    restrict-seccomp-strict, then disallow-default-namespace / require-pod-probes /
    require-requests-limits. The probe is a full Pod manifest shaped like every platform workload."""
    import yaml
    src = PLAYBOOK.read_text()
    block = src[src.index("apiVersion: v1\nkind: Pod"):src.index("YAML\n", src.index("kind: Pod"))]
    pod = yaml.safe_load(block)
    assert pod["metadata"]["namespace"] == "kube-system"
    spec = pod["spec"]
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert spec["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
    assert spec["priorityClassName"]
    c = spec["containers"][0]
    assert c["resources"]["requests"]["cpu"] and c["resources"]["limits"]["memory"]
    assert c["readinessProbe"] and c["livenessProbe"]
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    assert c["securityContext"]["allowPrivilegeEscalation"] is False
    assert c["securityContext"]["capabilities"]["drop"] == ["ALL"]


def test_cilium_unchain_forces_secret_store_after_the_tree_and_removes_the_probe(tmp_path):
    """run 33134611331: the webhooks rolled out, yet `secret-store` still showed the dry-run EOF
    from before the restart — `flux reconcile kustomization flux-system` does not cascade. The
    playbook forces secret-store after the tree, and the probe pod is not left in kube-system."""
    p, calls = _run("cilium-unchain", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    joined = "\n".join(calls)
    assert joined.index("reconcile kustomization flux-system") < joined.index("reconcile kustomization secret-store")
    # review idp#525: a leftover probe (a prior run died before remove, or already Succeeded) makes
    # apply a no-op and dns-answers reads the old verdict; clear it, waiting, before the apply.
    clear = joined.index("delete pod/dns-probe -n kube-system --ignore-not-found --wait=true")
    assert clear < joined.index("apply -f -", joined.index("rollout status deploy/coredns"))
    assert joined.index("wait pod/dns-probe") < joined.index("delete pod/dns-probe", clear + 1)


def test_cilium_unchain_restarts_the_admission_webhooks_after_coredns_and_before_flux(tmp_path):
    """run 33133317589: the chain was removed and coredns rolled out, but the ESO webhook and kyverno
    admission pods rescheduled during the outage stayed in dead sandboxes, so secret-store and its
    dependents failed dry-run with EOF. The playbook restarts them onto fresh sandboxes before Flux."""
    p, calls = _run("cilium-unchain", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    joined = "\n".join(calls)
    order = [
        joined.index("rollout status deploy/coredns"),
        joined.index("rollout restart deploy -n external-secrets"),
        joined.index("rollout restart deploy -n kyverno"),
        joined.index("rollout status deploy -n external-secrets"),
        joined.index("reconcile source git flux-system"),
    ]
    assert order == sorted(order), calls
