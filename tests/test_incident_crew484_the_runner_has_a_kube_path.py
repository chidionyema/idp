"""crew#484: no CI job in idp had a kube path; every drill graded a receipt or an endpoint instead
of asking the API server. bin/idp-verify-drill now mints a kubeconfig from the exchanged session
(the same identity its identity row proves) and reads the nodes through it. Rung 4, both ways:
a Ready node is an ok row; a 403 is a BLIND row naming the IAM gap; a NotReady node is red."""
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-verify-drill"
CLUSTER = '[{"n": "oke", "id": "ocid1.cluster.fake.abc"}]'
POOLS = '[{"n": "pool", "s": "ACTIVE"}]'


def _node(ready: str, rv: str = "7") -> str:
    return json.dumps({"items": [{"metadata": {"resourceVersion": rv},
                                  "status": {"conditions": [{"type": "Ready", "status": ready}]}}]})


def _bin(tmp: Path, nodes_out: str, nodes_rc: int = 0) -> Path:
    b = tmp / "bin"
    b.mkdir()
    (tmp / "nodes.json").write_text(nodes_out)
    # crew#66 CP5d: cluster list / node-pool list / create-kubeconfig now sit inside bin/idp-cloud's
    # `cluster` noun. The script calls the layer; the fake layer forwards the kubeconfig mint to the
    # fake oci so the kc-args check still pins the crew#484 invariants (same identity, no secret).
    (b / "oci").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *"iam user get"*) echo estate-ci;;\n'
        '  *"create-kubeconfig"*) echo "$*" >> "$TMPDIR/kc-args"; f=""; while [ $# -gt 0 ]; do [ "$1" = --file ] && f="$2"; shift; done; echo fake > "$f";;\n'
        "esac\n"
    )
    (b / "idp-cloud").write_text(
        "#!/bin/sh\n"
        'case "$1 $2" in\n'
        '  "cluster list") echo "oke ocid1.cluster.fake.abc";;\n'
        '  "cluster nodepools") echo "pool ACTIVE";;\n'
        '  "cluster kubeconfig") shift 2; cid=""; f=""; while [ $# -gt 0 ]; do case "$1" in --file) f="$2"; shift 2;; *) cid="$1"; shift;; esac; done; oci ce cluster create-kubeconfig --cluster-id "$cid" --file "$f" --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT;;\n'
        "esac\n"
    )
    (b / "kubectl").write_text(f"#!/bin/sh\ncat '{tmp}/nodes.json'; exit {nodes_rc}\n")
    (b / "idp-cluster-state").write_text("#!/bin/sh\necho 'ok      cluster-state nodes=1 ready=1 (3 min ago)'\n")
    (b / "idp-drills-row").write_text("#!/bin/sh\necho 'ok        drills    login-drill  login-drill.yml last green 1.0h ago (max 26h)'\n")
    (b / "idp-no-toil").write_text("#!/bin/sh\necho 'PASS    no-toil gate (2 document(s))'\n")  # crew#66 hourly row
    (b / "idp-github-app").write_text("#!/bin/sh\necho 'ok      github-tokens 2 token(s) re-minted from the App'\n")  # crew#577 hourly token row
    (b / "idp-root-trust").write_text("#!/bin/sh\necho 'PASS    root-trust: every entry registered, every MEETS row has its bootstrapper'\n")  # crew#66 root-trust row (crew#580)
    for f in b.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    # the script reads idp-cluster-state beside itself: run a copy of the script from the fake bin
    (b / "idp-verify-drill").write_text(SCRIPT.read_text())
    (b / "idp-verify-drill").chmod(0o755)
    return b


def _token(tmp: Path) -> None:
    import base64
    seg = base64.urlsafe_b64encode(json.dumps({"sub": "ocid1.user.fake", "ttype": "te", "iat": 0, "exp": 3540}).encode()).decode().rstrip("=")
    (tmp / "tok").write_text(f"h.{seg}.s")
    (tmp / "config").write_text(f"[DEFAULT]\nsecurity_token_file={tmp}/tok\n")


def _run(tmp: Path, b: Path) -> subprocess.CompletedProcess:
    env = {
        "PATH": f"{b}:/usr/bin:/bin", "TMPDIR": str(tmp), "HOME": str(tmp),
        "OCI_CLI_AUTH": "security_token",
        "OCI_CLI_CONFIG_FILE": str(tmp / "config"), "KUBECONFIG_OUT": str(tmp / "kc"),
    }
    return subprocess.run([str(b / "idp-verify-drill")], env=env, capture_output=True, text=True, timeout=60)


def test_a_ready_node_read_through_the_api_server_is_an_ok_row(tmp_path: Path) -> None:
    b = _bin(tmp_path, _node("True"))
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "ok      kube         1/1 node(s) Ready through the API server" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0 and "8/8 rows green" in r.stdout
    args = (tmp_path / "kc-args").read_text()
    assert "--token-version 2.0.0" in args and "--cluster-id ocid1.cluster.fake.abc" in args   # the exec plugin, not a static token
    assert not (tmp_path / "kc").exists(), "the kubeconfig outlived the run"


def test_a_healthy_node_whose_json_contains_403_is_still_ok(tmp_path: Path) -> None:
    """idp#447 review: the verdict is kubectl's exit code, never a number found in the body."""
    b = _bin(tmp_path, _node("True", rv="12403"))
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "ok      kube         1/1 node(s) Ready" in r.stdout, r.stdout
    assert "refused" not in r.stdout and r.returncode == 0


def test_a_failed_read_that_is_not_a_refusal_is_blind_without_the_iam_text(tmp_path: Path) -> None:
    b = _bin(tmp_path, "Unable to connect to the server: dial tcp: i/o timeout", nodes_rc=1)
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "BLIND   kube         kubectl get nodes failed" in r.stdout, r.stdout
    assert "IAM" not in r.stdout and r.returncode == 2


def test_a_refused_read_is_a_blind_row_that_names_the_iam_gap(tmp_path: Path) -> None:
    b = _bin(tmp_path, 'Error from server (Forbidden): nodes is forbidden: User "estate-ci" cannot list resource "nodes"', nodes_rc=1)
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "BLIND   kube         API server refused estate-ci" in r.stdout, r.stdout
    assert "use clusters" in r.stdout and "ClusterRoleBinding" in r.stdout
    assert r.returncode == 2


def test_a_notready_node_is_a_red_row(tmp_path: Path) -> None:
    b = _bin(tmp_path, _node("False"))
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "FAIL    kube         0/1 node(s) Ready" in r.stdout, r.stdout
    assert r.returncode == 1


def test_the_kube_row_lives_on_the_scheduled_drill_with_no_second_credential() -> None:
    script = SCRIPT.read_text()
    # crew#66 CP5d: the kubeconfig is minted through bin/idp-cloud's `cluster kubeconfig` noun;
    # the layer still calls `oci ce cluster create-kubeconfig --token-version 2.0.0` (the exec
    # plugin the kubeconfig carries is unchanged: same identity, no static token).
    assert '"$IDP/bin/idp-cloud" cluster kubeconfig' in script
    assert "kubectl get nodes" in script
    wf = (ROOT / ".github" / "workflows" / "verify-drill.yml").read_text()
    assert "KUBECONFIG" not in wf or "secrets." not in wf.split("KUBECONFIG")[1][:200], "a kubeconfig secret beside the exchanged session"
    assert os.access(SCRIPT, os.X_OK)
