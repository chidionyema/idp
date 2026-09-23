"""Incident, ruling R62 (2026-08-31): the founder found 13 leftover worktrees inside the idp
folder and 325 registered against the repository, and said "we never cleannup every pr nust
have cleanup section nandatory ... and i will defie what it says". Work piled up because no
pull request accounted for what it leaves behind. policy/operating_model.rego rule
`cleanup_section` refuses a body with no `## Cleanup` heading (or `Cleanup:` line).

Presence only: he defines the section's required content; until that lands the rule says
nothing about what the section must contain. Grandfathered like `optimised_plan`: a pull
request opened before the rule existed is not refused.
Rung 4: conftest on a fixture; opens no socket."""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy"
FIX = POLICY / "fixtures"

pytestmark = pytest.mark.skipif(
    shutil.which("conftest") is None, reason="conftest not installed"
)


def _rules(path: pathlib.Path) -> set[str]:
    out = subprocess.run(
        [
            "conftest",
            "test",
            "--parser",
            "json",
            "-p",
            str(POLICY),
            "-o",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return {
        f["msg"].split(" | ")[0]
        for r in json.loads(out)
        for f in (r.get("failures") or [])
    }


def _pr(
    tmp_path, body_suffix: str = "", created_at: str | None = "2026-09-01T00:00:00Z"
) -> pathlib.Path:
    d = json.loads((FIX / "opmodel-no-optimised.json").read_text())
    d["pr"]["body"] += body_suffix
    if created_at is None:
        d["pr"].pop("createdAt", None)
    else:
        d["pr"]["createdAt"] = created_at
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    return p


def test_a_body_with_no_cleanup_section_is_refused(tmp_path):
    assert "rule=cleanup_section" in _rules(_pr(tmp_path))


def test_a_cleanup_heading_passes(tmp_path):
    body = "\n## Cleanup\nRemoves the wt612 worktree; nothing else left behind.\n"
    assert "rule=cleanup_section" not in _rules(_pr(tmp_path, body))


def test_a_cleanup_line_passes(tmp_path):
    assert "rule=cleanup_section" not in _rules(
        _pr(tmp_path, "\nCleanup: nothing to clean\n")
    )


def test_a_pull_request_opened_before_the_rule_is_not_refused(tmp_path):
    assert "rule=cleanup_section" not in _rules(
        _pr(tmp_path, created_at="2026-08-30T00:00:00Z")
    )


def test_a_report_with_no_opening_time_is_judged(tmp_path):
    assert "rule=cleanup_section" in _rules(_pr(tmp_path, created_at=None))
