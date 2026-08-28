"""crew#527 lane process: a scheduled grader that exits non-zero to report a finding must say so on
its row, or the circuit breaker turns it dark after three findings runs and nobody is told.

Measured 2026-08-28 07:2xZ: `bin/scheduler-status` reported `open circuits: 2 ai.aiden.watch
com.chidionyema.graphify-sweep`. Run by hand, `graphify_sweep.py --fix --root ~/dev/code` printed
`repos 32 FRESH 0 STALE 0 ABSENT 29`, `HOOKS X ...` and `VERDICT: X` and exited 1 — it swept fine
and found holes. The row carried no `ok_exit`, so three findings runs read as three crashes and the
row stopped running: the sweep that exists to catch missing graphs was itself missing.

idp#532 closed the same class this morning on com.founder.board/ingit/lawenforcement. That fix was
three named rows, so the fourth instance opened a breaker eight hours later. This test is the sweep
LAW 45 asks for: it holds over EVERY row, not the ones already found.

The second half is the half that was silently wrong. `ok_exit` is read by the scheduler and keeps
the breaker closed; `HC_FINDINGS_EXIT` is read by hc-wrap.sh and decides which healthcheck the
non-zero exit fails. A row that declares only `ok_exit` and still goes through hc-wrap pings its
LIVENESS check as failed on every findings run: the breaker holds, and the dead-man alert cries
wolf instead. com.estate.costsentinel, every 15 minutes, was doing exactly that.
"""
import pathlib

import yaml

SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "scheduler" / "schedule.yml"
JOBS = yaml.safe_load(SCHEDULE.read_text())["jobs"]


def _hc_wrapped(job):
    cmd = [str(c) for c in (job.get("command") or [])]
    return bool(cmd) and cmd[0].endswith("hc-wrap.sh")


def test_the_graphify_sweep_findings_exit_is_declared_on_its_row():
    job = JOBS["com.chidionyema.graphify-sweep"]
    assert _hc_wrapped(job) and job["command"][1] == "graphify-sweep"
    assert job["ok_exit"] == [1], "exit 1 is VERDICT-with-findings, measured by hand 2026-08-28"
    assert job["env"]["HC_FINDINGS_EXIT"] == "1"


def test_every_hc_wrapped_row_that_accepts_a_findings_exit_tells_hc_wrap_the_same_codes():
    # the sweep over every instance: ok_exit without HC_FINDINGS_EXIT fails the liveness check
    # instead of the findings check, and the two must name the same codes or one of them is wrong
    wrong = []
    for name, job in JOBS.items():
        if not isinstance(job, dict) or not _hc_wrapped(job):
            continue
        ok = job.get("ok_exit")
        if not ok:
            continue
        declared = (job.get("env") or {}).get("HC_FINDINGS_EXIT")
        if declared is None:
            wrong.append(f"{name}: ok_exit={ok} but no HC_FINDINGS_EXIT (its liveness check fails on every finding)")
        elif sorted(str(c) for c in ok) != sorted(str(declared).replace(",", " ").split()):
            wrong.append(f"{name}: ok_exit={ok} != HC_FINDINGS_EXIT={declared!r}")
    assert not wrong, "\n".join(wrong)


def test_no_row_declares_a_findings_exit_of_zero():
    # exit 0 is "ran fine, found nothing": accepting it as a finding would make every run a finding
    for name, job in JOBS.items():
        if isinstance(job, dict) and job.get("ok_exit"):
            assert 0 not in [int(c) for c in job["ok_exit"]], name
