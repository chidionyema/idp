"""scheduler-venv builds the scheduler's .venv from the Dockerfile's pins and proves it imports.

Runs the repo's platform/estate/libexec/scheduler-venv.sh against a fake IDP checkout whose .venv
is the e48c6919 blob (a file, not a directory). A stub interpreter stands in for python3.12: its
`-m venv` lays out bin/ with a recording pip and a real python3, so the verify step genuinely
imports the fake checkout's estate_scheduler.definitions -- no network, no real dagster.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/scheduler-venv.sh"
)
BLOB = "/Users/x/Documents/code/idp/.venv"

STUB_PY = f"""#!/usr/bin/env bash
# stub python3.12: only `-m venv DIR` is supported
[ "$1" = -m ] && [ "$2" = venv ] || exit 9
d="$3"; mkdir -p "$d/bin"
ln -s {sys.executable} "$d/bin/python"
printf '#!/usr/bin/env bash\\necho "$@" >> "%s/pip.log"\\n' "$d" > "$d/bin/pip"
for b in dagster-daemon dagster-webserver; do printf '#!/bin/sh\\n' > "$d/bin/$b"; done
chmod +x "$d/bin/"*
"""


def _idp(
    tmp_path: Path, defs: str = "defs = type('D', (), {'jobs': [1, 2, 3]})()"
) -> Path:
    idp = tmp_path / "idp"
    (idp / "scheduler/estate_scheduler").mkdir(parents=True)
    (idp / "scheduler/estate_scheduler/__init__.py").write_text("")
    (idp / "scheduler/estate_scheduler/definitions.py").write_text(defs + "\n")
    (idp / "estate-scheduler.Dockerfile").write_text(
        "RUN pip install --no-cache-dir \\\n    dagster==1.13.19 \\\n"
        "    dagster-webserver==1.13.19 \\\n    dagster-postgres==0.29.19\n"
    )
    (idp / ".venv").write_text(BLOB)
    return idp


def _run(idp: Path, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    py = tmp_path / "python3.12"
    py.write_text(STUB_PY)
    py.chmod(0o755)
    env = {**os.environ, "IDP_REPO": str(idp), "SCHEDULER_VENV_PYTHON": str(py)}
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_dry_run_names_the_blob_and_touches_nothing(tmp_path):
    idp = _idp(tmp_path)
    r = _run(idp, tmp_path, "false")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "is not a directory (file): would move" in r.stdout, r.stdout
    assert "dagster==1.13.19" in r.stdout and "dagster-postgres==0.29.19" in r.stdout
    assert (idp / ".venv").read_text() == BLOB
    assert not list(idp.glob(".venv.stale-*"))


def test_apply_moves_the_blob_aside_installs_the_pins_and_proves_the_import(tmp_path):
    idp = _idp(tmp_path)
    r = _run(idp, tmp_path, "true")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "schedule.yml ok: 3 jobs" in r.stdout, r.stdout
    (stale,) = idp.glob(".venv.stale-*")
    assert stale.read_text() == BLOB  # moved, never deleted
    assert (idp / ".venv").is_dir()
    pip = (idp / ".venv/pip.log").read_text()
    for pkg in (
        "dagster==1.13.19",
        "dagster-webserver==1.13.19",
        "dagster-postgres==0.29.19",
    ):
        assert pkg in pip, pip
    # a second run finds a working venv and changes nothing
    again = _run(idp, tmp_path, "true")
    assert again.returncode == 0 and "nothing to do" in again.stdout, again.stdout
    assert len(list(idp.glob(".venv.stale-*"))) == 1


def test_a_venv_the_scheduler_cannot_import_from_is_exit_3(tmp_path):
    idp = _idp(tmp_path, defs="raise ImportError('load_gate')")
    r = _run(idp, tmp_path, "true")
    assert r.returncode == 3, r.stdout + r.stderr
    assert "ok " not in r.stdout


def test_no_dagster_pin_is_refused(tmp_path):
    idp = _idp(tmp_path)
    (idp / "estate-scheduler.Dockerfile").write_text("FROM python:3.11-slim\n")
    r = _run(idp, tmp_path, "true")
    assert r.returncode == 1 and "REFUSED no dagster" in r.stdout, r.stdout
    assert (idp / ".venv").read_text() == BLOB
