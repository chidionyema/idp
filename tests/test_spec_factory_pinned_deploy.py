"""A host without an argon checkout still finds the pinned Spec Factory deployment."""

import os
import subprocess
import tempfile
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"


def test_pinned_deployment_under_estate_home_is_found():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d) / "home"
        tool = home / ".estate" / "tools" / "estate-spec-factory" / "spec_factory.py"
        tool.parent.mkdir(parents=True)
        tool.write_text("import sys\nprint('PINNED:' + ','.join(sys.argv[1:]))\n")
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("ESTATE_SPEC_FACTORY", "ESTATE_ARGON")
        }
        env["HOME"] = str(home)
        r = subprocess.run(
            [str(BIN / "spec-factory"), "types"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert "PINNED:types" in r.stdout
