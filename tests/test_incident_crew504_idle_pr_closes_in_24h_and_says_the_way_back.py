"""Incident test, crew#504 CP2: the 7+7-day stale window let 113 PRs pile up in a day.

Both ways: the idp workflow and the rollout copy are the same file, the window is 24h, the close
comment names both ways back (reopen, Blocked-by), and the crew#299 14-day text is gone.
"""
import os

import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(HERE, ".github", "workflows", "stale.yml")
ROLLOUT = os.path.join(HERE, "platform", "github", "workflows", "stale.yml")


def _with():
    wf = yaml.safe_load(open(LIVE))
    return wf["jobs"]["stale"]["steps"][0]["with"], wf


def test_window_is_24h_and_hourly():
    w, wf = _with()
    assert float(w["days-before-pr-stale"]) + float(w["days-before-pr-close"]) == 1.0
    assert isinstance(w["days-before-pr-close"], int), "actions/stale parseInt()s the close window"
    assert w["days-before-issue-stale"] == -1 and w["days-before-issue-close"] == -1
    assert wf[True]["schedule"][0]["cron"].split()[1] == "*", "must run hourly, not daily"


def test_close_comment_names_both_ways_back():
    w, _ = _with()
    assert "gh pr reopen" in w["close-pr-message"]
    assert "Blocked-by:" in w["close-pr-message"] and "wake-blocked" in w["close-pr-message"]
    assert "14 days" not in w["close-pr-message"]
    assert w["delete-branch"] is False, "a kept branch is what wake-blocked reopens"


def test_rollout_copy_is_the_live_file():
    assert open(LIVE).read() == open(ROLLOUT).read()
