"""Incident test (crew#66, founder 2026-08-28): a session ran bare `kubectl` on the laptop, hit the
dead k3d-estate context (connection refused on 127.0.0.1:6445) and graded the estate BLIND while the
cluster was fine. Founder: "it shouldn't, don't repeat mistakes … solve once and forever."

bin/idp-kube is the one path: the kubeconfig comes from bin/idp-cloud (file backend here, so no
network socket is ever opened), lands 0600 under its own state dir, and kubectl runs with KUBECONFIG
set to it -- ~/.kube/config is never consulted. No cluster = BLIND exit 2, never a silent fallback.
"""
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-kube"


def _env(tmp: Path, fake_bin: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("KUBECONFIG", "IDP_KUBE", "IDP_CLOUD"))}
    env.update({
        "PATH": f"{fake_bin}:{env.get('PATH', '')}",
        "HOME": str(tmp / "home"),
        "IDP_CLOUD_BACKEND": "file",
        "IDP_CLOUD_FILE_ROOT": str(tmp / "cloud"),
        "IDP_KUBE_STATE": str(tmp / "state"),
    })
    return env


def _fake_kubectl(tmp: Path) -> Path:
    fake_bin = tmp / "fakebin"
    fake_bin.mkdir()
    k = fake_bin / "kubectl"
    k.write_text('#!/bin/sh\nprintf "KUBECONFIG=%s ARGS=%s\\n" "${KUBECONFIG:-unset}" "$*"\n')
    k.chmod(0o755)
    (tmp / "home").mkdir()
    return fake_bin


def _cluster(tmp: Path) -> None:
    c = tmp / "cloud" / "clusters" / "ocid1.cluster.test"
    c.mkdir(parents=True)
    (c / "name").write_text("estate\n")
    (c / "kubeconfig").write_text("apiVersion: v1\nkind: Config\ncurrent-context: estate\n")


def test_kubectl_runs_only_against_the_estate_kubeconfig(tmp_path: Path) -> None:
    fake_bin = _fake_kubectl(tmp_path)
    _cluster(tmp_path)
    r = subprocess.run([str(TOOL), "get", "pods", "-n", "observability"], env=_env(tmp_path, fake_bin),
                       capture_output=True, text=True, timeout=30)
    kc = tmp_path / "state" / "kubeconfig"
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == f"KUBECONFIG={kc} ARGS=get pods -n observability", r.stdout
    assert kc.read_text().startswith("apiVersion: v1")
    assert stat.S_IMODE(kc.stat().st_mode) == 0o600
    assert not (tmp_path / "home" / ".kube").exists(), "the laptop's own kube config must never be touched"


def test_no_cluster_is_blind_never_a_fallback_context(tmp_path: Path) -> None:
    fake_bin = _fake_kubectl(tmp_path)
    (tmp_path / "cloud").mkdir()
    r = subprocess.run([str(TOOL), "get", "nodes"], env=_env(tmp_path, fake_bin),
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stderr.startswith("BLIND   kube  no ACTIVE cluster"), r.stderr
    assert "KUBECONFIG=" not in r.stdout, "kubectl must not run when there is no cluster"


def test_cached_kubeconfig_is_reused_and_refresh_rebuilds_it(tmp_path: Path) -> None:
    fake_bin = _fake_kubectl(tmp_path)
    _cluster(tmp_path)
    env = _env(tmp_path, fake_bin)
    subprocess.run([str(TOOL)], env=env, capture_output=True, text=True, timeout=30, check=True)
    kc = tmp_path / "state" / "kubeconfig"
    kc.write_text("cached\n")
    subprocess.run([str(TOOL), "version"], env=env, capture_output=True, text=True, timeout=30, check=True)
    assert kc.read_text() == "cached\n", "a fresh cache is reused"
    subprocess.run([str(TOOL), "--refresh", "version"], env=env, capture_output=True, text=True, timeout=30, check=True)
    assert kc.read_text().startswith("apiVersion: v1"), "--refresh rebuilds it"
