"""Incident, 2026-08-26: the operating-model gate refused idp#191 with
`Drill: chaos-pod-kill names no entry in drills/catalogue.yaml` although that PR added the row.
bin/pr-report read the catalogue from IDP_ROOT (main) only, so the rule's own fix ("add the
drill in this PR") could not pass: a guard refusing correct work (LAW 38). Rung 4.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-drill-names"


def _names(*paths: Path) -> list[str]:
    out = subprocess.run([str(TOOL), *map(str, paths)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_incident_drill_added_in_the_pr_is_a_catalogued_name(tmp_path: Path) -> None:
    main = tmp_path / "main.yaml"
    main.write_text("drills:\n  - name: oke-check\n  - name: login-drill\n")
    head = tmp_path / "head.yaml"
    head.write_text("drills:\n  - name: oke-check\n  - name: login-drill\n  - name: chaos-pod-kill\n")
    # incident shape: main alone does not know the new row
    assert "chaos-pod-kill" not in _names(main)
    # fixed shape: main plus the PR head does, and nothing is duplicated
    got = _names(main, head)
    assert got == ["oke-check", "login-drill", "chaos-pod-kill"]


def test_unreadable_catalogue_adds_nothing_and_is_named(tmp_path: Path) -> None:
    main = tmp_path / "main.yaml"
    main.write_text("drills:\n  - name: oke-check\n")
    out = subprocess.run([str(TOOL), str(main), str(tmp_path / "missing.yaml")], capture_output=True, text=True)
    assert out.returncode == 0
    assert json.loads(out.stdout) == ["oke-check"]
    assert "missing.yaml" in out.stderr
