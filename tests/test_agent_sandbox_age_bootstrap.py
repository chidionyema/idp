"""Legion runner encryption bootstrap must not depend on broken Ubuntu mirrors."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "agent-sandbox-age"
WORKFLOW = ROOT / ".github" / "workflows" / "agent-sandbox.yml"


def test_bootstrap_pins_official_asset_and_never_uses_apt() -> None:
    body = SCRIPT.read_text()
    assert "v1.3.2-linux-amd64.tar.gz" in body
    assert "cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10" in body
    assert "sha256sum --check --status" in body
    assert "apt-get" not in body
    assert body.index("sha256sum --check --status") < body.index("sudo install")


def test_bogus_archive_never_reaches_install() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        curl = tmp / "curl"
        curl.write_text(
            "#!/bin/sh\\n"
            "while [ \\"$#\\" -gt 0 ]; do\\n"
            "  if [ \\"$1\\" = '--output' ]; then\\n"
            "    shift; printf 'tampered' > \\"$1\\"; exit 0\\n"
            "  fi\\n"
            "  shift\\n"
            "done\\nexit 2\\n"
        )
        curl.chmod(0o755)
        sudo = tmp / "sudo"
        sudo.write_text("#!/bin/sh\\ntouch \\"$RUNNER_TEMP/sudo_called\\"\\nexit 99\\n")
        sudo.chmod(0o755)
        env = {**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}", "RUNNER_TEMP": raw}
        result = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=15)
        assert result.returncode != 0
        assert "SHA-256 mismatch" in result.stderr
        assert not (tmp / "sudo_called").exists()


def test_workflow_all_three_stages_use_pinned_bootstrap() -> None:
    contents = WORKFLOW.read_text()
    assert contents.count("bash bin/agent-sandbox-age") == 3
    assert "sudo apt-get update -qq && sudo apt-get install -y -qq age" not in contents
