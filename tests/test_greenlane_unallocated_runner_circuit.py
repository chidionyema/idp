"""Zero-extra-spend: unallocated GitHub runners cannot burn retries or masquerade as code failures."""
from __future__ import annotations

from greenlane import github as G
from greenlane.engine import Batch, Engine, Lane, RED, PENDING, State


class NeverLog(G.GitHubBackend):
    def __init__(self):
        super().__init__("chidionyema/idp", ["ci-success"])
        self.calls = []

    def gh(self, path, method="GET", fields=None):
        self.calls.append(path)
        return {"jobs": [{
            "id": 131158208183, "name": "verify", "conclusion": "failure",
            "runner_id": 0, "steps": [],
            "html_url": "https://github.com/chidionyema/idp/actions/runs/43210978878/job/131158208183",
        }]}


def test_github_missing_runner_names_causal_admission_and_avoids_log_io(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("No log exists for a job that never started")

    monkeypatch.setattr(G, "_run", forbidden)
    backend = NeverLog()
    url = "https://github.com/chidionyema/idp/actions/runs/43210978878/job/131158208183"
    a = backend._cause(url, "ci-success")
    b = backend._cause(url, "ci-success")
    assert a == b
    assert "runner-not-allocated: zero test steps executed" in a
    assert len(backend.calls) == 1, "one bounded read, no useless retry"


class World:
    def __init__(self, reason):
        self.reason = reason
        self.reported = []
    def now(self): return 15.0
    def main(self): return "trusted-main"
    def checks(self, _tip): return "red", self.reason
    def main_red(self, _sha): return False
    def report(self, *args): self.reported.append(args)


def world(reason):
    b = World(reason)
    s = State()
    s.lanes["lane/one"] = Lane(name="lane/one", head="source-one")
    s.batch = Batch(
        id="batch-one", base="trusted-main", tip="candidate-one",
        members=[("lane/one", "source-one", "rebased-one")],
        started=0.0,
    )
    return b, s


def test_no_runner_safely_parks_exact_sha_without_two_futile_replays():
    b, s = world("ci-success failure -- verify: runner-not-allocated: zero test steps executed")
    Engine(b, s)._judge_batch()
    lane = s.lanes["lane/one"]
    assert lane.status == RED
    assert lane.attempts == 1
    assert lane.judged_on == "trusted-main"
    assert "infra admission hold" in lane.reason
    assert s.queued == [] and s.batch is None
    assert s.history[-1]["action"] == "runner-admission-hold"
    assert b.reported and "runner" in b.reported[-1][-1]


def test_failing_source_without_admission_block_preserves_existing_flake_handling():
    b, s = world("ci-success failure -- AssertionError: real test failed")
    Engine(b, s)._judge_batch()
    assert s.lanes["lane/one"].status == PENDING
    assert s.lanes["lane/one"].attempts == 1
    assert s.history[-1]["action"] == "retried"
