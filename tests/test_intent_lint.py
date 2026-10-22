"""bin/intent-lint: every intent on disk can run its own script.

The catalogue is what the Face offers by name ("run pr-list"), so an intent whose own step raises
before doing any work is a capability that is not there. On 2026-10-22 eight of the ninety-one
intents on main were in exactly that state: an inline `python3 -c "…"` inside a YAML block scalar
has its indentation stripped with the block, so every loop body fell back to column 0.

Proved both ways, because a gate that cannot fail is not a gate: the real catalogue passes, and a
catalogue with one broken intent is refused and named.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINT = REPO / "bin" / "intent-lint"
INTENTS = REPO / "platform" / "estate" / "intents"

GOOD = """\
name: fixture-good
description: one step that a shell can run and python can compile
args:
  repo: {type: string, default: "chidionyema/idp"}
steps:
  - name: list
    cmd: |
      echo "{{repo}}" | python3 -c "
      import sys
      for line in sys.stdin:
          print(line.strip())
      "
"""

# The shape that was on main: the loop body sits at the same indent as the `for`, because the
# block scalar took the indentation with it.
BROKEN = """\
name: fixture-broken
description: the loop body lost its indentation to the block scalar
steps:
  - name: list
    cmd: |
      echo '[]' | python3 -c "
      import json, sys
      items = json.load(sys.stdin)
      for item in items:
      print(item)
      "
"""


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LINT), *args], capture_output=True, text=True, check=False
    )


def test_every_intent_in_the_catalogue_runs_its_own_script() -> None:
    """The finding this lint exists for: on main, 8 of 91 intents could not."""
    proc = run()
    assert proc.returncode == 0, (
        f"intents that cannot run their own script:\n{proc.stdout}{proc.stderr}"
    )
    assert "cannot run their own script" in proc.stdout
    assert " 0 cannot run" in proc.stdout, proc.stdout


def test_a_broken_intent_is_refused_and_named(tmp_path: Path) -> None:
    (tmp_path / "good.yaml").write_text(GOOD)
    (tmp_path / "broken.yaml").write_text(BROKEN)
    proc = run("--intents", str(tmp_path))
    assert proc.returncode == 1, proc.stdout
    assert "broken.yaml" in proc.stdout
    assert "good.yaml" not in proc.stdout, (
        "a runnable intent must not be reported as broken"
    )
    assert "cannot run their own script" in proc.stdout


def test_a_runnable_intent_alone_passes(tmp_path: Path) -> None:
    """The other half of the two-way proof: the lint is not simply always red."""
    (tmp_path / "good.yaml").write_text(GOOD)
    proc = run("--intents", str(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "1 intents in" in proc.stdout
    assert " 0 cannot run" in proc.stdout


def test_an_unparseable_intent_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    (tmp_path / "not-yaml.yaml").write_text("steps: [\n  - name: x\n   cmd: |\n")
    proc = run("--intents", str(tmp_path))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "not-yaml.yaml" in proc.stdout
    assert "yaml:" in proc.stdout


def test_no_intents_at_all_is_an_error_not_a_pass(tmp_path: Path) -> None:
    """An empty directory must not read as 'every intent is fine'."""
    proc = run("--intents", str(tmp_path))
    assert proc.returncode == 2, proc.stdout
    assert "no intents found" in proc.stderr


def test_a_missing_directory_is_an_error(tmp_path: Path) -> None:
    proc = run("--intents", str(tmp_path / "absent"))
    assert proc.returncode == 2
    assert "no such directory" in proc.stderr


def test_the_ref_mode_reads_what_a_ref_has() -> None:
    proc = run("--ref", "HEAD", "-q")
    assert proc.returncode in (0, 1), proc.stderr
    assert "intents," in proc.stdout
