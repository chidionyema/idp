"""Incident, crew#584 (2026-08-29): the founder had to say "optimise before build" and then "note this
process down as it will become law" because sessions executed the first plan they had. LAW 51 (ruling R50)
makes the counted plan a precondition; this gate is the protocol behind the law (LAW 44): a PR body
without a counted `Optimised:` line is refused by policy/operating_model.rego rule `optimised_plan`.
Trial receipt: crew#584 5459773413 (go -> three PRs merged in 12 min against a 45-minute estimate).
Rung 4: conftest on a fixture; opens no socket."""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy"
FIX = POLICY / "fixtures"

pytestmark = pytest.mark.skipif(shutil.which("conftest") is None, reason="conftest not installed")


def _rules(path: pathlib.Path) -> set[str]:
    out = subprocess.run(["conftest", "test", "--parser", "json", "-p", str(POLICY), "-o", "json", str(path)],
                         capture_output=True, text=True, check=False).stdout
    return {f["msg"].split(" | ")[0] for r in json.loads(out) for f in (r.get("failures") or [])}


def _with_body(tmp_path, line: str) -> pathlib.Path:
    d = json.loads((FIX / "opmodel-no-optimised.json").read_text())
    d["pr"]["body"] += line
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    return p


def test_a_body_without_the_line_is_refused():
    assert "rule=optimised_plan" in _rules(FIX / "opmodel-no-optimised.json")


def test_a_sentence_is_refused():
    assert "rule=optimised_plan" in _rules(FIX / "opmodel-optimised-sentence.json")


@pytest.mark.parametrize("line", [
    "Optimised: 7 PRs -> 3, 7 round trips -> 2; cut: typed floors, git already holds the sums\n",
    "Optimised: 12 steps -> 4 (2 parallel), 3 CI round trips -> 1; cut: rebuild step, image unchanged\n",
])
def test_two_counts_and_a_cut_pass(tmp_path, line):
    assert "rule=optimised_plan" not in _rules(_with_body(tmp_path, line))


def test_an_arrow_without_numbers_is_refused(tmp_path):
    assert "rule=optimised_plan" in _rules(_with_body(tmp_path, "Optimised: slow -> fast; cut: things\n"))


def test_the_ok_fixture_still_passes():
    assert not _rules(FIX / "opmodel-ok.json")
