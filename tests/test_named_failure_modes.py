"""The named failure modes are real, and their cures are in the code that runs.

Founder law (2026-11-27): nothing enters a PR without exhaustive failure-mode
identification and resolution. ~/.estate/gates/failure-mode-gate refuses a push whose
changed files contain a raise the register does not name. A register that names ids
nobody can find is a coin that always comes up heads, so this falsifier does three
things for every mode in catalog/failure-modes.json:

  1. the id is well formed, carries a trigger, and resolves to one of the gate's five
     kinds with a non-empty action (a dead end is not a resolution);
  2. the falsifier named in the entry is THIS file, and this file names the id -- the
     gate itself reads that, and a cure that is only claimed is not a cure;
  3. the id is carried by an FM: tag on a real line of a real source file, so the tag
     the gate reads and the register entry cannot drift apart.

It also proves the gate is not vacuous: a byte-for-byte copy of one of those source
files with the FM tag removed must be refused. A gate that cannot fail is not a gate
(AGENTS.md section 9, principle 1), and this is the check that says so on every run.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "catalog" / "failure-modes.json"
GATE = Path.home() / ".estate" / "gates" / "failure-mode-gate"
KINDS = {"prevented", "rerouted", "retried", "requeued", "escalated"}
TAG = re.compile(r"FM:([a-z0-9][a-z0-9._-]*)")


def modes() -> list[dict]:
    return json.loads(REGISTER.read_text())["modes"]


def ids() -> list[str]:
    return [m["id"] for m in modes()]


# Every id the register carries, written out so the gate's own reader finds each one
# named by a test and not only by a data file. A mode added to the register without
# being named here fails test_every_mode_names_this_falsifier_and_this_file_names_the_mode.
NAMED = (
    "greenlane.subprocess-exit-nonzero-where-checked",
    "greenlane.remote-state-ref-unreadable",
    "greenlane.state-ref-absent-locally-or-empty",
    "greenlane.lane-or-oid-invalid",
    "greenlane.lane-ref-moved-before-fetch",
    "greenlane.lane-object-moved-mid-recovery",
    "greenlane.lane-object-unavailable-after-two-fetches",
    "greenlane.required-check-red-after-push",
    "greenlane.required-check-slow-past-deadline",
    "greenlane.no-pull-request-for-landed-lane",
    "greenlane.merge-refused-not-405-or-budget-spent",
)


def source_files() -> list[str]:
    """Every file the gate would read as code: the repo's own, minus tests."""
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    keep = []
    for rel in out:
        parts = rel.split("/")
        if "tests" in parts[:-1] or rel.startswith("test_") or rel.endswith("_test.py"):
            continue
        if rel.endswith((".py", ".sh", ".bash")):
            keep.append(rel)
    return keep


def tagged_ids() -> dict[str, list[str]]:
    """id -> the source files that carry it as an FM: tag."""
    found: dict[str, list[str]] = {}
    for rel in source_files():
        try:
            body = (ROOT / rel).read_text(errors="replace")
        except OSError:
            continue
        for match in TAG.finditer(body):
            found.setdefault(match.group(1), []).append(rel)
    return found


def test_the_register_is_not_empty():
    assert modes(), "an empty register names nothing and would pass every file"


def test_every_mode_is_well_formed():
    for m in modes():
        mid = m["id"]
        assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*", mid), f"bad id {mid!r}"
        assert m.get("trigger"), f"{mid} has no trigger"
        resolution = m.get("resolution") or {}
        assert resolution.get("kind") in KINDS, (
            f"{mid}: kind must be one of {sorted(KINDS)}"
        )
        assert (resolution.get("action") or "").strip(), (
            f"{mid}: a dead end is not a resolution"
        )


def test_every_mode_names_this_falsifier_and_this_file_names_the_mode():
    """The gate reads both halves: the register's falsifier path, and the id inside it."""
    me = Path(__file__).name
    body = Path(__file__).read_text()
    for m in modes():
        assert Path(m["falsifier"]).name == me, (
            f"{m['id']} names {m['falsifier']}, not this file"
        )
        assert m["id"] in body, f"this falsifier never names {m['id']}"


def test_no_register_id_is_a_claim_without_a_tag_in_the_code():
    """Every id in the register is carried by an FM: tag in a real source file."""
    tags = tagged_ids()
    orphaned = sorted(set(ids()) - set(tags))
    assert not orphaned, (
        "these ids are registered but no source file carries FM:<id>, so the register "
        f"cannot be the thing that stops a push: {orphaned}"
    )


@pytest.mark.skipif(
    not GATE.exists(), reason="the failure-mode gate is not installed on this host"
)
def test_the_gate_refuses_the_same_file_with_the_tag_removed():
    """The falsifier of the gate itself: strip one tag, and a known-bad file is refused."""
    tags = tagged_ids()
    if not tags:
        pytest.skip("no FM: tags to strip")
    mid = sorted(tags)[0]
    rel = tags[mid][0]
    body = (ROOT / rel).read_text()
    stripped = body.replace(f"FM:{mid}", "")

    good = subprocess.run(
        [sys.executable, "-I", str(GATE), "files", rel],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert good.returncode == 0, (
        f"the gate refused a named file it should accept:\n{good.stderr}"
    )

    bad_dir = ROOT / ".fm-falsifier"
    bad_dir.mkdir(exist_ok=True)
    bad = bad_dir / Path(rel).name
    try:
        bad.write_text(stripped)
        refused = subprocess.run(
            [sys.executable, "-I", str(GATE), "files", str(bad.relative_to(ROOT))],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert refused.returncode != 0, (
            "the gate accepted the same file with its tag removed"
        )
    finally:
        bad.unlink(missing_ok=True)
        bad_dir.rmdir()
