"""Incident, crew#227 CP5 (2026-08-27): ~/.estate/bin/estate-presence was compiled on 2026-08-25 04:15
and never again; a706e26 (16:29 the same day) added --pubkey and --verify-sig to the source, so on
the founder's Mac `enroll()` got {"error":"unknown command"} and failed closed. Rule (rung 4): a
cached build artifact is invalidated by its source's content, not by its existence."""
import hashlib
import os
import stat
from pathlib import Path

import pytest

from sovereign.trust import anchor


@pytest.fixture
def fake_toolchain(monkeypatch, tmp_path):
    """Stands in for xcrun swiftc: 'compiles' by copying the source text into the output."""
    src = tmp_path / "presence_helper.swift"
    out = tmp_path / "bin" / "estate-presence"
    monkeypatch.setattr(anchor, "_swift_source_path", lambda: src)
    monkeypatch.setattr(anchor, "_swift_helper_path", lambda: out)
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1]).write_bytes(Path(cmd[2]).read_bytes())
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(anchor.subprocess, "run", run)
    return src, out, calls


def test_helper_rebuilds_when_the_source_changes(fake_toolchain):
    src, out, calls = fake_toolchain
    src.write_text("v1 --detect --sign --verify")
    assert anchor._ensure_swift_helper_compiled() == out and len(calls) == 1
    assert anchor._ensure_swift_helper_compiled() == out and len(calls) == 1, "unchanged source: cached"
    src.write_text("v2 --detect --sign --verify --pubkey --verify-sig")
    assert anchor._ensure_swift_helper_compiled() == out
    assert len(calls) == 2, "changed source must recompile"
    assert out.read_text() == src.read_text()
    assert out.with_suffix(".sha256").read_text() == hashlib.sha256(src.read_bytes()).hexdigest()


def test_binary_without_a_stamp_is_rebuilt_once(fake_toolchain):
    """The state this incident was found in: a binary from before the stamp existed."""
    src, out, calls = fake_toolchain
    src.write_text("v2")
    out.parent.mkdir(parents=True)
    out.write_text("v1")
    assert anchor._ensure_swift_helper_compiled() == out
    assert len(calls) == 1 and out.read_text() == "v2"
    assert anchor._ensure_swift_helper_compiled() == out and len(calls) == 1
