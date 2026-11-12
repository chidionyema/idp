"""Zero-extra-spend: unallocated GitHub runners never burn retries or fake tests."""

from __future__ import annotations

from greenlane import github as G
from greenlane.engine import PENDING, RED, Batch, Engine, Lane, State


class NeverLog(G.GitHubBackend):
    def __init__(self):
        super().__init__("chidionyema/idp", ["ci-success"])
        self.calls = []

    def gh(self, path, method="GET", fields=None):
        self.calls.append(path)
        return {
            "jobs": [
                {
                    "id": 131158208183,
                    "name": "verify",
                    "conclusion": "failure",
                    "runner_id": 0,
                    "steps": [],
                    "html_url": (
                        "https://github.com/chidionyema/idp/actions/runs/"
                        "43210978878/job/131158208183"
                    ),
                }
            ]
        }


def test_github_missing_runner_names_causal_admission_and_avoids_log_io(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("No log exists for a job that never started")

    monkeypatch.setattr(G, "_run", forbidden)
    backend = NeverLog()
    url = "https://github.com/chidionyema/idp/actions/runs/43210978878/job/131158208183"
    first = backend._cause(url, "ci-success")
    second = backend._cause(url, "ci-success")
    assert first == second
    assert "runner-not-allocated: zero test steps executed" in first
    assert len(backend.calls) == 1, "one bounded read, no useless retry"


class World:
    def __init__(self, reason):
        self.reason = reason
        self.reported = []

    def now(self):
        return 15.0

    def main(self):
        return "trusted-main"

    def checks(self, _tip):
        return "red", self.reason

    def main_red(self, _sha):
        return False

    def report(self, *args):
        self.reported.append(args)


def world(reason):
    backend = World(reason)
    state = State()
    state.lanes["lane/one"] = Lane(name="lane/one", head="source-one")
    state.batch = Batch(
        id="batch-one",
        base="trusted-main",
        tip="candidate-one",
        members=[("lane/one", "source-one", "rebased-one")],
        started=0.0,
    )
    return backend, state


def test_no_runner_safely_parks_exact_sha_without_two_futile_replays():
    backend, state = world(
        "ci-success failure -- verify: runner-not-allocated: zero test steps executed"
    )
    Engine(backend, state)._judge_batch()
    lane = state.lanes["lane/one"]
    assert lane.status == RED
    assert lane.attempts == 1
    assert lane.judged_on == "trusted-main"
    assert "infra admission hold" in lane.reason
    assert state.queued == [] and state.batch is None
    assert state.history[-1]["action"] == "runner-admission-hold"
    assert backend.reported and "runner" in backend.reported[-1][-1]


def test_real_source_failure_preserves_existing_flake_handling():
    backend, state = world("ci-success failure -- AssertionError: real test failed")
    Engine(backend, state)._judge_batch()
    assert state.lanes["lane/one"].status == PENDING
    assert state.lanes["lane/one"].attempts == 1
    assert state.history[-1]["action"] == "retried"
