"""crew#586 CP3: the hourly conscience run keeps one issue per red tenet and never two.

Shape tests on .github/workflows/conscience.yml: it is scheduled, it looks the issue up by
exact title before creating, it closes on green, and only BLIND (exit 2) fails the run.
"""
import pathlib
import yaml

WF = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "conscience.yml"


def load():
    return yaml.safe_load(WF.read_text()), WF.read_text()


def test_hourly_schedule_and_dispatch():
    wf, _ = load()
    on = wf.get("on") or wf.get(True)
    assert on["schedule"][0]["cron"].split()[1] == "*" and "workflow_dispatch" in on


def test_lookup_by_exact_title_before_create():
    _, text = load()
    assert 'select(.title == \\"$title\\")' in text and "gh issue create" in text
    assert text.index("gh issue list") < text.index("gh issue create")


def test_green_closes_and_only_blind_fails():
    _, text = load()
    assert "gh issue close" in text
    assert '[ "$rc" -ne 2 ]' in text[text.rindex("- name:"):]   # the last step, never the grade step (run 33200707064)
    # run 33198014582: gating every later step on rc != 2 hid the founder line, the issues and the page
    # behind one BLIND row. The run stays red; the surface still ships from the receipt.
    assert "steps.grade.outputs.rc != '2'" not in text
    assert text.count("if: ${{ steps.grade.outputs.rc != ''") == 4 and "cancelled()" not in text  # collector, issues, founder line, page
    assert "conscience: $tenet is $other" in text and "for other in red BLIND" in text


def test_receipt_is_kept():
    wf, _ = load()
    steps = wf["jobs"]["grade"]["steps"]
    assert any("upload-artifact" in (s.get("uses") or "") and "conscience.json" in str(s.get("with")) for s in steps)
