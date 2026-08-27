"""crew#401 CP4, rung 4. A hostname the cluster publishes that the catalogue does not name is a
surface the founder cannot find from the portal. bin/idp-catalogue-drift grades the cluster-state
receipt against backstage/**/catalog-info.yaml. Proved both ways on receipt bodies on disk, plus
BLIND for a receipt that predates the collector change; the collector and the oke-check step are
asserted so the row cannot silently stop running."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "bin" / "idp-catalogue-drift"
ZONE = re.search(r"^\s*ESTATE_ZONE:\s*(\S+)", (ROOT / "clusters/oke/estate-config.yaml").read_text(), re.M).group(1)


def _grade(body: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    f = tmp_path / "receipt"
    f.write_text("ok cluster-state at x nodes=1 ready=1\n" + json.dumps(body) + "\n")
    return subprocess.run([sys.executable, str(ROW), "--receipt", str(f)], capture_output=True, text=True)


def test_an_unregistered_hostname_fails_and_is_named(tmp_path):
    r = _grade({"hostnames": [f"catalogue.{ZONE}", f"nobody-registered-this.{ZONE}"]}, tmp_path)
    assert r.returncode == 1 and r.stdout.startswith("FAIL") and f"nobody-registered-this.{ZONE}" in r.stdout, r.stdout


def test_every_catalogued_hostname_passes(tmp_path):
    r = _grade({"hostnames": [f"catalogue.{ZONE}", f"CATALOGUE.{ZONE}"]}, tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("ok      catalogue-drift  0 unregistered"), r.stdout


def test_a_receipt_without_hostnames_is_blind_never_clean(tmp_path):
    r = _grade({"nodes": []}, tmp_path)
    assert r.returncode == 2 and r.stdout.startswith("BLIND"), r.stdout


def test_the_collector_and_the_workflow_carry_the_row():
    cs = (ROOT / "platform/state/cluster-state.yaml").read_text()
    assert "gateway.networking.k8s.io" in cs and '"httproutes"' in cs, "RBAC must allow listing HTTPRoutes"
    assert '"hostnames": hostnames' in cs, "the receipt body must carry the hostnames list"
    wf = (ROOT / ".github/workflows/oke-check.yml").read_text()
    assert "run: bin/idp-catalogue-drift" in wf, "oke-check must run the row"
