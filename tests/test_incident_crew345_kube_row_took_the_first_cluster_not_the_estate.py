"""crew#345 / crew#516 CP1, 2026-08-28: the compartment had three ACTIVE clusters and both
bin/idp-verify-drill's kube row and bin/idp-kube picked `awk NR==1` -- the first cluster by name,
not the estate -- so `create-kubeconfig` failed on every hourly verify-drill run from 14:03Z to
19:50Z (12 red in a row) while oke-check, which names its cluster, stayed green. The identity row
was green the whole time: the machine identity worked, the row after it pointed it at the wrong
cluster. On top, the row cut the ServiceError at 160 characters, so the receipt read
`"code": "InvalidP` and nobody could attribute it.

The guard, over both callers:
  * the cluster is selected by name (`OCI_CLUSTER_NAME`, default `estate`), never by position;
  * a compartment without that name is BLIND and the row lists what is there;
  * the create-kubeconfig failure line carries the service's own code and message.
"""
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KUBE = ROOT / "bin" / "idp-kube"


def _cloud(tmp: Path, names: list[str]) -> None:
    for i, n in enumerate(names):
        c = tmp / "cloud" / "clusters" / f"ocid1.cluster.{i}.{n}"
        c.mkdir(parents=True)
        (c / "name").write_text(n + "\n")
        (c / "kubeconfig").write_text(f"apiVersion: v1\nkind: Config\ncurrent-context: {n}\n")


def _env(tmp: Path) -> dict:
    fake = tmp / "fakebin"
    fake.mkdir(exist_ok=True)
    k = fake / "kubectl"
    k.write_text('#!/bin/sh\nprintf "KUBECONFIG=%s\\n" "${KUBECONFIG:-unset}"; cat "$KUBECONFIG"\n')
    k.chmod(k.stat().st_mode | stat.S_IEXEC)
    (tmp / "home").mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("KUBECONFIG", "IDP_KUBE", "IDP_CLOUD", "OCI_CLUSTER"))}
    env.update({
        "PATH": f"{fake}:{env.get('PATH', '')}",
        "HOME": str(tmp / "home"),
        "IDP_CLOUD_BACKEND": "file",
        "IDP_CLOUD_FILE_ROOT": str(tmp / "cloud"),
        "IDP_KUBE_STATE": str(tmp / "state"),
    })
    return env


def test_idp_kube_picks_estate_by_name_when_it_is_not_first(tmp_path: Path) -> None:
    _cloud(tmp_path, ["aaa-drill", "estate", "zzz-old"])   # `aaa-drill` sorts first; NR==1 took it
    r = subprocess.run([str(KUBE), "get", "nodes"], env=_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "current-context: estate" in r.stdout, r.stdout
    assert "aaa-drill" not in r.stdout, r.stdout


def test_idp_kube_honours_oci_cluster_name(tmp_path: Path) -> None:
    _cloud(tmp_path, ["estate", "estate-drill"])
    env = _env(tmp_path)
    env["OCI_CLUSTER_NAME"] = "estate-drill"
    r = subprocess.run([str(KUBE), "get", "nodes"], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "current-context: estate-drill" in r.stdout, r.stdout


def test_a_compartment_without_the_named_cluster_is_blind_and_lists_what_is_there(tmp_path: Path) -> None:
    _cloud(tmp_path, ["aaa-drill", "zzz-old"])
    r = subprocess.run([str(KUBE), "get", "nodes"], env=_env(tmp_path), capture_output=True, text=True, timeout=60)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND   kube  no ACTIVE cluster named estate; ACTIVE: aaa-drill,zzz-old" in r.stderr, r.stderr


def test_neither_caller_selects_the_cluster_by_position() -> None:
    for f in (KUBE, ROOT / "bin" / "idp-verify-drill"):
        s = f.read_text()
        assert "NR==1{print $2}" not in s, f"{f.name} still takes the first cluster"
        assert "OCI_CLUSTER_NAME:-estate" in s, f"{f.name} does not select the cluster by name"


def test_the_drill_kube_row_carries_the_service_error_code_and_message(tmp_path: Path) -> None:
    # The same line shape the 19:50Z run cut at `"code": "InvalidP`; the row must carry code and message.
    s = (ROOT / "bin" / "idp-verify-drill").read_text()
    assert '"code": "([^"]+)".*"message": "([^"]+)"' in s
    assert 'create-kubeconfig failed: $(printf \'%s\' "$out" | tail -1 | cut -c1-160)' not in s
