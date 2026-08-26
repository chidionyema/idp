"""crew#340: for two days bin/langfuse-verify said "span accepted but never appeared" while the
cause was three failed Langfuse v4 background migrations (events_full cutover). The probe now
reads background_migrations first and names a failed row. Rung 4, incident test, proved both
ways through a docker shim: a failed row -> FAIL naming it; no row -> PASS."""
import os
import pathlib
import stat
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFY = ROOT / "bin" / "langfuse-verify"


def _run(tmp_path, psql_output):
    shim = tmp_path / "docker"
    shim.write_text("#!/bin/sh\nprintf '%s' \"$FAKE_PSQL\"\n")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
    envf = tmp_path / ".env"
    envf.write_text("LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk\nLANGFUSE_INIT_PROJECT_SECRET_KEY=sk\n")
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", FAKE_PSQL=psql_output, LANGFUSE_ENV_FILE=str(envf))
    return subprocess.run([str(VERIFY), "--migrations-only"], env=env, capture_output=True, text=True, cwd=ROOT)


def test_incident_crew340_failed_migration_is_named_and_fails(tmp_path):
    r = _run(tmp_path, "20260701_v4_step_3_backfill_events_full_from_observations ClickHouse events_full table does not exist\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "20260701_v4_step_3" in r.stdout and r.stdout.rstrip().endswith("FAIL")


def test_incident_crew340_no_failed_migration_passes(tmp_path):
    r = _run(tmp_path, "")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.rstrip().endswith("PASS")
