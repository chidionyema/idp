"""The two commands the bootstrap plan rests on have to answer the same way every run.

Founder, 2026-08-31: "THIS PROCEES NEEDS AUTOMATION and rerunnable". These pin the properties that
make that true without reaching a cloud: both commands are read-only by default, both take a
freshness window rather than re-asking, and the backup command never counts a volume it has not
actually backed up.
"""

import subprocess
import sys
from pathlib import Path

IDP = Path(__file__).resolve().parent.parent
AUDIT = IDP / "bin/idp-estate-audit"
BACKUP = IDP / "bin/idp-estate-backup"


def help_text(script: Path) -> str:
    p = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_both_commands_answer_help_without_a_cloud():
    assert "--reuse" in help_text(AUDIT)
    assert "--dry-run" in help_text(BACKUP)


def test_a_volume_that_was_not_backed_up_is_never_counted_as_covered():
    """The first dry run said 16/16 covered on an estate where not one volume had ever been
    backed up, because a planned backup counted as a real one. That is the silent-green class."""
    lines = [
        ln
        for ln in BACKUP.read_text().splitlines()
        if ln.strip().startswith("covered =")
    ]
    assert len(lines) == 1, lines
    assert '"fresh"' in lines[0] and '"created"' in lines[0]
    assert "would-create" not in lines[0]


def test_the_derived_list_says_why_each_type_is_not_work():
    """A resource excused from the codify list has to name what makes it; otherwise the number
    that matters can be shrunk by adding a type to a set."""
    text = AUDIT.read_text()
    block = text[text.index("DERIVED = {") : text.index("}", text.index("DERIVED = {"))]
    entries = [ln for ln in block.splitlines() if ln.strip().startswith('"')]
    assert len(entries) >= 8
    for ln in entries:
        reason = ln.split(":", 1)[1].strip().strip(",").strip('"')
        assert len(reason) > 20, f"no reason given for {ln.strip()}"


def test_the_inventory_report_is_generated_and_names_its_own_command():
    report = IDP / "docs/audit/estate-inventory.md"
    assert report.exists()
    body = report.read_text()
    assert "bin/idp-estate-audit" in body
    assert "bin/idp-estate-backup" in body
