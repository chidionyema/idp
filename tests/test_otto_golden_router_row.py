"""Otto (otto-golden) gets its router credential the same way every consumer does: a row in
the seed's router plan, minted by bin/idp-router-key into vault entry otto-golden, read by an
ExternalSecret and mounted into the deployment. Before this row the pod had no key at all:
its router client raised EgressDenied on every call and the workload had never answered a
single message. This spec runs the seed's preflight (with a fake vault writer, no network)
and asserts the plan the seed itself announces; then it parses the ExternalSecret and the
deployment and asserts the two sides name the same vault entry and field.
"""

import os
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "bin" / "idp-estate-seed"
ES = ROOT / "platform" / "otto-golden" / "router-key.yaml"
DEPLOY = ROOT / "platform" / "otto-golden" / "deployment.yaml"

ENTRY = "otto-golden"
FIELD = "LITELLM_API_KEY"


def _preflight_rows(tmp_path: Path) -> dict:
    """Run the seed's preflight with a fake vault writer; return {entry: detail}."""
    fake = tmp_path / "idp-vault-put"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "IDP_VAULT_PUT": str(fake)}
    p = subprocess.run(  # noqa: S603
        [str(SEED), "--preflight"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=120,
    )
    assert p.returncode == 0, p.stdout + p.stderr  # noqa: S101
    rows = {}
    for line in p.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0] == "":
            continue
        if len(parts) >= 2 and not line.startswith(("ok", "FAIL", "BLIND")):
            entry = line.split()[0]
            rows[entry] = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
    return rows


def test_seed_preflight_announces_the_otto_golden_router_key(tmp_path):
    rows = _preflight_rows(tmp_path)
    assert ENTRY in rows, sorted(rows)  # noqa: S101
    detail = rows[ENTRY]
    assert FIELD in detail and "router key" in detail, detail  # noqa: S101
    assert "kimi" in detail, detail  # noqa: S101


def test_external_secret_and_deployment_agree_on_entry_and_field():
    es = yaml.safe_load(ES.read_text())
    data = es["spec"]["data"]
    refs = [(d["remoteRef"]["key"], d["remoteRef"]["property"]) for d in data]
    assert (ENTRY, FIELD) in refs, refs  # noqa: S101

    secret_name = es["spec"]["target"]["name"]
    docs = [d for d in yaml.safe_load_all(DEPLOY.read_text()) if d]
    deploy = next(d for d in docs if d.get("kind") == "Deployment")
    pod = deploy["spec"]["template"]["spec"]
    vols = {
        v["name"]: v["secret"]["secretName"] for v in pod["volumes"] if "secret" in v
    }
    assert secret_name in vols.values(), vols  # noqa: S101
