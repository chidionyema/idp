"""Incident crew#554 (2026-08-28 02:38Z): every hourly cron on the GitHub account fired 1-3 times in
24h (verify-drill 1/24, trace-drill 2/24, login-drill 2/24, stale 1/24). The catalogue's green ages
came from push runs; nothing was scheduling the drills. platform/drills/drill-dispatcher.yaml runs
them on the estate's clock as the GitHub App. Rules (rung 2 over the manifests, rung 4 for drift):
  1. the dispatcher is a restricted CronJob on the pinned image every estate CronJob uses, hourly,
     Forbid, authenticating as the App Secret Flux's githubdispatch Provider already reads;
  2. WORKFLOWS is exactly the catalogue's non-pending workflows, each with its cron -- a drill
     added to the catalogue without the dispatcher, or the reverse, or a changed schedule, is a diff;
  3. the repo slug comes from estate-config (LAW 46), never a literal in platform/;
  4. the embedded dispatcher compiles, and its plan() skips a workflow the CLOCK already ran this
     hour (GitHub's own schedule, or this Job) and dispatches one that did not;
  5. the dispatcher and bin/idp-drills-row agree on what the clock is. They disagreed until
     2026-08-28: plan() treated any run as coverage while scheduled_firings() counted only
     `schedule` and App `workflow_dispatch`, so every hour a push happened to cover was an hour
     the dispatcher skipped and the drills row then reported as a dropped schedule. Measured over
     24h that was 16 of login-drill's 24 hours, 13 of trace-drill's and 11 of verify-drill's, and
     the row's 80% bar was unreachable on any repo with pushes. Rule 5 is the guard: one
     definition, asserted on both sides, so the two cannot drift apart again (LAW 45)."""
from __future__ import annotations

import pathlib
import re
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/drills/drill-dispatcher.yaml"


def _cronjob() -> dict:
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d and d["kind"] == "CronJob"][0]


def _container() -> dict:
    return _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]


def _script() -> str:
    args = _container()["args"][0]
    return args[args.index("<<'PY'\n") + len("<<'PY'\n"):args.rindex("\nPY")]


def _catalogue_workflows() -> set[str]:
    """Every non-pending catalogue drill as `<workflow>=<cron, spaces as _>` -- the shape WORKFLOWS
    carries, so the dispatcher's period is the catalogue's schedule and nothing else."""
    out = set()
    for d in yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]:
        if d.get("pending"):
            continue
        assert re.fullmatch(r"\d+|\*/(15|30)", d["schedule"].split()[0]), d["name"]
        out.add("%s=%s" % (d["workflow"], d["schedule"].replace(" ", "_")))
    return out


def test_dispatcher_is_a_restricted_hourly_cronjob_on_the_pinned_image() -> None:
    cj = _cronjob()
    assert cj["metadata"]["namespace"] == "flux-system", "the github-app Secret lives in flux-system"
    minute, hour, *_ = cj["spec"]["schedule"].split()
    minutes = [int(m) for m in minute.split(",")]
    assert hour == "*" and cj["spec"]["concurrencyPolicy"] == "Forbid"
    # crew#648: four firings an hour, 15 apart, so a `*/15` catalogue row is covered on the estate's clock
    assert len(minutes) == 4 and {b - a for a, b in zip(minutes, minutes[1:])} == {15}, cj["spec"]["schedule"]
    pod = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert pod["securityContext"]["runAsNonRoot"] is True and pod["automountServiceAccountToken"] is False
    psc = pod["securityContext"]
    assert psc.get("runAsUser", 0) != 0 and psc.get("fsGroup") == psc["runAsUser"], "the 0400 Secret is readable only when the pod group owns it (REWORK 9b57aef)"
    c = _container()
    sc = c["securityContext"]
    assert sc["readOnlyRootFilesystem"] and sc["capabilities"] == {"drop": ["ALL"]} and not sc["allowPrivilegeEscalation"]
    assert c["image"] in (ROOT / "platform/chaos/backstage-pod-kill.yaml").read_text(), "one pinned image for every estate CronJob"
    assert not any("valueFrom" in e for e in c["env"]), "kyverno secrets-not-from-env-vars: the App identity is files, never env"
    vols = {v["secret"]["secretName"] for v in pod["volumes"] if "secret" in v}
    assert vols == {"github-app"}
    env = {e["name"]: e["value"] for e in c["env"]}
    assert env["GITHUB_APP_DIR"] in {vm["mountPath"] for vm in c["volumeMounts"] if vm["name"] == "github-app"}
    es = [d for d in yaml.safe_load_all((ROOT / "platform/alerts-github/github-app.yaml").read_text()) if d][0]
    assert es["spec"]["target"]["name"] == "github-app" and es["metadata"]["namespace"] == "flux-system"
    assert "drill-dispatcher.yaml" in (ROOT / "platform/drills/kustomization.yaml").read_text()


def test_workflows_are_exactly_the_catalogues_drills_with_their_crons() -> None:
    env = {e["name"]: e.get("value") for e in _container()["env"]}
    assert set(env["WORKFLOWS"].split()) == _catalogue_workflows()
    for entry in env["WORKFLOWS"].split():
        wf, _cron = entry.split("=", 1)
        text = (ROOT / ".github/workflows" / wf).read_text()
        assert "workflow_dispatch" in text, f"{wf} cannot be dispatched"


def test_a_slow_cron_is_covered_once_per_period_after_its_own_firing_time() -> None:
    """crew#554 CP4, verify-drill 33234050516 (2026-08-29 04:32Z): `estate-escrow.yml fired 0 of 4
    promised in 24h (cron 29 */6 * * *, 0 dispatched by the App)` and `kyverno-secrets-drill.yml
    last green 34.0h ago, older than 26h (cron 41 7 * * *)`. GitHub dropped both schedules and the
    dispatcher only covered hourly crons. Now the period is the cron's: skip until the cron's own
    minute in the period, skip if the clock ran in the period, else dispatch -- never twice."""
    import pytest

    ns: dict = {"__name__": "test"}
    exec(compile(_script(), str(MANIFEST), "exec"), ns)  # noqa: S102 - the manifest's own program
    plan, six, daily, weekly = ns["plan"], "29 */6 * * *", "41 7 * * *", "23 5 * * 1"
    assert ns["period_hours"](six) == 6 and ns["period_hours"](daily) == 24 and ns["period_hours"](weekly) == 168
    # 6-hourly: not due at 00:03, due at 01:03; a clock run at 00:29 covers the whole 00-06 period
    assert plan([], datetime(2026, 8, 29, 0, 3, tzinfo=timezone.utc), six) == "skipped: not due until 2026-08-29T00:29:00Z"
    assert plan([], datetime(2026, 8, 29, 1, 3, tzinfo=timezone.utc), six) == "dispatch"
    fired = [{"created_at": "2026-08-29T00:29:10Z", "event": "schedule", "id": 3}]
    assert plan(fired, datetime(2026, 8, 29, 5, 3, tzinfo=timezone.utc), six).startswith("skipped: schedule run 3")
    assert plan(fired, datetime(2026, 8, 29, 7, 3, tzinfo=timezone.utc), six) == "dispatch", "the 06-12 period is a new promise"
    # daily 07:41: nothing before 07:41, one dispatch after, none once the clock (or the App) ran today
    assert plan([], datetime(2026, 8, 29, 7, 3, tzinfo=timezone.utc), daily) == "skipped: not due until 2026-08-29T07:41:00Z"
    assert plan([], datetime(2026, 8, 29, 8, 3, tzinfo=timezone.utc), daily) == "dispatch"
    app = [{"created_at": "2026-08-29T08:03:20Z", "event": "workflow_dispatch", "id": 4,
            "triggering_actor": {"login": "estate-agents[bot]"}}]
    assert plan(app, datetime(2026, 8, 29, 23, 3, tzinfo=timezone.utc), daily).startswith("skipped: workflow_dispatch run 4")
    yesterday = [{"created_at": "2026-08-28T07:41:30Z", "event": "schedule", "id": 5}]
    assert plan(yesterday, datetime(2026, 8, 29, 8, 3, tzinfo=timezone.utc), daily) == "dispatch", "yesterday's run is not today's"
    # weekly Monday 05:23 (2026-08-31 is a Monday): 03:03 that Monday is before the firing, Tuesday is after
    assert plan([], datetime(2026, 8, 31, 3, 3, tzinfo=timezone.utc), weekly) == "skipped: not due until 2026-08-31T05:23:00Z"
    assert plan([], datetime(2026, 9, 1, 12, 3, tzinfo=timezone.utc), weekly) == "dispatch"
    # a hand dispatch still does not stand in for the clock, whatever the period
    hand = [{"created_at": "2026-08-29T08:00:00Z", "event": "workflow_dispatch", "id": 6,
             "triggering_actor": {"login": "chidionyema"}}]
    assert plan(hand, datetime(2026, 8, 29, 9, 3, tzinfo=timezone.utc), daily) == "dispatch"
    with pytest.raises(ValueError):
        ns["period_hours"]("*/5 * * * *")


def test_repo_slug_is_estate_config_not_a_literal() -> None:
    env = {e["name"]: e.get("value") for e in _container()["env"]}
    assert env["GITHUB_REPO"] == "${ESTATE_GITHUB_REPO}"
    cfg = yaml.safe_load((ROOT / "clusters/oke/estate-config.yaml").read_text())
    assert re.fullmatch(r"[\w.-]+/[\w.-]+", cfg["data"]["ESTATE_GITHUB_REPO"])
    assert "github.com/" not in MANIFEST.read_text().split("PY\n", 1)[0].replace("api.github.com", "")
    flux = (ROOT / "clusters/oke/platform.yaml").read_text()
    assert "path: ./platform/drills" in flux and "name: estate-config" in flux


def test_plan_skips_a_workflow_that_already_ran_this_hour_and_dispatches_one_that_did_not() -> None:
    ns: dict = {"__name__": "test"}
    exec(compile(_script(), str(MANIFEST), "exec"), ns)  # noqa: S102 - the manifest's own program, main() not called
    now = datetime(2026, 8, 28, 3, 3, tzinfo=timezone.utc)
    assert ns["plan"]([], now) == "dispatch"
    assert ns["plan"]([{"created_at": "2026-08-28T02:23:07Z", "event": "schedule", "id": 1}], now) == "dispatch"
    # the clock ran it this hour, either as GitHub's cron or as this Job: nothing to do
    got = ns["plan"]([{"created_at": "2026-08-28T03:00:41Z", "event": "schedule", "id": 7}], now)
    assert got.startswith("skipped: schedule run 7")
    got = ns["plan"]([{"created_at": "2026-08-28T03:03:02Z", "event": "workflow_dispatch",
                       "id": 8, "triggering_actor": {"login": "estate-agents[bot]"}}], now)
    assert got.startswith("skipped: workflow_dispatch run 8")
    assert ns["PERMISSIONS"] == {"actions": "write", "metadata": "read"}


def test_a_push_or_a_hand_does_not_stand_in_for_the_heartbeat() -> None:
    """The incident this file is named for. Measured 2026-08-28 over 24h: login-drill had a run in
    19 of 24 hours but only 3 were clock-driven -- 16 hours were push-only, skipped by the
    dispatcher and counted as dropped by the drills row. A heartbeat that stops when the pushes
    stop is not a heartbeat, and the hour nobody pushes is the hour it has to cover."""
    ns: dict = {"__name__": "test"}
    exec(compile(_script(), str(MANIFEST), "exec"), ns)  # noqa: S102 - the manifest's own program
    now = datetime(2026, 8, 28, 3, 3, tzinfo=timezone.utc)
    for event, actor in (("push", "chidionyema"), ("pull_request", "chidionyema"),
                         ("workflow_dispatch", "chidionyema")):
        run = {"created_at": "2026-08-28T03:00:41Z", "event": event, "id": 7,
               "triggering_actor": {"login": actor}}
        assert ns["plan"]([run], now) == "dispatch", f"a {event} by {actor} suppressed the heartbeat"
    # and it must still find the clock run when an hour of pushes is stacked in front of it
    noise = [{"created_at": "2026-08-28T03:%02d:00Z" % m, "event": "push", "id": 100 + m,
              "triggering_actor": {"login": "chidionyema"}} for m in range(0, 40, 2)]
    clock = {"created_at": "2026-08-28T03:03:01Z", "event": "schedule", "id": 9}
    assert ns["plan"](noise + [clock], now).startswith("skipped: schedule run 9")
    assert "per_page=30" in _script(), "5 runs is not enough to see past an hour of pushes"


def test_the_dispatcher_and_the_drills_row_agree_on_what_the_clock_is() -> None:
    """Rule 5. Two files decide whether an hour was covered by the clock: the dispatcher's
    by_the_clock() and scheduled_firings() in bin/idp-drills-row. When they disagreed, one
    skipped the hour and the other called it dropped. Neither is allowed to widen alone."""
    ns: dict = {"__name__": "test"}
    exec(compile(_script(), str(MANIFEST), "exec"), ns)  # noqa: S102 - the manifest's own program
    row = (ROOT / "bin/idp-drills-row").read_text()
    sched = row[row.index("def scheduled_firings"):row.index("def scheduled_firings") + 2000]

    cases = [
        ({"event": "schedule", "triggering_actor": {"login": "github"}}, True),
        ({"event": "workflow_dispatch", "triggering_actor": {"login": "estate-agents[bot]"}}, True),
        ({"event": "workflow_dispatch", "triggering_actor": {"login": "chidionyema"}}, False),
        ({"event": "push", "triggering_actor": {"login": "chidionyema"}}, False),
        ({"event": "pull_request", "triggering_actor": {"login": "chidionyema"}}, False),
    ]
    for run, expected in cases:
        assert ns["by_the_clock"](run) is expected, f"dispatcher disagrees on {run['event']}"

    # the row reaches the same verdict, from its own flattened shape
    def row_counts(ev: str, actor: str) -> bool:
        return ev == "schedule" or (ev == "workflow_dispatch" and actor.endswith("[bot]"))

    for run, expected in cases:
        actor = run["triggering_actor"]["login"]
        assert row_counts(run["event"], actor) is expected
    # and the row's source still implements exactly that, so row_counts is not a stale copy
    assert 'ev == "schedule"' in sched
    assert '"[bot]"' in sched and 'ev == "workflow_dispatch"' in sched
    assert "pull_request" not in sched and '== "push"' not in sched


def test_a_fifteen_minute_cron_is_covered_once_per_quarter_hour() -> None:
    """crew#648 (2026-08-30): estate-state.yml (`*/15 * * * *`) never fired in its first three hours
    and ping.yml (`*/5`) fired 10 times in 60h. The dispatcher only knew hours. A `*/N` minute cron
    is an N-minute period due at its start: skipped when the clock ran it in this quarter hour,
    dispatched when it did not, and never dispatched twice in one quarter hour."""
    ns: dict = {}
    exec(_script(), ns)  # noqa: S102 - the manifest's own code is the unit under test
    plan, q = ns["plan"], "*/15 * * * *"
    now = datetime(2026, 8, 30, 10, 18, tzinfo=timezone.utc)
    assert plan([{"created_at": "2026-08-30T10:03:20Z", "event": "schedule", "id": 1}], now, q) == "dispatch"
    got = plan([{"created_at": "2026-08-30T10:15:40Z", "event": "workflow_dispatch", "triggering_actor": {"login": "estate[bot]"}, "id": 2}], now, q)
    assert got.startswith("skipped: workflow_dispatch run 2")
    assert plan([{"created_at": "2026-08-30T10:16:00Z", "event": "push", "id": 3}], now, q) == "dispatch"
    import pytest
    with pytest.raises(ValueError):
        ns["period_hours"]("*/5 * * * *")   # a five-minute promise this Job cannot keep
