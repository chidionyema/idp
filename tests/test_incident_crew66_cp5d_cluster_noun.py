"""crew#66 CP5d: bin/idp-cloud grows a `cluster` noun (list, nodepools, kubeconfig); the three OKE
callers (bin/idp-verify-drill, bin/idp-oke-rebuild, bin/idp-flux-bootstrap) move off `oci ce` and
read through the layer. Rung 4, incident test, both ways: a one-cluster, two-ACTIVE-pool layer
response makes the cluster row an ok; a layer exit 2 makes the row a BLIND that names why; a UPDATING
pool is a resize in flight: ok, naming the pool (idp#507 / crew#539 CP4, the same verdict
bin/idp-oke-rebuild gives; a DELETING pool stays FAIL and is named — see
test_incident_crew516_verify_drill_cluster_row_tolerates_resize.py). The script-side gate is "no `oci ce`
outside a comment" (the cp5b test uses the same comment-excluding pattern)."""
import base64
import json
import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-verify-drill"


# ------------------------------------------------------------------------- fake idp-cloud on PATH

def _fake(b: Path, name: str, body: str) -> None:
    f = b / name
    f.write_text("#!/usr/bin/env bash\n" + body)
    f.chmod(f.stat().st_mode | stat.S_IEXEC)


# ------------------------------------------------------------------------- helpers shared with crew484

def _bin(tmp: Path) -> Path:
    """Build a fake checkout rooted at tmp with a script and the fakes it needs.

    The script computes $IDP via `$(cd "$(dirname "$0")/.." && pwd)`, so the fake idp-cloud is a
    sibling of the copied script under tmp/bin; the kubectl and idp-cluster-state fakes live there
    too, and the receipt row uses idp-cluster-state."""
    b = tmp / "bin"
    b.mkdir()
    return b


def _token(tmp: Path) -> None:
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


# ------------------------------------------------------------------------- runtime cases

def test_a_one_cluster_two_active_pools_is_an_ok_row(tmp_path: Path) -> None:
    """A fake idp-cloud that prints one ACTIVE cluster and two ACTIVE pools drives the cluster row
    to '1 cluster ACTIVE, 2/2 node pool(s) ACTIVE'."""
    b = _bin(tmp_path)
    _fake(b, "oci", '''
        case "$*" in
          *"iam user get"*) echo estate-ci;;
          *"create-kubeconfig"*) f=""; while [ $# -gt 0 ]; do [ "$1" = --file ] && f="$2"; shift; done; echo fake > "$f";;
        esac
    ''')
    _fake(b, "kubectl", "echo '{\"items\":[{\"metadata\":{\"resourceVersion\":\"7\"},\"status\":{\"conditions\":[{\"type\":\"Ready\",\"status\":\"True\"}]}}]}'")
    _fake(b, "idp-cluster-state", "echo 'ok      cluster-state nodes=1 ready=1 (3 min ago)'")
    _fake(b, "idp-drills-row", "echo 'ok        drills    login-drill  login-drill.yml last green 1.0h ago (max 26h)'")
    _fake(b, "idp-no-toil", "echo 'PASS    no-toil gate (2 document(s))'")  # crew#66 hourly row
    _fake(b, "idp-github-app", "echo 'ok      github-tokens 2 token(s) re-minted from the App'")  # crew#577 hourly token row
    _fake(b, "idp-root-trust", "echo 'PASS    root-trust: every entry registered, every MEETS row has its bootstrapper'")  # crew#66 root-trust row (crew#580)
    # the layer: one cluster, two ACTIVE pools, kubeconfig write
    _fake(b, "idp-cloud", '''
        case "$1 $2" in
          "cluster list") echo "oke ocid1.cluster.fake.abc";;
          "cluster nodepools") printf "pool-a ACTIVE\\npool-b ACTIVE\\n";;
          "cluster kubeconfig") f=""; shift 2; while [ $# -gt 0 ]; do [ "$1" = --file ] && f="$2"; shift; done; echo fake > "$f";;
        esac
    ''')
    (b / "idp-verify-drill").write_text(SCRIPT.read_text())
    (b / "idp-verify-drill").chmod(0o755)
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "ok      cluster      1 cluster ACTIVE, 2/2 node pool(s) ACTIVE" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0 and "8/8 rows green" in r.stdout


def test_a_updating_pool_keeps_the_cluster_row_ok_and_names_it(tmp_path: Path) -> None:
    """One pool ACTIVE, one UPDATING -> the row grades ok and names the resizing pool: the
    autoscaler resizing a pool is the platform working, not a red row (idp#507, crew#539 CP4).
    Until idp#548 this case asserted FAIL, and every verify-drill.yml run on 2026-08-28 was red
    on it while a1-spot resized (crew#516 CP1)."""
    b = _bin(tmp_path)
    _fake(b, "oci", '''
        case "$*" in
          *"iam user get"*) echo estate-ci;;
        esac
    ''')
    _fake(b, "kubectl", "echo '{\"items\":[]}'")
    _fake(b, "idp-cluster-state", "echo 'ok      cluster-state nodes=0 ready=0 (3 min ago)'")
    _fake(b, "idp-drills-row", "echo 'ok        drills    login-drill  login-drill.yml last green 1.0h ago (max 26h)'")
    _fake(b, "idp-no-toil", "echo 'PASS    no-toil gate (2 document(s))'")  # crew#66 hourly row
    _fake(b, "idp-github-app", "echo 'ok      github-tokens 2 token(s) re-minted from the App'")  # crew#577 hourly token row
    _fake(b, "idp-root-trust", "echo 'PASS    root-trust: every entry registered, every MEETS row has its bootstrapper'")  # crew#66 root-trust row (crew#580)
    _fake(b, "idp-cloud", '''
        case "$1 $2" in
          "cluster list") echo "oke ocid1.cluster.fake.abc";;
          "cluster nodepools") printf "pool-a ACTIVE\\npool-b UPDATING\\n";;
          "cluster kubeconfig") f=""; shift 2; while [ $# -gt 0 ]; do [ "$1" = --file ] && f="$2"; shift; done; echo fake > "$f";;
        esac
    ''')
    (b / "idp-verify-drill").write_text(SCRIPT.read_text())
    (b / "idp-verify-drill").chmod(0o755)
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "ok      cluster      1 cluster ACTIVE, 1/2 node pool(s) ACTIVE, UPDATING (resize in flight): pool-b" in r.stdout, r.stdout + r.stderr
    assert "FAIL    cluster" not in r.stdout


def test_a_layer_exit_2_on_cluster_list_makes_the_row_blind(tmp_path: Path) -> None:
    """The layer exits 2 with a message on stderr; verify-drill must call bl cluster with the
    message, not propagate the exit code or treat the empty answer as success."""
    b = _bin(tmp_path)
    _fake(b, "oci", '''
        case "$*" in
          *"iam user get"*) echo estate-ci;;
        esac
    ''')
    _fake(b, "kubectl", "echo '{}'")
    _fake(b, "idp-cluster-state", "echo 'ok      cluster-state nodes=0 ready=0 (3 min ago)'")
    _fake(b, "idp-drills-row", "echo 'ok        drills    login-drill  login-drill.yml last green 1.0h ago (max 26h)'")
    _fake(b, "idp-no-toil", "echo 'PASS    no-toil gate (2 document(s))'")  # crew#66 hourly row
    _fake(b, "idp-github-app", "echo 'ok      github-tokens 2 token(s) re-minted from the App'")  # crew#577 hourly token row
    _fake(b, "idp-root-trust", "echo 'PASS    root-trust: every entry registered, every MEETS row has its bootstrapper'")  # crew#66 root-trust row (crew#580)
    _fake(b, "idp-cloud", '''
        case "$1 $2" in
          "cluster list") echo "compartment unreadable" >&2; exit 2;;
        esac
    ''')
    (b / "idp-verify-drill").write_text(SCRIPT.read_text())
    (b / "idp-verify-drill").chmod(0o755)
    _token(tmp_path)
    r = _run(tmp_path, b)
    assert "BLIND   cluster      cluster list failed: compartment unreadable" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 2


# ------------------------------------------------------------------------- static checks

def test_no_oci_ce_outside_comments_in_the_three_callers() -> None:
    r"""crew#66 CP5d: every `oci ce ...` call in the three OKE callers must move into the layer.
    Comments are not counted (the cp5b test uses the same `^\s*[^#]*\b` shape: only the exec-plugin
    comment in verify-drill mentions `oci ce`, and the plan says leave it)."""
    for script in ("bin/idp-verify-drill", "bin/idp-oke-rebuild", "bin/idp-flux-bootstrap"):
        text = (ROOT / script).read_text()
        offenders = [line for line in text.splitlines() if not line.lstrip().startswith("#") and "oci ce" in line]
        assert offenders == [], f"{script} still names `oci ce` outside a comment: {offenders}"


def test_verify_drill_calls_idp_cloud_for_each_cluster_verb() -> None:
    """The plan pins the layer calls literally so a refactor of bin/idp-verify-drill cannot quietly
    re-introduce the OCI CLI. Same `oci ce` comment rule applies."""
    text = SCRIPT.read_text()
    assert '"$IDP/bin/idp-cloud" cluster list' in text
    assert '"$IDP/bin/idp-cloud" cluster nodepools' in text
    assert '"$IDP/bin/idp-cloud" cluster kubeconfig "$cid" --file "$kc"' in text


def test_flux_bootstrap_calls_idp_cloud_for_the_kubeconfig() -> None:
    text = (ROOT / "bin" / "idp-flux-bootstrap").read_text()
    assert '"$IDP/bin/idp-cloud" cluster kubeconfig "$CLUSTER" --file "$KUBECONFIG"' in text
    # the chmod 600 line is kept
    assert 'chmod 600 "$KUBECONFIG"' in text


def test_oke_rebuild_nodes_oci_grades_with_awk_through_the_layer() -> None:
    """The no-kube path now reads node pools via the layer and grades them with awk: no rows ->
    'no node pools', a non-ACTIVE row -> 'node pools not ACTIVE: <names>', all ACTIVE -> '<n> node
    pool(s) ACTIVE (cloud layer)'."""
    text = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    assert '"$IDP/bin/idp-cloud" cluster nodepools' in text
    # idp#507 (crew#539 CP4): the grade names the state and waives UPDATING; still awk, still through the layer
    assert 'awk \'$2!="ACTIVE" && $2!="UPDATING"{print $1"("$2")"}\'' in text
    assert "cloud layer" in text
    assert "(OCI API)" not in text.split("nodes_oci")[1].split("}", 1)[1]   # the old jq-bracket message is gone
