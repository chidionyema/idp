"""crew#561, 2026-08-30: otto-parity run 33291368505 failed `mac-run hostname` with
`cp: cannot create regular file '/tmp/mac-run.id_ed25519': Permission denied`, so Otto could not
reach the founder's Mac although the key was mounted and the tailnet was up. The key copy ssh
needs (the mounted secret is group-readable, which ssh refuses) goes under HERMES_HOME, the data
volume hermes already writes to. This pins that: no /tmp in mac-run's key path."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAC_RUN = ROOT / "platform" / "hermes-agent" / "mac-run.yaml"


def _script() -> str:
    text = MAC_RUN.read_text()
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def test_key_copy_lives_under_hermes_home() -> None:
    m = re.search(r"^\s*key=(\S+)", _script(), re.M)
    assert m, "mac-run must name where it copies the key"
    assert "HERMES_HOME" in m.group(1), m.group(1)


def test_key_copy_never_targets_tmp() -> None:
    script = _script()
    tmp_root = "/" + "tmp/"
    assert tmp_root not in script
    assert "TMPDIR" not in script
