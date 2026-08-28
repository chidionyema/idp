"""Incident 2026-08-26 (crew#345): four sessions were told by this repo's own BLIND lines and
headers to "run oci session authenticate" -- a browser login on a laptop -- when the estate
already publishes its state as receipts (platform/state, bin/idp-cluster-state, oke-check.yml on
the runner's OIDC identity). Rule: no script, workflow or comment in this repo tells a session
to authenticate an OCI session; the one browser login is the founder's tenancy bootstrap
(bin/idp-oci-bootstrap), and every other mention names the receipt path instead. claude-guards#108
refuses the command itself; this test refuses the text that would send a session to it.
Rung 4, incident test."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted(list((ROOT / "bin").glob("idp-oci-*")) + list((ROOT / ".github/workflows").glob("*.yml")))
# The only file allowed to run the login: the tenancy bootstrap, and only the invocation itself.
BOOTSTRAP = ROOT / "bin" / "idp-oci-bootstrap"
ROUTES = re.compile(r"run(?::| the)?\s+(?:`)?oci session authenticate|oci session authenticate first", re.I)
RECEIPT = re.compile(r"idp-cluster-state|oke-check\.yml")


def test_no_file_tells_a_session_to_authenticate_an_oci_session() -> None:
    assert FILES, "nothing scanned"
    bad = []
    for f in FILES:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if ROUTES.search(line):
                bad.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not bad, "\n".join(bad)


def test_every_mention_of_the_login_names_the_receipt_path() -> None:
    for f in FILES:
        text = f.read_text()
        if "oci session authenticate" in text:
            assert RECEIPT.search(text), f"{f.relative_to(ROOT)} mentions the login without naming the receipt path"


def test_the_guard_refuses_the_instance_that_bit() -> None:
    assert ROUTES.search("BLIND   oci-whoami: no $SESSIONS_DIR; run oci session authenticate first")
    assert ROUTES.search('run: oci session authenticate --region <region>')
    assert not ROUTES.search("sessions read state through bin/idp-cluster-state (crew#345), no login")
