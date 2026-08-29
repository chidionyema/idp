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


# Second incident, same morning (2026-08-29): the rule above landed on main at 02:28:20Z and by
# 07:03Z it had turned nine open pull requests red -- prospector 770/768/767/711/701 and four on
# crew -- none of which could have carried a counted line, because the law did not exist when they
# were written. The only way through was to invent an `Optimised:` line for a plan nobody counted.
# LAW 38: a guard that refuses correct work is an outage. The rule now reads `pr.createdAt`.
LAW51_LANDED = "2026-08-29T02:28:20Z"   # commit dca2a929 on main


def _with_created(tmp_path, created: str | None) -> pathlib.Path:
    """The no-optimised fixture, opened at a given moment. None removes the field entirely."""
    d = json.loads((FIX / "opmodel-no-optimised.json").read_text())
    if created is None:
        d["pr"].pop("createdAt", None)
    else:
        d["pr"]["createdAt"] = created
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    return p


@pytest.mark.parametrize("created", [
    "2026-08-28T14:03:11Z",   # prospector#770's shape: opened the day before
    "2026-08-29T02:28:19Z",   # one second before the commit landed
])
def test_a_pr_opened_before_the_law_is_not_judged(tmp_path, created):
    assert "rule=optimised_plan" not in _rules(_with_created(tmp_path, created))


@pytest.mark.parametrize("created", [
    LAW51_LANDED,             # the commit's own second: the law exists, so it binds
    "2026-08-29T09:00:00Z",
])
def test_a_pr_opened_once_the_law_existed_is_still_judged(tmp_path, created):
    assert "rule=optimised_plan" in _rules(_with_created(tmp_path, created))


def test_a_report_with_no_created_field_is_still_judged(tmp_path):
    """Absent only on a hand-built fixture or an old report; the safe default is to grade."""
    assert "rule=optimised_plan" in _rules(_with_created(tmp_path, None))


def test_the_age_exemption_does_not_excuse_any_other_rule(tmp_path):
    """An old PR is spared this rule alone -- it is not a skeleton key for the whole gate."""
    d = json.loads((FIX / "opmodel-no-optimised.json").read_text())
    d["pr"]["createdAt"] = "2026-08-01T00:00:00Z"
    d["pr"]["body"] = "nothing here at all"          # trips architecture_laws and its neighbours
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    fired = _rules(p)
    assert "rule=optimised_plan" not in fired
    assert fired, "the rest of the gate went quiet: the exemption is too wide"


def test_incident_the_image_bump_body_passes_the_rule(tmp_path):
    """Incident, 2026-08-29: idp#719 (flux/image-updates, 30 commits, auto-merge armed 05:31Z) never
    merged because the bot body bin/idp-image-update-pr writes carried no `Optimised:` line and the
    gate refused every cycle, so the portal stayed on a stale image. The literal line in the script
    is graded by the real rule here; a body without it is still refused (the LAW 38 other way)."""
    script = (ROOT / "bin" / "idp-image-update-pr").read_text()
    line = next(l.strip().strip('"\\ ') for l in script.splitlines() if l.strip().startswith('"Optimised:'))
    assert "rule=optimised_plan" not in _rules(_with_body(tmp_path, "\n" + line + "\n")), line
    assert "rule=optimised_plan" in _rules(_with_body(tmp_path, "\n"))
