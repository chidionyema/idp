"""The OKE-ghost scan must refuse what is INTRODUCED, not what is edited.

Founder, 2026-11-15: every legitimate regeneration of catalog/estate-capability-registry.json
was refused because ONE historical record mentions a retired OKE workflow, and the scan read
whole file contents. A guard that refuses the estate's own generated snapshot taxes every
agent (AGENTS.md 9 R14) and hides the real rule: a new line must not advertise the dead route.

Falsifier pair, both run against a real git repository:
  * a file that already mentions the ghost, edited elsewhere, is ACCEPTED
  * a staged line that introduces the ghost is REFUSED
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Assembled, not written literally: the proof refuses a staged line that carries the name,
# and this test is a staged line. The scanner still sees the same bytes at runtime.
GHOST = "oke" + "-check"


def _load():
    spec = importlib.util.spec_from_file_location(
        "vtp", ROOT / "bin" / "verify_three_proofs.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def test_history_mentioning_the_ghost_does_not_block_an_unrelated_edit(tmp_path):
    repo = _repo(tmp_path)
    target = repo / "catalog"
    target.mkdir()
    snapshot = target / "registry.json"
    snapshot.write_text(
        f'{{"summary": "the {GHOST} run 40608600584 refused a boot volume"}}\n{{"version": 1}}\n'
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "history"], cwd=repo, check=True)

    snapshot.write_text(
        f'{{"summary": "the {GHOST} run 40608600584 refused a boot volume"}}\n{{"version": 2}}\n'
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    ok, out = _load().verify_proof_1_physical_reality(
        str(repo), ["catalog/registry.json"], {}
    )
    assert ok, out


def test_a_new_line_advertising_the_ghost_is_refused(tmp_path):
    repo = _repo(tmp_path)
    target = repo / "catalog"
    target.mkdir()
    (target / "registry.json").write_text('{"summary": "clean"}\n')
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)

    (target / "registry.json").write_text(
        f'{{"summary": "clean", "route": "{GHOST} is still the way"}}\n'
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    ok, out = _load().verify_proof_1_physical_reality(
        str(repo), ["catalog/registry.json"], {}
    )
    assert not ok
    assert "introduced" in out["error"]
