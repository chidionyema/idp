"""One-hop institutional recovery is executable, not a narrative."""
import json
import subprocess
import sys
from pathlib import Path
import pytest
from legion.failure_atlas import ATLAS, load_atlas, diagnose
ROOT=Path(__file__).resolve().parents[1]

def test_429_dual_exhaustion_is_not_blind_retry():
    x=diagnose("LEGION_RATE_BOTH")
    assert x["known"] and x["cooldown_s"]>=300
    assert x["max_identical_attempts"]<=2
    assert "capacity" in x["recovery"].lower()
    assert "effect" in x["proof"].lower()

def test_unknown_failure_preserves_fingerprint_and_quarantines():
    x=diagnose("NEW_PROVIDER_FAILURE")
    assert not x["known"]
    assert x["id"]=="LEGION_UNKNOWN"
    assert x["requested_fingerprint"]=="NEW_PROVIDER_FAILURE"
    assert "Quarantine" in x["recovery"]

def test_all_failure_classes_have_effect_proofs_and_bounded_recovery():
    records=load_atlas()["modes"]
    assert len(records)>=10
    for r in records:
        assert r["diagnosis"] and r["recovery"] and r["proof"]
        assert 1<=r["max_identical_attempts"]<=2
        assert "debug" not in r["recovery"].lower()

def test_missing_recovery_or_duplicate_id_fail_admission(tmp_path):
    broken=json.loads(ATLAS.read_text())
    broken["modes"][0].pop("recovery")
    p=tmp_path/"faults.json";p.write_text(json.dumps(broken))
    with pytest.raises(ValueError):
        load_atlas(p)
    duplicated=json.loads(ATLAS.read_text())
    duplicated["modes"].append(dict(duplicated["modes"][0]))
    p.write_text(json.dumps(duplicated))
    with pytest.raises(ValueError):
        load_atlas(p)

def test_cli_one_hop_known_and_unknown():
    for code,exitcode in [("LEGION_RATE_BOTH",0),("UNMAPPED_CLASS",2)]:
        r=subprocess.run([sys.executable,"-m","legion","diagnose",code,"--json"],
            cwd=ROOT,capture_output=True,text=True,timeout=10)
        assert r.returncode==exitcode,r.stderr
        x=json.loads(r.stdout)
        assert x["status"]=="RECOVERY_REQUIRED"
        assert x["proof"] and x["recovery"]

def test_memory_is_not_a_deployment_receipt():
    assert all("OPERATIONAL"!=x.get("status") for x in load_atlas()["modes"])
