"""DoF suspension must release old red work once, without resetting unrelated failures."""

from __future__ import annotations

import json

from greenlane import github as G
from greenlane.engine import Engine, Lane, PENDING, RED, State


class StubBackend:
    def __init__(self, epoch: str = "") -> None:
        self.epoch = epoch
        self.reports: list[tuple[str, str, str, str]] = []

    def dof_suspension_epoch(self) -> str:
        return self.epoch

    def report(self, name: str, head: str, status: str, reason: str) -> None:
        self.reports.append((name, head, status, reason))


def frozen_state() -> State:
    return State(
        lanes={
            "blocked": Lane(
                name="blocked",
                head="a" * 40,
                status=RED,
                attempts=3,
                reason="ci-success failure https://example.test/job/1 -- dof-gate > Run base=main",
            ),
            "preflight": Lane(
                name="preflight",
                head="b" * 40,
                status=RED,
                attempts=3,
                reason="trusted DoF [f00dbabe]: critical incident prevents release",
            ),
            "unrelated": Lane(
                name="unrelated",
                head="c" * 40,
                status=RED,
                attempts=3,
                reason="ci-success failure https://example.test/job/2 -- offline-gate > language",
            ),
        },
        seq=3,
    )


def test_recovery_is_once_per_trusted_control_epoch() -> None:
    b = StubBackend("rev1:founder")
    s = frozen_state()
    Engine(b, s)._recover_suspended_dof_lanes()
    assert s.dof_suspension_recovered == "rev1:founder"
    assert s.lanes["blocked"].status == PENDING
    assert s.lanes["preflight"].status == PENDING
    assert s.lanes["blocked"].attempts == 0
    assert s.lanes["preflight"].attempts == 0
    assert s.lanes["unrelated"].status == RED
    assert s.lanes["unrelated"].attempts == 3
    assert len(b.reports) == 2
    assert s.lanes["blocked"].seq > 3

    restored = State.loads(s.dumps())
    Engine(b, restored)._recover_suspended_dof_lanes()
    assert len(b.reports) == 2  # no duplicate dispatch after restart
    restored.lanes["blocked"].status = RED
    restored.lanes["blocked"].attempts = 3
    restored.lanes["blocked"].reason = "ci-success failure u -- dof-gate > unexpected"
    Engine(b, restored)._recover_suspended_dof_lanes()
    assert restored.lanes["blocked"].status == RED
    assert restored.lanes["blocked"].attempts == 3


def test_missing_authority_never_revives_red_work() -> None:
    b = StubBackend("")
    s = frozen_state()
    Engine(b, s)._recover_suspended_dof_lanes()
    assert all(l.status == RED for l in s.lanes.values())
    assert not b.reports
    assert not s.dof_suspension_recovered


def test_backend_reads_only_explicit_disabled_control(tmp_path, monkeypatch) -> None:
    path = tmp_path / "dof-registry.json"
    monkeypatch.setattr(G, "DOF_REGISTRY", path)
    b = G.GitHubBackend("chidionyema/idp", ["ci-success"])
    assert b.dof_suspension_epoch() == ""
    path.write_text("{bad-json")
    assert b.dof_suspension_epoch() == ""
    path.write_text(
        json.dumps(
            {
                "revision": "rev1",
                "control": {"mode": "enforced", "directive": "founder"},
            }
        )
    )
    assert b.dof_suspension_epoch() == ""
    path.write_text(
        json.dumps(
            {
                "revision": "rev1",
                "control": {"mode": "disabled", "directive": "founder"},
            }
        )
    )
    assert b.dof_suspension_epoch() == "rev1:founder"
