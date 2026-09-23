"""crew#631 CP2: the verdict signing key is readable by the prover identity only.

Incident class (crew#631): an agent that can read the signing key can sign its own verdict, and
the verification plane proves nothing. The laptop and the cluster nodes act as estate-operators
and the workers dynamic group; both grants now exclude `verdict-hmac-key` by name (a vendor policy
variable, docs.oracle.com keypolicyreference: target.secret.name). The prover group estate-provers
holds estate-ci and reads that one secret. Driven both ways through the drift grader with a fake
`oci`: a live compartment line carrying the where clause is a match, and the old unscoped line is
drift, so a widening back to every secret is red.
"""

import json
import os
import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / "platform" / "oci" / "policy" / "estate-operators.statements.json"
GUARD = ROOT / "bin" / "idp-iam-policy-drift"
COMP = "ocid1.compartment.oc1..test"
SCOPED = "Allow group estate-operators to manage secret-family in compartment estate where target.secret.name != 'verdict-hmac-key'"


def _run(tmp: Path, live, comp) -> subprocess.CompletedProcess:
    b = tmp / "bin"
    b.mkdir(exist_ok=True)
    fake = b / "oci"
    (b / "comp.json").write_text(json.dumps(comp))
    (b / "live.json").write_text(json.dumps(live))
    fake.write_text(
        '#!/usr/bin/env bash\ncase "$*" in '
        f"*\"--name estate-operators-compartment\"*) cat '{b / 'comp.json'}'; exit 0;; "
        f"*\"iam policy list\"*) cat '{b / 'live.json'}'; exit 0;; "
        "*) echo unexpected >&2; exit 9;; esac\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "OCI_TENANCY_OCID": "ocid1.tenancy.oc1..test",
        "OCI_COMPARTMENT_OCID": COMP,
    }
    return subprocess.run(["bash", str(GUARD)], env=env, capture_output=True, text=True)


def _compartment_lines(statements):
    return [
        s.replace(" in compartment estate", f" in compartment id {COMP}")
        for s in statements
        if re.search(r" in compartment estate( where .*)?$", s)
    ]


def test_operators_and_workers_are_refused_the_signing_key_by_name() -> None:
    statements = json.loads(JSON.read_text())
    assert SCOPED in statements
    assert not any(
        s.endswith("manage secret-family in compartment estate") for s in statements
    )
    vault = (ROOT / "platform/oci/vault.tf").read_text()
    assert (
        "read secret-family in compartment id ${var.compartment_ocid} where target.secret.name != 'verdict-hmac-key'"
        in vault
    )


def test_the_prover_group_reads_that_one_secret_and_waits_for_the_bootstrap() -> None:
    tf = (ROOT / "platform/oci/provers.tf").read_text()
    assert (
        "Allow group estate-provers to read secret-family in compartment id ${var.compartment_ocid} where target.secret.name = 'verdict-hmac-key'"
        in tf
    )
    assert (
        "count          = length(data.oci_identity_groups.provers.groups) > 0 ? 1 : 0"
        in tf
    )
    boot = (ROOT / "bin/idp-oci-bootstrap").read_text()
    assert (
        "ensure group estate-provers" in boot
        and 'displayName eq "estate-provers"' in boot
    )
    assert (
        'can(regex(" in compartment estate( where .*)?$", s))'
        in (ROOT / "platform/oci/iam.tf").read_text()
    )


def test_drift_grader_matches_the_scoped_line_and_refuses_the_unscoped_one(
    tmp_path: Path,
) -> None:
    want = json.loads(JSON.read_text())
    tenancy = [s for s in want if s not in (SCOPED,)]  # the tenancy copy predates CP2
    ok = _run(tmp_path, tenancy, comp=_compartment_lines(want))
    assert ok.returncode == 0 and ok.stdout.startswith("ok      iam-policy"), (
        ok.stdout + ok.stderr
    )
    widened = [s.split(" where ")[0] if s == SCOPED else s for s in want]
    bad = _run(tmp_path, tenancy, comp=_compartment_lines(widened))
    assert (
        bad.returncode == 1
        and "verdict-hmac-key" in bad.stdout
        and "missing" in bad.stdout
    ), bad.stdout
