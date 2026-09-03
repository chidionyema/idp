"""Incident, crew#584 (2026-08-29): the founder had to say "optimise before build" and then "note this
process down as it will become law" because sessions executed the first plan they had. LAW 51 (ruling R50)
makes the counted plan a precondition; this gate is the protocol behind the law (LAW 44): a PR body
without a counted `Optimised:` line is refused by policy/operating_model.rego rule `optimised_plan`.
Trial receipt: crew#584 5459773413 (go -> three PRs merged in 12 min against a 45-minute estimate).
Rung 4: conftest on a fixture; opens no socket."""

import json
import os
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


@pytest.mark.parametrize(
    "line",
    [
        "Optimised: 7 PRs -> 3, 7 round trips -> 2; cut: typed floors, git already holds the sums\n",
        "Optimised: 12 steps -> 4 (2 parallel), 3 CI round trips -> 1; cut: rebuild step, image unchanged\n",
    ],
)
def test_two_counts_and_a_cut_pass(tmp_path, line):
    assert "rule=optimised_plan" not in _rules(_with_body(tmp_path, line))


def test_the_ok_fixture_still_passes():
    assert not _rules(FIX / "opmodel-ok.json")


# Second incident, same morning (2026-08-29): the rule above landed on main at 02:28:20Z and by
# 07:03Z it had turned nine open pull requests red -- prospector 770/768/767/711/701 and four on
# crew -- none of which could have carried a counted line, because the law did not exist when they
# were written. The only way through was to invent an `Optimised:` line for a plan nobody counted.
# LAW 38: a guard that refuses correct work is an outage. The rule now reads `pr.createdAt`.
LAW51_LANDED = "2026-08-29T02:28:20Z"  # commit dca2a929 on main


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


@pytest.mark.parametrize(
    "created",
    [
        "2026-08-28T14:03:11Z",  # prospector#770's shape: opened the day before
        "2026-08-29T02:28:19Z",  # one second before the commit landed
    ],
)
def test_a_pr_opened_before_the_law_is_not_judged(tmp_path, created):
    assert "rule=optimised_plan" not in _rules(_with_created(tmp_path, created))


@pytest.mark.parametrize(
    "created",
    [
        LAW51_LANDED,  # the commit's own second: the law exists, so it binds
        "2026-08-29T09:00:00Z",
    ],
)
def test_a_pr_opened_once_the_law_existed_is_still_judged(tmp_path, created):
    assert "rule=optimised_plan" in _rules(_with_created(tmp_path, created))


def test_a_report_with_no_created_field_is_still_judged(tmp_path):
    """Absent only on a hand-built fixture or an old report; the safe default is to grade."""
    assert "rule=optimised_plan" in _rules(_with_created(tmp_path, None))


def test_the_age_exemption_does_not_excuse_any_other_rule(tmp_path):
    """An old PR is spared this rule alone -- it is not a skeleton key for the whole gate."""
    d = json.loads((FIX / "opmodel-no-optimised.json").read_text())
    d["pr"]["createdAt"] = "2026-08-01T00:00:00Z"
    d["pr"]["body"] = (
        "nothing here at all"  # trips architecture_laws and its neighbours
    )
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
    line = next(
        l.split("=", 1)[1].strip('"')
        for l in script.splitlines()
        if l.startswith('OPTIMISED="Optimised:')
    )
    assert "rule=optimised_plan" not in _rules(
        _with_body(tmp_path, "\n" + line + "\n")
    ), line
    assert "rule=optimised_plan" in _rules(_with_body(tmp_path, "\n"))


def _fake_gh(tmp_path, body: str):
    """A `gh` that knows one open pull request (#719) with `body`, records every `pr edit` body to
    edits.txt, and answers the rest of the script's calls with what a clean run needs."""
    b = tmp_path / "bin"
    b.mkdir(exist_ok=True)
    (tmp_path / "body.txt").write_text(body)
    gh = b / "gh"
    gh.write_text(
        '#!/usr/bin/env bash\ncase "$1 $2" in\n'
        "  'pr list') echo 719;;\n"
        '  \'pr view\') case "$*" in *mergeable*) echo MERGEABLE;; *) cat "$BODY_FILE";; esac;;\n'
        '  \'pr edit\') shift 4; printf \'%s\' "$1" > "$EDIT_FILE"; printf \'%s\' "$1" > "$BODY_FILE";;\n'
        "  'pr merge') ;;\n"
        '  *) echo "unexpected gh $*" >&2; exit 9;;\nesac\n'
    )
    gh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "BODY_FILE": str(tmp_path / "body.txt"),
        "EDIT_FILE": str(tmp_path / "edits.txt"),
        "MERGEABLE_WAIT": "0",
    }
    return subprocess.run(
        ["bash", str(ROOT / "bin" / "idp-image-update-pr")],
        env=env,
        capture_output=True,
        text=True,
    )


def test_incident_idp719_an_old_body_gains_the_line_on_the_next_push(tmp_path):
    """Incident, 2026-08-29 08:12Z: idp#744 fixed the create path, but idp#719 was opened before it,
    kept its old body on every controller push, and operating-model-gate refused it again
    (run 33242579402, rule=optimised_plan). An existing body without the line is refreshed."""
    r = _fake_gh(
        tmp_path, "Written by image-automation-controller.\n\nDrill: login-drill\n"
    )
    assert r.returncode == 0, r.stdout + r.stderr
    edited = (tmp_path / "edits.txt").read_text()
    assert (
        "Written by image-automation-controller." in edited
        and "\nOptimised: 1 -> 1 steps" in edited
    )
    assert "rule=optimised_plan" not in _rules(_with_body(tmp_path, edited))
    assert "body gained the Optimised line" in r.stdout


VERIFY = "Verify: `grep -rn imagepolicy platform/ clusters/ --include=*.yaml`"


def test_a_body_that_already_carries_both_lines_is_left_alone(tmp_path):
    """Two backfills now run on every controller push, `Optimised:` and `Verify:` (idp#1046, the
    same class one gate later), so "left alone" means neither of them found anything to add."""
    r = _fake_gh(
        tmp_path,
        "Written by image-automation-controller.\n\nOptimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing\n"
        + VERIFY
        + "\n",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (tmp_path / "edits.txt").exists()


def test_an_old_body_gains_the_verify_line_too(tmp_path):
    """Same incident shape as idp#719 one gate later: verify-claims.yml refuses a pull request
    touching platform/ or clusters/ with no `Verify:` line, and the deploy pull request touches
    both. A body opened before that gate keeps failing it on every controller push unless the
    script backfills, and the notice goes to stderr because the last line of stdout is the verdict
    the workflow reads."""
    r = _fake_gh(
        tmp_path,
        "Written by image-automation-controller.\n\nOptimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing\n",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert VERIFY in (tmp_path / "edits.txt").read_text()
    assert "body gained the Verify line" in r.stderr


# Third incident, 2026-08-31, found while clearing the open queue on chidionyema/idp. Three of the
# ten open pull requests were refused by rule=optimised_plan alone, for two reasons neither of
# which is "nobody planned the work":
#
#   idp#1012 carried a real counted plan -- "Optimised: 4 -> 2 steps, 3 -> 1 round trip. Cut: ..."
#   -- written with U+2192 for the arrow and a full stop before Cut. The rule matched the BYTES of
#   an ASCII arrow, not the property it says it grades (a number on each side of an arrow and a cut
#   clause), so it refused a correct body. LAW 38.
#
#   idp#726 and idp#797 are scheduled renders. bin/catalog-render and .github/workflows/
#   conscience.yml write their bodies, and neither was taught LAW 51 -- exactly the idp#719 shape
#   already recorded above, so the daily jobs piled up pull requests that could never go green.
#   Both generators now write the line on create AND refresh an existing body that lacks it.


@pytest.mark.parametrize(
    "line",
    [
        # idp#1012's line, verbatim in shape: unicode arrow, full stop, capital Cut.
        "Optimised: 4 \u2192 2 steps, 3 \u2192 1 round trip. Cut: the commit was cherry-picked, not re-attached\n",
        "Optimised: 4 -> 2 steps, 3 -> 1 round trips. Cut: one render\n",
        "Optimised: 4 \u2192 2 steps, 3 \u2192 1 round trips; cut: one render\n",
    ],
)
def test_a_unicode_arrow_or_a_full_stop_is_the_same_plan(tmp_path, line):
    assert "rule=optimised_plan" not in _rules(_with_body(tmp_path, line))


@pytest.mark.parametrize(
    "line",
    [
        "Optimised: slow \u2192 fast. Cut: things\n",  # an arrow, still no counts
        "Optimised: 4 \u2192 2 steps, 3 \u2192 1 round trip\n",  # counts, no cut clause
    ],
)
def test_widening_the_arrow_did_not_widen_the_rest(tmp_path, line):
    assert "rule=optimised_plan" in _rules(_with_body(tmp_path, line))


def _generated_line(text: str) -> str:
    """The one `Optimised:` line a generator writes, taken from the generator itself."""
    hits = [l for l in text.splitlines() if "Optimised: 1 -> 1 steps" in l]
    assert len(hits) >= 1, "the generator no longer writes an Optimised line"
    i = hits[0].index("Optimised: 1 -> 1 steps")
    return hits[0][i:].split('"')[0]


@pytest.mark.parametrize(
    "path", ["bin/catalog-render", ".github/workflows/conscience.yml"]
)
def test_incident_a_scheduled_render_carries_the_line(tmp_path, path):
    """The literal line each generator writes is graded by the real rule, both ways."""
    line = _generated_line((ROOT / path).read_text())
    assert "rule=optimised_plan" not in _rules(
        _with_body(tmp_path, "\n" + line + "\n")
    ), line
    assert "rule=optimised_plan" in _rules(_with_body(tmp_path, "\n"))
