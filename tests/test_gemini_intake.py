"""The Gemini intake preserves originals and is idempotent (founder, 2026-11-15).

A stranded Gemini workstream was lost because nothing captured it. This test proves the intake
half: first run copies, second run copies 0, a differing destination file is never overwritten,
and a dry run copies nothing.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INTAKE = REPO / "bin" / "gemini-intake"


def _run(source: Path, dest: Path, *extra: str) -> dict:
    out = subprocess.run(
        [sys.executable, str(INTAKE), "--source", str(source), "--dest", str(dest), *extra],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def _source(tmp_path: Path) -> Path:
    src = tmp_path / "handover"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("alpha\n", encoding="utf-8")
    (src / "sub" / "b.txt").write_text("beta\n", encoding="utf-8")
    return src


def test_first_run_copies_and_writes_manifest(tmp_path: Path) -> None:
    src = _source(tmp_path)
    dest = tmp_path / "quarantine" / "gemini-1"
    result = _run(src, dest)
    assert result["counts"]["SAFE-COPIED"] == 2
    assert (dest / "a.txt").read_text(encoding="utf-8") == "alpha\n"
    manifest = json.loads((dest / ".intake" / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["SAFE-COPIED"] == 2
    assert len(manifest["files"]) == 2
    assert all(len(f["sha256"]) == 64 for f in manifest["files"])
    assert (dest / ".intake" / "SHA256SUMS").read_text(encoding="utf-8").count("\n") == 2


def test_second_run_copies_zero(tmp_path: Path) -> None:
    src = _source(tmp_path)
    dest = tmp_path / "quarantine" / "gemini-1"
    _run(src, dest)
    result = _run(src, dest)
    assert result["counts"]["SAFE-COPIED"] == 0
    assert result["counts"]["SKIPPED-IDENTICAL"] == 2


def test_a_differing_destination_is_never_overwritten(tmp_path: Path) -> None:
    src = _source(tmp_path)
    dest = tmp_path / "quarantine" / "gemini-1"
    _run(src, dest)
    (dest / "a.txt").write_text("locally changed\n", encoding="utf-8")
    result = _run(src, dest)
    assert result["counts"]["ON-DISK-DIFFERS"] == 1
    assert result["counts"]["SKIPPED-IDENTICAL"] == 1
    assert (dest / "a.txt").read_text(encoding="utf-8") == "locally changed\n"


def test_source_files_named_like_the_records_do_not_collide(tmp_path: Path) -> None:
    src = _source(tmp_path)
    (src / "SHA256SUMS").write_text("source-owned manifest\n", encoding="utf-8")
    (src / "MANIFEST.json").write_text('{"source": true}\n', encoding="utf-8")
    dest = tmp_path / "quarantine" / "gemini-collide"
    _run(src, dest)
    second = _run(src, dest)
    assert second["counts"]["ON-DISK-DIFFERS"] == 0
    assert second["counts"]["SKIPPED-IDENTICAL"] == 4
    assert (dest / "SHA256SUMS").read_text(encoding="utf-8") == "source-owned manifest\n"


def test_a_dry_run_copies_nothing(tmp_path: Path) -> None:
    src = _source(tmp_path)
    dest = tmp_path / "quarantine" / "gemini-dry"
    result = _run(src, dest, "--dry-run")
    assert result["counts"]["DRY-RUN"] == 2
    assert not (dest / "a.txt").exists()
