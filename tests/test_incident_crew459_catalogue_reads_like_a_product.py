"""Incident, crew#459 (founder, 2026-08-29: "assume an investor and buyer is coming to view our
backstage ... every single detail needs to be 100x better"). Measured that morning in the served
catalog/catalog-info.yaml: 527 lines carried /Users/<account>/..., 8 titles were launchd labels
(ai.aiden.watch), and Adobe's CCXProcess was an estate Resource. Rung 4, proved both ways on a
fixture inventory through the real generator."""
import json
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"


def _generate(tmp_path, rows):
    base = json.loads((ROOT / "tests" / "fixtures" / "inventory.json").read_text())
    inv = tmp_path / "inventory.json"
    inv.write_text(json.dumps({**base, "rows": base["rows"] + rows}))
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run([sys.executable, str(GEN)], env={**os.environ, "INV": str(inv), "OUT": str(out),
                                                        "ESTATE_ENV": "dev", "CATALOG_GEN_ROOT": str(ROOT)},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    text = (out / "catalog-info.yaml").read_text()
    return text, {d["metadata"]["name"]: d for d in yaml.safe_load_all(text) if d}


ROWS = [
    {"kind": "scheduled_job", "id": "ai.aiden.watch", "root": "x", "path": "/Users/someone/work/x/watch.py",
     "what": "One tick of Aiden.", "loaded": True, "last_status": "clean", "interval_s": 60},
    {"kind": "scheduled_job", "id": "com.adobe.ccxprocess", "root": "x",
     "path": "/Applications/Utilities/Adobe Creative Cloud Experience/CCXProcess/CCXProcess.app/Contents/MacOS/CCXProcess",
     "loaded": False, "last_status": "not loaded"},
    {"kind": "ledger", "id": "receipts", "root": "x", "path": "/Users/other/.estate/receipts.jsonl", "rows": 3},
]


def test_incident_no_home_directory_no_label_titles_no_vendor_software(tmp_path):
    text, by = _generate(tmp_path, ROWS)
    assert "/Users/" not in text and "/home/" not in text, [l for l in text.splitlines() if "/Users/" in l or "/home/" in l][:3]
    assert "~/work/x/watch.py" in text and "~/.estate/receipts.jsonl" in text
    job = by["ai.aiden.watch"]
    assert job["metadata"]["title"] == "Aiden watch"
    assert job["metadata"]["annotations"]["estate/label"] == "ai.aiden.watch"
    assert "com.adobe.ccxprocess" not in by and "CCXProcess" not in text


def test_the_other_way_a_plain_id_keeps_its_title_and_an_estate_job_is_still_written(tmp_path):
    text, by = _generate(tmp_path, [
        {"kind": "scheduled_job", "id": "nightly-backup", "root": "x", "path": "/opt/estate/backup.sh",
         "what": "Copies the ledgers offsite every night.", "loaded": True, "last_status": "clean"}])
    assert by["nightly-backup"]["metadata"]["title"] == "nightly-backup"
    assert "estate/label" not in by["nightly-backup"]["metadata"].get("annotations", {})
    assert "/opt/estate/backup.sh" in text
