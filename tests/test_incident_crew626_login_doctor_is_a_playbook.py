"""crew#626 CP15: the Langfuse SSO click returns error=OAuthCallback and no playbook could read a
healthy pod's log. `login-doctor` is the read-only playbook that prints the callback lines, the
secret sync state and the identity endpoint from the cluster.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "oke-check.yml"


def test_login_doctor_is_listed_and_dispatchable():
    out = subprocess.run(
        [str(ROOT / "bin" / "idp-oke-break-glass"), "--list"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "login-doctor" in out.split()
    assert "login-doctor" in WF.read_text()


def test_login_doctor_reads_state_never_a_secret_value():
    src = (ROOT / "bin" / "idp-oke-break-glass").read_text()
    body = src.split("pb_login_doctor() {")[1].split("\n}\n")[0]
    assert "show_redacted langfuse-web-log-callback" in body
    assert "jsonpath='{.data}'" in body and "sed -E 's/:.*//'" in body
