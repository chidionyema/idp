"""Incident crew#684 (2026-08-30): the founder said "why is backstage still down". The door was up;
the Ops page's founder tile read "What waits on you could not be read" because docs/founder.json
did not exist on the state branch: catalog-render's 01:58Z schedule never fired (GitHub's cron,
measured on this account: the four ticks before it drifted 40 to 190 minutes, this one was dropped),
and the Mac row that used to follow the inventory tick was retired on 2026-08-27 (crew#516 CP3).
A hand dispatch at 05:06Z then ran in the input's default `dry-run` mode and pushed nothing.

Rules (rung 2 over the files, rung 4 for the dispatcher's own program):
  1. catalog-render is a catalogue row carrying the workflow's own cron, so the drills row grades it
     and platform/drills/drill-dispatcher.yaml runs it on the estate's clock when GitHub does not
     (the crew#554 test already refuses a catalogue row the dispatcher does not carry);
  2. the dispatcher's plan() understands the `58 1,7,13,19` hour list as a 6-hour period
     offset by one hour: not due before the cron's own minute, one dispatch after, none once the
     clock ran in the period;
  3. a dispatch with no inputs publishes: the workflow's mode input has no dry-run default, and both
     the render step and the push step fall back to commit; the portal button passes mode itself.
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/drills/drill-dispatcher.yaml"
WORKFLOW = ROOT / ".github/workflows/catalog-render.yml"
CRON = "58 1,7,13,19 * * *"


def _script() -> str:
    cj = [
        d
        for d in yaml.safe_load_all(MANIFEST.read_text())
        if d and d["kind"] == "CronJob"
    ][0]
    args = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0][
        "args"
    ][0]
    return args[args.index("<<'PY'\n") + len("<<'PY'\n") : args.rindex("\nPY")]


def test_catalog_render_is_a_catalogue_row_with_the_workflows_own_cron() -> None:
    rows = {
        d["name"]: d
        for d in yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]
    }
    row = rows["catalog-render"]
    assert row["workflow"] == "catalog-render.yml" and not row.get("pending")
    wf = yaml.safe_load(WORKFLOW.read_text())
    assert [c["cron"] for c in wf[True]["schedule"]] == [row["schedule"]] == [CRON]
    assert row["max_age_hours"] >= 6 + 1, "six-hourly plus GitHub's slack"


def test_the_dispatcher_covers_the_hour_list_once_per_period_after_its_minute() -> None:
    ns: dict = {"__name__": "test"}
    exec(compile(_script(), str(MANIFEST), "exec"), ns)  # noqa: S102 - the manifest's own program
    plan, period = ns["plan"], ns["period_hours"]
    assert period(CRON) == 6
    utc = timezone.utc
    assert (
        plan([], datetime(2026, 8, 30, 1, 3, tzinfo=utc), CRON)
        == "skipped: not due until 2026-08-30T01:58:00Z"
    )
    assert plan([], datetime(2026, 8, 30, 2, 3, tzinfo=utc), CRON) == "dispatch", (
        "the 01:58 tick was dropped: the 02:03 Job covers it"
    )
    fired = [{"created_at": "2026-08-30T01:58:40Z", "event": "schedule", "id": 1}]
    assert plan(fired, datetime(2026, 8, 30, 6, 3, tzinfo=utc), CRON).startswith(
        "skipped: schedule run 1"
    )
    assert plan(fired, datetime(2026, 8, 30, 8, 3, tzinfo=utc), CRON) == "dispatch", (
        "07-13 is a new promise"
    )
    # the period holding 00:03 began at 19:00 the day before; its firing at 19:58 covers it
    last_night = [{"created_at": "2026-08-29T19:58:12Z", "event": "schedule", "id": 2}]
    assert plan(last_night, datetime(2026, 8, 30, 0, 3, tzinfo=utc), CRON).startswith(
        "skipped: schedule run 2"
    )
    assert plan([], datetime(2026, 8, 30, 0, 3, tzinfo=utc), CRON) == "dispatch"
    import pytest

    with pytest.raises(ValueError):
        period("58 1,7,13 * * *")
