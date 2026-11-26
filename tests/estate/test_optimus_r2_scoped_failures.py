"""The registered Optimus measure must be ABLE TO READ (idp#8575).

THE DEFECT THIS FILE IS THE FALSIFIER FOR (measured 2026-11-26, origin/main dd4c1e8be):

    catalog/optimus-metrics.json registered

        {"name": "bootstrap.r2_scoped_failures",
         "measure": ["python3", "tests/test_r2_decouple.py"], ...}

    and every readback of it was UNKNOWN, because:

      1. the measure's file is not on main --
         $ python3 tests/test_r2_decouple.py
         python3: can't open file 'tests/test_r2_decouple.py': [Errno 2] No such file...
         exit=2
         and greenlane/github.py:_optimus_readings skips a measure whose exit status is
         not 0, so no reading is recorded;
      2. even with the file present it cannot read: it is a unittest.main() module whose
         stdout is 0 bytes and carries no 'optimus.<name>=<number>' line, while the
         registry's own contract says "A measure prints exactly optimus.<name>=<number>".

    So a metric was registered that could never produce a reading: a metric that cannot
    fail, and a target-0 gate that never gated.

THE FIX: a measure that exists on main and prints exactly one line,

    optimus.bootstrap.r2_scoped_failures=<n>

where n is the number of fatal R2 failure points in bin/idp-bootstrap-cloudflare's
DNS/Workers critical path -- the R2 mint path and the R2 bucket-proof path. It is 5 on
main today and 0 once I-8455 Stage 1 ("R2 gates only R2") lands, so the metric reports the
truth about main and reaches its target on its own when the decoupling lands.

THE INSTRUMENT MUST BE ABLE TO FAIL: a subject it cannot judge (a bootstrap script with
neither a fatal nor a scoped R2 site, or a missing file) makes it exit non-zero and print
nothing, so the readback is UNKNOWN -- never a silent 0 that would pass a target-0 gate.

Everything here runs offline: no daemon, no network, no mutation outside pytest's own
temporary directory.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTRUMENT = ROOT / "bin" / "optimus-r2-scoped-failures"
BOOTSTRAP = ROOT / "bin" / "idp-bootstrap-cloudflare"
REGISTRY = ROOT / "catalog" / "optimus-metrics.json"

# The reader's own rule (greenlane/github.py:53): a number is a reading only when the
# measure printed exactly this on stdout.
READING = re.compile(r"(?m)^optimus\.([a-z][a-z0-9_.]{2,80})=(-?\d+(?:\.\d+)?)\s*$")

# The fatal sites, counted from the FAIL CALLS themselves -- a different implementation
# from the instrument's line scan, so the two have to agree.
FAIL_CALL = re.compile(r'fail\s+(\w+)\s+"([^"]*)"')


def _metric(name: str) -> dict:
    metrics = json.loads(REGISTRY.read_text())["metrics"]
    for entry in metrics:
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"BLIND: {name} is not registered in {REGISTRY}")


def _run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd or ROOT), capture_output=True, text=True, timeout=60
    )


def _instrument(path: Path) -> subprocess.CompletedProcess:
    return _run(["bash", str(INSTRUMENT), str(path)])


def _fatal_sites(script: Path) -> int:
    """The fatal R2 sites of a bootstrap script, counted from its FAIL calls."""
    calls = FAIL_CALL.findall(script.read_text())
    return sum(
        1
        for kind, message in calls
        if "r2" in kind.lower() or message.lower().startswith("r2")
    )


def test_a_known_bad_subject_is_counted_exactly(tmp_path: Path):
    """Known-bad fixture: three fatal R2 sites (one mint, two bucket-proof)."""
    fixture = tmp_path / "known-bad.sh"
    fixture.write_text(
        "#!/bin/bash\n"
        'r2tok=$(mint "estate-r2 $BUCKET" "$r2pol") || fail mint "R2 token not created"\n'
        'bk=$(cf "$R2_VAL" GET "/accounts/$ACCOUNT_ID/r2/buckets/$BUCKET") '
        '|| fail r2 "bucket GET transport failure"\n'
        '[ "$code" = 10006 ] || fail r2 "bucket GET refused by Cloudflare"\n'
    )
    done = _instrument(fixture)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "optimus.bootstrap.r2_scoped_failures=3"


def test_a_known_good_subject_reads_zero(tmp_path: Path):
    """Known-good fixture: the I-8455 shape -- R2 failures are scoped, so 0 sites."""
    fixture = tmp_path / "known-good.sh"
    fixture.write_text(
        "#!/bin/bash\n"
        'R2_SCOPE_FAILED=""\n'
        'r2tok=$(mint "estate-r2 $BUCKET" "$r2pol") '
        '|| { R2_SCOPE_FAILED="R2 token not created"; say WARN r2 "$R2_SCOPE_FAILED '
        '-- R2 gates only R2 (I-8455)"; }\n'
        'bk=$(cf "$R2_VAL" GET "/accounts/$ACCOUNT_ID/r2/buckets/$BUCKET") '
        '|| R2_SCOPE_FAILED="bucket GET transport failure"\n'
    )
    done = _instrument(fixture)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "optimus.bootstrap.r2_scoped_failures=0"


def test_the_instrument_refuses_to_guess(tmp_path: Path):
    """A subject it cannot judge must not become a 0: it exits non-zero and says nothing."""
    fixture = tmp_path / "undecidable.sh"
    fixture.write_text("#!/bin/bash\necho 'no credentials here'\n")
    done = _instrument(fixture)
    assert done.returncode != 0
    assert READING.search(done.stdout or "") is None
    assert "cannot judge" in (done.stderr or "")


def test_a_missing_bootstrap_script_is_not_a_zero(tmp_path: Path):
    """A missing subject is UNKNOWN, never a passing 0."""
    done = _instrument(tmp_path / "absent.sh")
    assert done.returncode != 0
    assert READING.search(done.stdout or "") is None
    assert "cannot judge" in (done.stderr or "")


def test_the_registered_measure_is_the_instrument():
    """The registry points at a measure that EXISTS on main, not at a file it does not."""
    entry = _metric("bootstrap.r2_scoped_failures")
    argv = entry["measure"]
    assert argv, "the metric has no measure"
    assert "bin/optimus-r2-scoped-failures" in argv
    assert (ROOT / argv[-1]).is_file(), "the registered measure is not on main"


def test_the_registered_measure_prints_a_reading_the_reader_accepts():
    """Run the registered argv exactly as the Greenlane does, and read it with its regex."""
    argv = _metric("bootstrap.r2_scoped_failures")["measure"]
    done = _run(argv)
    assert done.returncode == 0, done.stderr
    found = READING.findall(done.stdout or "")
    assert found, f"the registered measure printed no optimus line: {done.stdout!r}"
    name, value = found[-1]
    assert name == "bootstrap.r2_scoped_failures"
    # The reading must equal the fatal sites of the bootstrap script on main, counted
    # independently here, so the assertion survives I-8455 Stage 1 landing (5 -> 0).
    assert float(value) == _fatal_sites(BOOTSTRAP)


def test_the_readback_metric_reads_one():
    """The acceptance metric of idp#8575: the registered measure can read."""
    entry = _metric("bootstrap.r2_scoped_measure_reads")
    done = _run(entry["measure"])
    assert done.returncode == 0, done.stderr
    found = READING.findall(done.stdout or "")
    assert found, f"the readback metric printed no optimus line: {done.stdout!r}"
    name, value = found[-1]
    assert name == "bootstrap.r2_scoped_measure_reads"
    assert float(value) == 1
