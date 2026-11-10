"""Falsifiers for bin/research-first, the door .githooks/commit-msg names.

The whole value of this door is that it CANNOT be satisfied by assertion: a receipt is a record of
two kinds of finding, each carrying a source that is checked. The defect this file exists to
prevent is a door that writes `pass: true` for a window with nothing in it -- which is exactly what
the receipts already in the store show happened before (findings with no source, pass: true).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
DOOR = IDP / "bin" / "research-first"


def run(*argv, store):
    env = dict(os.environ, ESTATE_RECEIPTS=str(store))
    return subprocess.run(
        [sys.executable, str(DOOR), *argv],
        capture_output=True,
        text=True,
        cwd=str(IDP),
        env=env,
    )


# ---- the door exists and is runnable --------------------------------------
def test_the_door_is_committed_and_executable():
    assert DOOR.exists(), (
        "bin/research-first is missing: the commit-msg gate names a door that is not there"
    )
    assert DOOR.stat().st_mode & 0o111


def test_the_door_parses_as_python():
    out = subprocess.run(
        [sys.executable, "-m", "py_compile", str(DOOR)], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr


# ---- the hook's contract, read from the hook ------------------------------
def test_the_gate_named_in_the_hook_is_satisfied_by_a_real_receipt(tmp_path):
    """The end-to-end claim: run the door, then run the hook's own predicate against the result.
    If these two ever drift, every commit in the estate starts refusing again."""
    store = tmp_path / "receipts"
    assert run("start", "--task", "t", store=store).returncode == 0
    assert (
        run(
            "note",
            "--kind",
            "internal",
            "--finding",
            "f",
            "--source",
            "bin/idp-edge-cutover:1",
            store=store,
        ).returncode
        == 0
    )
    assert (
        run(
            "note",
            "--kind",
            "external",
            "--finding",
            "e",
            "--source",
            "https://example.com/x",
            store=store,
        ).returncode
        == 0
    )
    assert run("done", store=store).returncode == 0
    newest = sorted((store / "research-first").glob("*.json"))[-1]
    rec = json.loads(newest.read_text())
    assert rec["pass"] is True
    assert rec["internal"] and rec["external"]


def test_done_without_a_window_is_blind_not_a_silent_pass(tmp_path):
    store = tmp_path / "receipts"
    out = run("done", store=store)
    assert out.returncode == 2, (
        f"no open window must be BLIND (2), got {out.returncode}"
    )
    assert not list((store / "research-first").glob("*.json")), (
        "it wrote a receipt anyway"
    )


# ---- a source is checked, never trusted ----------------------------------
def test_an_internal_source_naming_a_file_that_does_not_exist_is_refused(tmp_path):
    store = tmp_path / "receipts"
    run("start", "--task", "t", store=store)
    out = run(
        "note",
        "--kind",
        "internal",
        "--finding",
        "f",
        "--source",
        "bin/does-not-exist.sh:1",
        store=store,
    )
    assert out.returncode == 2, (
        "an internal source naming a nonexistent file was accepted, so the receipt records a "
        f"finding about nothing. got {out.returncode}: {out.stderr}"
    )
    assert "does not exist" in out.stderr


def test_an_internal_source_without_a_line_is_refused(tmp_path):
    store = tmp_path / "receipts"
    run("start", "--task", "t", store=store)
    out = run(
        "note",
        "--kind",
        "internal",
        "--finding",
        "f",
        "--source",
        "bin/idp-edge-cutover",
        store=store,
    )
    assert out.returncode == 2, "a bare path with no line number is not `path:line`"


def test_an_external_source_that_is_not_a_url_is_refused(tmp_path):
    store = tmp_path / "receipts"
    run("start", "--task", "t", store=store)
    out = run(
        "note",
        "--kind",
        "external",
        "--finding",
        "e",
        "--source",
        "i-read-it-somewhere",
        store=store,
    )
    assert out.returncode == 2, "an external source that is not a URL is an assertion"


def test_an_empty_source_is_refused_and_the_flag_is_required(tmp_path):
    store = tmp_path / "receipts"
    run("start", "--task", "t", store=store)
    out = run(
        "note", "--kind", "internal", "--finding", "f", "--source", "", store=store
    )
    assert out.returncode == 2, "an empty --source must be refused"
    out2 = run("note", "--kind", "internal", "--finding", "f", store=store)
    assert out2.returncode != 0, "--source must be a required flag"


# ---- a window that lacks a kind FAILS, honestly --------------------------
def test_one_kind_only_fails_and_names_the_missing_kind(tmp_path):
    store = tmp_path / "receipts"
    run("start", "--task", "t", store=store)
    run(
        "note",
        "--kind",
        "internal",
        "--finding",
        "f",
        "--source",
        "bin/idp-edge-cutover:1",
        store=store,
    )
    out = run("done", store=store)
    assert out.returncode == 1, (
        "a window with only internal findings must FAIL (1), not pass and not be BLIND"
    )
    assert "external" in out.stderr, "the failure must name WHICH kind is missing"
    rec = json.loads(sorted((store / "research-first").glob("*.json"))[-1].read_text())
    assert rec["pass"] is False and rec["missing"] == ["external"]


def test_an_unknown_kind_is_refused(tmp_path):
    store = tmp_path / "receipts"
    run("start", "--task", "t", store=store)
    out = run(
        "note",
        "--kind",
        "vibes",
        "--finding",
        "f",
        "--source",
        "https://example.com",
        store=store,
    )
    assert out.returncode == 2, "an unknown --kind must not be silently accepted"
