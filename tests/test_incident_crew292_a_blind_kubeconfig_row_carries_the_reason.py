"""crew#292: `BLIND kube create-kubeconfig failed: BLIND cloud oci ce cluster create-kubeconfig
failed` is the whole of what 7 of 7 verify-drill runs said about a row that has been blind on
every run since the drill existed. The oci CLI writes a ServiceError naming the code, the target
and the request id; bin/idp-cloud discarded it -- `oci ... || blind "<fixed string>"` keeps the
exit status and nothing else -- and bin/idp-kube then took `tail -1` of the combined output,
which is that fixed string. The cause is destroyed at the boundary and is nowhere in the run log,
so the row cannot be attributed at all, which is what LAW 29 needs before any repair and what
LAW 28 means by an instrument nobody can read.

Rules this file holds:
  1. The reason the CLI gave travels in the blind line.
  2. It stays one line, whatever the CLI printed, because a grading row is one row.
  3. Anything shaped like a token or a key is redacted before it becomes a log line: a
     diagnosis must never be the way a credential escapes (crew#407).
  4. The exit status is still 2, and a success is still silent with the file written.
  5. bin/idp-kube's `tail -1` now lands on a line that carries the cause.

The tool is executed against a fake `oci` on PATH. Nothing here asserts on the text of the source.
"""
import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLOUD = ROOT / "bin/idp-cloud"
KUBE = ROOT / "bin/idp-kube"
# verbatim from an oci CLI ServiceError, the shape the row has never once carried
SERVICE_ERROR = """ServiceError:
{
    "client_version": "Oracle-PythonSDK/2.126.4",
    "code": "NotAuthorizedOrNotFound",
    "message": "Authorization failed or requested resource not found.",
    "operation_name": "create_kubeconfig",
    "status": 404
}"""


def _fake_oci(tmp_path: Path, stderr: str, rc: int, stdout: str = "") -> dict:
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    p = d / "oci"
    p.write_text("#!/bin/sh\ncat <<'E' >&2\n%s\nE\nprintf '%%s' '%s'\nexit %d\n" % (stderr, stdout, rc))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", IDP_CLOUD_BACKEND="oci")
    return env


def _kubeconfig(tmp_path, env):
    return subprocess.run(
        [str(CLOUD), "cluster", "kubeconfig", "ocid1.cluster.oc1.uk-london-1.aaaa",
         "--file", str(tmp_path / "kc")],
        capture_output=True, text=True, check=False, env=env)


def test_the_reason_the_cli_gave_is_in_the_blind_line(tmp_path):
    """Rule 1. This is the sentence 7 runs of verify-drill did not carry."""
    r = _kubeconfig(tmp_path, _fake_oci(tmp_path, SERVICE_ERROR, 1))
    assert r.returncode == 2, r.stderr
    assert "NotAuthorizedOrNotFound" in r.stderr, r.stderr
    assert "create_kubeconfig" in r.stderr and "404" in r.stderr, r.stderr


def test_a_multi_line_diagnosis_still_grades_as_one_row(tmp_path):
    """Rule 2. A receipt reader splits on newlines; a row that spans nine of them is not a row."""
    r = _kubeconfig(tmp_path, _fake_oci(tmp_path, SERVICE_ERROR, 1))
    blind = [ln for ln in r.stderr.splitlines() if ln.startswith("BLIND")]
    assert len(blind) == 1 and len(r.stderr.strip().splitlines()) == 1, r.stderr


@pytest.mark.parametrize("secret", [
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9aaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "ocid1exampleprivatekeyfingerprintaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
])
def test_a_token_shaped_run_of_characters_never_reaches_the_line(tmp_path, secret):
    """Rule 3. A diagnosis is not a licence to print whatever the CLI held (crew#407)."""
    r = _kubeconfig(tmp_path, _fake_oci(tmp_path, f"ServiceError: Authorization: Bearer {secret}", 1))
    assert r.returncode == 2
    assert secret not in r.stderr, r.stderr
    assert "<redacted>" in r.stderr, r.stderr


def test_a_short_word_survives_so_the_redaction_does_not_eat_the_diagnosis(tmp_path):
    """The redaction must not be the new way the cause disappears."""
    r = _kubeconfig(tmp_path, _fake_oci(tmp_path, "ServiceError: code NotAuthorizedOrNotFound status 404", 1))
    assert "NotAuthorizedOrNotFound" in r.stderr and "404" in r.stderr, r.stderr


def test_the_line_is_capped_so_a_runaway_cli_cannot_flood_the_receipt(tmp_path):
    """8000 characters of CLI noise becomes 300 of them, behind the row's own fixed prefix."""
    noisy = "x " * 4000
    r = _kubeconfig(tmp_path, _fake_oci(tmp_path, noisy, 1))
    prefix = "BLIND   cloud  oci ce cluster create-kubeconfig failed: "
    line = r.stderr.strip()
    assert r.returncode == 2 and line.startswith(prefix), line[:80]
    assert len(line) - len(prefix) <= 300 < len(noisy), len(line)


def test_a_failed_call_that_also_printed_to_stdout_leaks_none_of_it(tmp_path):
    """Rule 3, on the path that actually risks it. `create-kubeconfig` writes to --file, but a
    partial run can still put a token-bearing document on stdout, and a failing call is exactly
    when the blind line is built. Only stderr is captured, so stdout cannot reach the row at all."""
    # short words on purpose: a payload the redaction cannot rescue, so the test grades the
    # capture and not the sed. Redacting a leak is a second line of defence, never the first.
    on_stdout = "apiVersion v1 kind Config user exec token FROM STDOUT"
    env = _fake_oci(tmp_path, "ServiceError: code NotAuthorizedOrNotFound", 1, stdout=on_stdout)
    r = _kubeconfig(tmp_path, env)
    assert r.returncode == 2
    assert "FROM STDOUT" not in r.stderr and "kind Config" not in r.stderr, r.stderr
    assert "NotAuthorizedOrNotFound" in r.stderr, r.stderr


def test_a_success_is_silent_and_writes_the_file(tmp_path):
    """Rule 4. The kubeconfig goes to --file; stdout is discarded so a token cannot reach a log."""
    env = _fake_oci(tmp_path, "", 0, stdout="apiVersion: v1  # would be a token-bearing config")
    (tmp_path / "kc").write_text("apiVersion: v1\n")
    r = _kubeconfig(tmp_path, env)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "" and r.stderr == "", (r.stdout, r.stderr)


def test_idp_kube_tail_one_now_lands_on_the_cause(tmp_path):
    """Rule 5. bin/idp-kube keeps only the last line of the combined output; that line has to be
    the one carrying the reason, or this fix stops at the boundary it was written to cross."""
    env = _fake_oci(tmp_path, SERVICE_ERROR, 1)
    r = _kubeconfig(tmp_path, env)
    last = r.stderr.strip().splitlines()[-1]
    assert "NotAuthorizedOrNotFound" in last, last
    assert "tail -1" in KUBE.read_text(), "the boundary this test is about still slices that way"
