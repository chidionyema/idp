"""Issue #5618: bounded recovery of two exact fast-gate-stranded lanes.

The historical gate was repaired by b5423 and its post-main cloud job
43143345221/job/130935344047 executed the ten contract falsifiers.
Recovery must still fail closed on unrelated RED, absent exact trusted
workflow blobs, red/pending main, and repeated same-head attempts.
"""

from __future__ import annotations

from greenlane.engine import Engine, Lane, State, PENDING, RED

REPAIRED_MAIN = "f7a19cee746893d1ce992e2ef65bdffb33fcb83b"
CASES = (
    (
        "lane/meridian-contact-mailjet-extract-20261111",
        "22d69b0c6686a557d07759772001e960b4305442",
        "43074841259",
    ),
    (
        "lane/otto-main114-rollout-20261111",
        "c2526b73794fd0795991c1e27b420903a6a8b7bb",
        "43083819999",
    ),
)


class Backend:
    def __init__(self, name, head, main=REPAIRED_MAIN, verdict="green"):
        self.name, self.head, self.main_sha, self.verdict = name, head, main, verdict
        self.reports = []

    def main(self):
        return self.main_sha

    def lanes(self):
        return {self.name: self.head}

    def checks(self, sha):
        assert sha == self.main_sha
        return self.verdict, "forced negative" if self.verdict != "green" else ""

    def report(self, *args):
        self.reports.append(args)

    def now(self):
        return 1.0


def stranded(name, head, run):
    return Lane(
        name=name,
        head=head,
        status=RED,
        attempts=3,
        judged_on="",
        reason=f"land refused: fast-gate / fast-gate failure https://github.com/chidionyema/idp/actions/runs/{run}/job/123 -- bin/idp-ci",
    )


def test_exact_stranded_lanes_rearm_once_after_verified_gate_repair():
    for name, head, run in CASES:
        b = Backend(name, head)
        st = State(lanes={name: stranded(name, head, run)})
        e = Engine(b, st)
        e._observe_lanes()
        assert st.lanes[name].status == PENDING
        assert st.lanes[name].attempts == 0
        assert st.lanes[name].recovered_gate_sha == REPAIRED_MAIN
        st.lanes[name].status = RED
        st.lanes[name].attempts = 3
        st.lanes[name].reason = stranded(name, head, run).reason
        e._observe_lanes()
        assert st.lanes[name].status == RED
        assert st.lanes[name].attempts == 3


def test_unrelated_red_does_not_rearm():
    name, head, run = CASES[0]
    b = Backend(name, head)
    for reason in (
        "ci-success failure ui-kit > violations 358",
        "ci-success failure bdd > 0 tests",
        f"fast-gate / fast-gate failure https://github.com/chidionyema/idp/actions/runs/{run} -- unrelated check",
        "fast-gate / fast-gate failure https://github.com/chidionyema/idp/actions/runs/99999999999/job/123 -- bin/idp-ci",
    ):
        lane = stranded(name, head, run)
        lane.reason = reason
        st = State(lanes={name: lane})
        Engine(b, st)._observe_lanes()
        assert st.lanes[name].status == RED, reason


def test_changed_head_is_not_the_verified_stranded_candidate():
    name, head, run = CASES[0]
    other = "b" * 40
    st = State(lanes={name: stranded(name, other, run)})
    Engine(Backend(name, other), st)._observe_lanes()
    assert st.lanes[name].status == RED


def test_red_or_pending_main_cannot_authorize_recovery():
    name, head, run = CASES[0]
    for verdict in ("red", "pending"):
        st = State(lanes={name: stranded(name, head, run)})
        Engine(Backend(name, head, verdict=verdict), st)._observe_lanes()
        assert st.lanes[name].status == RED


def test_missing_trusted_main_blob_cannot_authorize_recovery():
    name, head, run = CASES[0]
    st = State(lanes={name: stranded(name, head, run)})
    Engine(Backend(name, head, main="a" * 40), st)._observe_lanes()
    assert st.lanes[name].status == RED


def test_recovery_budget_survives_state_round_trip():
    name, head, run = CASES[0]
    st = State(lanes={name: stranded(name, head, run)})
    Engine(Backend(name, head), st)._observe_lanes()
    restored = State.loads(st.dumps())
    assert restored.lanes[name].recovered_gate_sha == REPAIRED_MAIN
    restored.lanes[name].status = RED
    restored.lanes[name].reason = stranded(name, head, run).reason
    Engine(Backend(name, head), restored)._observe_lanes()
    assert restored.lanes[name].status == RED


def test_tampered_workflow_blob_refuses_recovery(monkeypatch):
    import subprocess

    from greenlane import engine

    original = engine.subprocess.run

    def tampered(argv, **kwargs):
        result = original(argv, **kwargs)
        if argv[:2] == ["git", "ls-tree"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                result.stdout.replace(
                    "e2e9ec70e9c4de1cdb4a17751ea815829b831c20",
                    "0" * 40,
                ),
                result.stderr,
            )
        return result

    monkeypatch.setattr(engine.subprocess, "run", tampered)
    name, head, run = CASES[0]
    st = State(lanes={name: stranded(name, head, run)})
    Engine(Backend(name, head), st)._observe_lanes()
    assert st.lanes[name].status == RED


def test_unavailable_cloud_checks_refuse_recovery():
    class Unavailable(Backend):
        def checks(self, sha):
            raise RuntimeError("cloud checks unavailable")

    name, head, run = CASES[0]
    st = State(lanes={name: stranded(name, head, run)})
    Engine(Unavailable(name, head), st)._observe_lanes()
    assert st.lanes[name].status == RED
