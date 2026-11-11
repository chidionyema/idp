"""Falsifiers for bin/debug-packs, the door an agent asks "has this been seen before?" through.

The defect this file exists to prevent is subtle and it is the reason the door has a 3: a lookup
that answers "no match" when it could not look, or that answers every pack for every query, turns
the estate's memory into a decoration. Both failure modes read as a working search.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


IDP = Path(__file__).resolve().parents[1]
DOOR = IDP / "bin" / "debug-packs"


def run(*argv, cwd=None):
    return subprocess.run(
        [sys.executable, str(DOOR), *argv],
        capture_output=True,
        text=True,
        cwd=cwd or str(IDP),
    )


# ---- the door exists and is runnable --------------------------------------
# Section heading `the door exists and is runnable` is the falsifier for the pack that says an
# index nobody can invoke is a document.
def test_the_door_is_committed_and_executable():
    assert DOOR.exists(), "bin/debug-packs is missing, so the index has no door"
    assert DOOR.stat().st_mode & 0o111, "bin/debug-packs is not executable"


def test_the_door_parses_as_python():
    out = subprocess.run(
        [sys.executable, "-m", "py_compile", str(DOOR)], capture_output=True, text=True
    )
    assert out.returncode == 0, f"bin/debug-packs does not compile:\n{out.stderr}"


# ---- exit codes are the verdict, not decoration ----------------------------
# Section heading `exit codes are the verdict` is the falsifier for the pack that says a door
# reporting BLIND where it means "nothing matched" sends the next agent to re-derive a known bug.
def test_listing_the_index_succeeds():
    out = run()
    assert out.returncode == 0, out.stderr
    assert re.search(r"^DBG-001", out.stdout, re.M), "the listing names no packs"


def test_a_known_symptom_finds_its_pack():
    out = run("vault", "BLIND")
    assert out.returncode == 0, (
        "a symptom that is IN the index answered 'nothing matched'"
    )
    assert "DBG-001" in out.stdout, out.stdout


def test_an_unknown_symptom_exits_3_and_says_new_not_blind():
    out = run("quantum", "flux", "capacitor")
    assert out.returncode == 3, (
        "an unknown symptom must exit 3 (NEW), not 0 (found) or 2 (BLIND); a false 0 claims the "
        f"estate has seen this and a false 2 hides that it looked. got {out.returncode}"
    )
    assert "NEW" in out.stdout.upper() or "RECORDED" in out.stdout.upper(), out.stdout


def test_search_is_and_not_or():
    """Two words that no single pack carries together must not match. An OR search over prose
    matches everything, which is how a lookup door quietly becomes an echo."""
    both = run("vault", "quantum")
    assert both.returncode == 3, (
        "a two-word query whose words live in different packs matched something, so the search "
        f"is OR not AND:\n{both.stdout}"
    )


def test_id_shows_one_pack_in_full():
    out = run("--id", "DBG-004")
    assert out.returncode == 0, out.stderr
    for field in ("symptom", "cause", "falsifier", "remedy"):
        assert field in out.stdout, f"--id DBG-004 did not print {field}"
    assert "DBG-004" in out.stdout


def test_id_of_a_pack_that_does_not_exist_exits_3():
    out = run("--id", "DBG-999")
    assert out.returncode == 3, f"a missing id must be NEW (3), got {out.returncode}"


def test_json_mode_is_machine_consumable():
    out = run("--json", "vault")
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert isinstance(data, list) and data, "--json must emit a list of packs"
    assert all("id" in p and "falsifier" in p for p in data)


# ---- BLIND is measured, never guessed ------------------------------------
# Section heading `BLIND is measured` is the falsifier for the pack that says a lookup which
# answers "nothing found" outside a checkout is a false absence.
def test_outside_any_checkout_it_is_blind_not_empty(tmp_path):
    """Copied out of the checkout, the door must say BLIND (2) and name what it looked for. The
    measured defect it prevents: a door that resolved its root from __file__ answered "no pack
    matches" for a token sitting in the vault (DBG-003)."""
    stray = tmp_path / "elsewhere" / "debug-packs"
    stray.parent.mkdir(parents=True)
    stray.write_text(DOOR.read_text())
    stray.chmod(0o755)
    out = subprocess.run(
        [sys.executable, str(stray), "vault"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert out.returncode == 2, (
        f"outside a checkout the door answered {out.returncode}; an empty index must be BLIND, "
        f"never 'no match'. stdout={out.stdout!r} stderr={out.stderr!r}"
    )
    assert "BLIND" in (out.stdout + out.stderr), "it did not name itself BLIND"


def test_check_proves_every_named_falsifier_exists():
    out = run("--check")
    assert out.returncode == 0, (
        "a pack names a falsifier file that does not exist, so that pack cannot fire:\n"
        + out.stdout
        + out.stderr
    )
    assert "ok" in out.stdout
