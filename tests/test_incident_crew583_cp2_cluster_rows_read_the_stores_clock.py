"""crew#583 CP2: bin/idp-cluster-state and bin/idp-telemetry-coverage graded a receipt's age by
subtracting this machine's clock from the store's `last-modified`. Under a clock behind the store
(a flat battery resets the Mac RTC; the 1970 stamps of 2026-08-27) the age went negative and the
row read ok however dead the CronJob was. Each row now asks the store for both clocks and refuses
a head that brings only one. Both scripts are driven for real, through the idp-cloud shim."""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROWS = {
    "bin/idp-cluster-state": ("cluster-state", "CLUSTER_STATE_MAX_AGE_MIN",
                              "ok cluster-state at 2026-08-29T02:00:03Z nodes=1 ready=1 pods=3 pods_not_ready=0 flux=1 "
                              "flux_not_ready=0 ds=1 ds_short=0 events_warning=0 monitoring_rules=3 alert_watchdog=1 cpu_used_pct=30 mem_used_pct=25 "
                              "cpu_req_pct=12 mem_req_pct=4\n{\"capacity\": [], \"capacity_error\": \"\"}\n"),
    "bin/idp-telemetry-coverage": ("telemetry-coverage", "TELEMETRY_COVERAGE_MAX_AGE_MIN",
                                   "ok telemetry-coverage pods=2 seen=2 missing=0 hubble_radio_flows=7\n"),
}


def _run(tmp_path, script, head, body):
    idp = tmp_path / "idp"; (idp / "bin").mkdir(parents=True)
    shutil.copytree(ROOT / "bin" / "lib", idp / "bin" / "lib")
    shutil.copy(ROOT / script, idp / script)
    shim = idp / "bin" / "idp-cloud"
    shim.write_text("#!/bin/sh\ncase \"$*\" in\n  *\"object head\"*) printf '%s' '" + json.dumps(head)
                    + "';;\n  *\"object get\"*) printf '%s' '" + body + "';;\nesac\n")
    shim.chmod(0o755)
    row, max_var, _ = ROWS[script]
    env = {**os.environ, max_var: "30"}
    return subprocess.run([str(idp / script)], capture_output=True, text=True, env=env)


@pytest.mark.parametrize("script", sorted(ROWS))
def test_a_receipt_stamped_ahead_of_the_stores_clock_is_never_ok(tmp_path, script):
    """The one-sided bound: last-modified 400 days after the store's own date. Before CP2 this
    machine's clock decided the sign and the row read ok."""
    head = {"last-modified": "Sat, 03 Oct 2027 12:00:00 GMT", "date": "Sat, 29 Aug 2026 12:00:00 GMT"}
    r = _run(tmp_path, script, head, ROWS[script][2])
    assert r.returncode == 2 and r.stdout.startswith("BLIND"), r.stdout + r.stderr


@pytest.mark.parametrize("script", sorted(ROWS))
def test_a_head_with_no_store_clock_is_blind_not_measured_locally(tmp_path, script):
    head = {"last-modified": "Sat, 29 Aug 2026 12:00:00 GMT"}
    r = _run(tmp_path, script, head, ROWS[script][2])
    assert r.returncode == 2 and "no date header" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize("script", sorted(ROWS))
def test_a_fresh_receipt_by_the_stores_clock_is_ok_whatever_this_machine_says(tmp_path, script):
    """Both stamps sit in 2019, far behind this machine: the row is still ok because this machine
    was never asked."""
    head = {"last-modified": "Tue, 01 Jan 2019 12:00:00 GMT", "date": "Tue, 01 Jan 2019 12:05:00 GMT"}
    r = _run(tmp_path, script, head, ROWS[script][2])
    assert r.returncode == 0 and r.stdout.startswith("ok"), r.stdout + r.stderr
