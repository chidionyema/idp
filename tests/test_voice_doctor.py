"""voice-doctor judges the running voice-router, not its history.

2026-09-29: right after the models came back, a real turn spoke a 6.29 s reply and the doctor still
failed "speech synthesis", counting token errors logged before the restart.
"""

from __future__ import annotations

import runpy
from pathlib import Path

DOCTOR = (
    Path(__file__).resolve().parent.parent / "platform/estate/libexec/voice-doctor.py"
)


def test_only_lines_since_the_last_start_count(tmp_path):
    since_start = runpy.run_path(str(DOCTOR), run_name="voice_doctor")["since_start"]
    log = tmp_path / "voice-router.err.log"
    log.write_text(
        "voice-router-launchd: router key loaded\n"
        "Failed to convert Hello to token IDs\n"
        "voice-router-launchd: fetched models vits\n"
        "voice-router-launchd: router key loaded\n"
        "all good\n"
    )
    assert since_start(log, "voice-router-launchd:") == ["all good"]


def test_a_log_with_no_start_marker_reads_its_tail(tmp_path):
    since_start = runpy.run_path(str(DOCTOR), run_name="voice_doctor")["since_start"]
    log = tmp_path / "v.log"
    log.write_text("".join(f"l{i}\n" for i in range(1000)))
    assert since_start(log, '"voice.ready"')[0] == "l600"
    assert since_start(tmp_path / "absent.log", "x") == []
