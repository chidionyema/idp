"""Canonical relative-path helper (cp20 "Windows paths do not change
hashes"). A state diff, and the receipt hash chain built over it, must
hash identically whether it was produced on macOS or on Windows -- the
only thing that legitimately differs between the two OSes here is the
path separator a filesystem walk hands back. canonical_relpath collapses
both separators to POSIX ("/") before anything is hashed, so the same
logical file never produces two different hashes depending on which OS
walked it.
"""
from __future__ import annotations

from sovereign.trust import config_keys as ck

_POSIX_SEP = ck.get("trust.posix_separator")
_WINDOWS_SEP = ck.get("trust.windows_separator")
_CURRENT_DIR = "."
_EMPTY = ""


def _to_posix_parts(value: str) -> list[str]:
    # A path string may arrive with either separator regardless of the
    # host OS (a Windows-produced diff replayed on macOS, or the reverse),
    # so both are normalized here rather than trusting pathlib's PurePath
    # for "the" OS -- there is no single OS to trust.
    normalized = value.replace(_WINDOWS_SEP, _POSIX_SEP)
    return [part for part in normalized.split(_POSIX_SEP) if part not in (_EMPTY, _CURRENT_DIR)]


def canonical_relpath(root: str, path: str) -> str:
    """`path` relative to `root`, POSIX-separated, regardless of which OS
    (or which separator convention) produced either string. If `path`
    does not start with `root`'s parts, `path` itself is returned
    canonicalized (the caller passed an already-relative path)."""
    root_parts = _to_posix_parts(root)
    path_parts = _to_posix_parts(path)
    if root_parts and path_parts[: len(root_parts)] == root_parts:
        rel_parts = path_parts[len(root_parts):]
    else:
        rel_parts = path_parts
    return _POSIX_SEP.join(rel_parts)
