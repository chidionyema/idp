"""voice-router's launcher must put back speech models that went missing, and only the pinned ones.

2026-09-29: ~/.cache/estate-tools/sherpa-models vanished under a running voice-router. Every reply
then failed at speech ("Failed to convert ... to token IDs"), and a restart would not have started
at all, because nothing installed the models: they had been put there by hand. The launcher now
fetches any pinned model that is missing, checked against the Dockerfile's sha256.
"""

from __future__ import annotations

import hashlib
import io
import runpy
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "bin/voice-router-launchd"
NAME = "vits-piper-en_US-ljspeech-medium"
REL = f"tts-models/{NAME}.tar.bz2"


def _mod():
    return runpy.run_path(str(LAUNCHER), run_name="voice_router_launchd")


def _release() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:bz2") as t:
        data = b"tokens"
        info = tarfile.TarInfo(f"{NAME}/tokens.txt")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _serve(mod, monkeypatch, body: bytes) -> list[str]:
    asked: list[str] = []

    def run(cmd, check):
        asked.append(cmd[-1])
        Path(cmd[cmd.index("-o") + 1]).write_bytes(body)

    monkeypatch.setattr(mod["subprocess"], "run", run)
    return asked


def test_the_pins_are_the_images_pins():
    pins = _mod()["pinned_models"](ROOT / "platform/voice-router/Dockerfile")
    assert {Path(r).name for r, _ in pins} >= {f"{NAME}.tar.bz2"}
    assert all(len(sha) == 64 for _, sha in pins)


def test_a_missing_model_is_fetched_and_unpacked(tmp_path, monkeypatch):
    mod, body = _mod(), _release()
    asked = _serve(mod, monkeypatch, body)
    got = mod["ensure_models"](tmp_path, [(REL, hashlib.sha256(body).hexdigest())])
    assert got == [NAME] and asked and asked[0].endswith(REL)
    assert (tmp_path / NAME / "tokens.txt").read_bytes() == b"tokens"


def test_a_present_model_is_left_alone(tmp_path, monkeypatch):
    mod = _mod()
    (tmp_path / NAME).mkdir()
    asked = _serve(mod, monkeypatch, b"")
    assert mod["ensure_models"](tmp_path, [(REL, "0" * 64)]) == [] and not asked


def test_a_download_that_is_not_the_pinned_bytes_is_refused(tmp_path, monkeypatch):
    mod = _mod()
    _serve(mod, monkeypatch, _release())
    with pytest.raises(RuntimeError, match="not the pinned"):
        mod["ensure_models"](tmp_path, [(REL, "0" * 64)])
    assert not (tmp_path / NAME).exists()


def test_a_download_killed_midway_is_cleared(tmp_path, monkeypatch):
    mod = _mod()
    (tmp_path / NAME).mkdir()
    (tmp_path / "tmp4doqtx77").mkdir()
    _serve(mod, monkeypatch, b"")
    mod["ensure_models"](tmp_path, [(REL, "0" * 64)])
    assert not (tmp_path / "tmp4doqtx77").exists() and (tmp_path / NAME).is_dir()
