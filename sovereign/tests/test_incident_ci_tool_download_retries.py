"""Incident (2026-08-27, run 33034954710): offline-gate on main went red because one `curl | tar` tool
download hit "Recv failure: Connection reset by peer"; rule-guard then refused every merge onto the red
main. Rule (rung 4): every network download in a workflow retries, so a single peer reset is not a red
main. Both ways: the real files pass; a stripped copy fails."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
DOWNLOAD = re.compile(r"curl\s+[^\n|]*https?://[^\n|]*\|")


def _unretried(text):
    return [m.group(0) for m in DOWNLOAD.finditer(text) if "--retry" not in m.group(0)]


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_every_piped_download_retries(wf):
    assert _unretried(wf.read_text()) == []


def test_detector_sees_a_bare_download():
    assert _unretried("run: curl -sSL https://x/y.tgz | tar -xz\n") != []
    assert _unretried("run: curl -sSL --retry 5 https://x/y.tgz | tar -xz\n") == []
