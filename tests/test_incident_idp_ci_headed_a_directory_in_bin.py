"""Incident 2026-08-29 (idp#846 fast-gate): bin/idp-ci ran `head -1` over bin/* and printed
`head: error reading 'bin/lib': Is a directory` on every run, a red-looking line beside a real red.
A directory under bin/ is skipped before any file check."""

from pathlib import Path

CI = Path(__file__).resolve().parents[1] / "bin" / "idp-ci"


def test_bin_lib_is_a_directory_so_the_guard_is_live() -> None:
    assert (CI.parent / "lib").is_dir()
