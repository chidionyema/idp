"""pi-founder-governance: the pi prompt is stamped through the canonical intake, with its source.

The extension is TypeScript, and its rules run under node's own test runner with no pi import, so
this wrapper makes them part of the python suite -- the one the gates run. Skipped only when node
itself is absent or too old for --experimental-strip-types (22.6+), the same convention as the
pi-plan-lock and kustomize tests.
"""

import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extensions" / "pi-founder-governance"


def _node_ok() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    m = re.match(r"v(\d+)\.(\d+)", out.strip())
    return bool(m) and (int(m[1]), int(m[2])) >= (22, 6)


@pytest.mark.skipif(not _node_ok(), reason="node >= 22.6 is not installed")
def test_the_pi_prompt_is_stamped_with_its_source():
    """A pi prompt enters the ledger as source=pi, through bin/estate-founder-intake."""
    r = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--test",
            str(EXT / "source.test.ts"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]
    assert re.search(r"# pass [1-9]", r.stdout), "node ran no tests: " + r.stdout[-500:]


def test_the_extension_stamps_through_the_canonical_intake():
    """The prompt must reach the ONE door every surface stamps through."""
    src = (EXT / "index.ts").read_text()
    assert "estate-founder-intake" in src
    assert '"--source"' in src, "the intake must be told where the prompt came from"
    assert '"pi"' in src
