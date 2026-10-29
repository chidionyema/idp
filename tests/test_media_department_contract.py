"""features/media-department/m1_contract.feature, bound to the real department contract (idp#7395).

Every step runs `platform/department/contract.py admit()` over records validated against
`schema/department/v1/`. Nothing is mocked: the ledger is the contract's own in-memory ledger (the
M1 interface; M2 backs it with JetStream), and time and source revisions are the explicit Context
the contract takes, so each verdict is reproducible.

The contract lives under `platform/` (not an installed package), so it is imported by path.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

_REPO_ROOT = Path(__file__).resolve().parents[1]
_LIB = _REPO_ROOT / "platform" / "department" / "contract.py"
_MEDIA = _REPO_ROOT / "platform" / "department" / "media.yaml"


def _load_contract():
    spec = importlib.util.spec_from_file_location("estate_department_contract", _LIB)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_department_contract"] = module
    spec.loader.exec_module(module)
    return module


contract = _load_contract()

scenarios("../features/media-department/m1_contract.feature")

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
SHA = "a" * 64
OBJECTIVE = "obj-live-film"
SOURCE = "idp#7395"


def _granted_config() -> dict:
    """The committed media config, with one worker per role. The prototype studio also holds the
    evaluator role, so self-certification is refused by the contract and not by a missing grant."""
    config = contract.load_config(_MEDIA)
    config["workers"] = {f"agent-{role}": [role] for role in config["roles"]}
    config["workers"]["agent-prototype-studio"] = ["prototype-studio", "evaluator"]
    return config


def _record(
    kind: str, state: str, run_id: str, role: str, payload: dict, **over
) -> dict:
    record = {
        "schema_version": "department.v1",
        "department_id": "media",
        "objective_id": OBJECTIVE,
        "run_id": run_id,
        "parent_run_id": None,
        "kind": kind,
        "state": state,
        "source_ref": SOURCE,
        "source_revision": "r1",
        "evidence_refs": [
            {"kind": "test", "uri": "pytest://tests/test_media_department_contract.py"}
        ],
        "artifact_uri": None,
        "artifact_sha256": None,
        "created_at": "2026-10-29T10:00:00Z",
        "expires_at": "2026-10-30T00:00:00Z",
        "authority": role,
        "policy_decision": None,
        "budget_cap_usd": 5.0,
        "spend_usd": 0.0,
        "evaluator_id": None,
        "verdict": None,
        "reason": f"{kind} -> {state}",
        "payload": payload,
    }
    record.update(over)
    return record


def _opportunity() -> dict:
    return {
        "hypothesis": "an avatar driven by estate.agent events is legible to the founder",
        "rank": 1,
        "non_duplication": {
            "query": "avatar scene renderer",
            "registry_refs": ["cap:service/voice-router/voice-router-director"],
        },
    }


def _artifact(author: str) -> dict:
    return {
        "media_type": "text/html",
        "lane": "truth",
        "generative": False,
        "licence": "MIT",
        "author_id": author,
    }


def _review(author: str = "agent-prototype-studio") -> dict:
    return {
        "prototype_run_id": "run-film-1",
        "prototype_author_id": author,
        "scorecard": {"fidelity": 1.0},
    }


BUILT = {"artifact_uri": "file://prototype/index.html", "artifact_sha256": SHA}

# The legal walk of one run, in order: (state, writer, kind, payload, overrides).
WALK = [
    ("TRIAGED", "agent-portfolio-governor", "opportunity", _opportunity, {}),
    (
        "RESEARCHING",
        "agent-research-scout",
        "experiment",
        lambda: {
            "plan": "render one avatar",
            "sandbox": "preview",
            "acceptance_fixtures": ["replay-equivalence"],
        },
        {},
    ),
    (
        "PROTOTYPING",
        "agent-prototype-studio",
        "artifact",
        lambda: _artifact("agent-prototype-studio"),
        BUILT,
    ),
    (
        "EVALUATING",
        "agent-evaluator",
        "review",
        _review,
        {**BUILT, "evaluator_id": "agent-evaluator"},
    ),
    (
        "PROPOSED",
        "agent-evaluator",
        "review",
        _review,
        {**BUILT, "evaluator_id": "agent-evaluator", "verdict": "pass"},
    ),
    (
        "APPROVED",
        "agent-authorization-door",
        "decision",
        lambda: {
            "door": "founder.decision",
            "decision_id": "dec-1a2b3c4d",
            "question": "ship the film prototype?",
            "answer": "allow",
        },
        {
            "policy_decision": {
                "door": "founder.decision",
                "decision_id": "dec-1a2b3c4d",
                "verdict": "allow",
            }
        },
    ),
    (
        "SHIPPING",
        "agent-delivery",
        "artifact",
        lambda: _artifact("agent-delivery"),
        BUILT,
    ),
    (
        "VERIFYING",
        "agent-delivery",
        "artifact",
        lambda: _artifact("agent-delivery"),
        BUILT,
    ),
]
ROLE_OF = {f"agent-{role}": role for role in contract.load_config(_MEDIA)["roles"]}


class World:
    def __init__(self) -> None:
        self.config = _granted_config()
        self.ledger = contract.Ledger()
        self.revisions = {SOURCE: "r1"}
        self.verdicts: list = []

    def submit(self, record: dict, writer: str):
        verdict = contract.admit(
            record,
            writer,
            self.ledger,
            self.config,
            contract.Context(NOW, dict(self.revisions)),
        )
        self.verdicts.append(verdict)
        return verdict

    def walk_to(self, run_id: str, target: str) -> None:
        for state, writer, kind, payload, over in WALK:
            verdict = self.submit(
                _record(kind, state, run_id, ROLE_OF[writer], payload(), **over), writer
            )
            assert verdict.admitted, (state, verdict)
            if state == target:
                return
        raise AssertionError(f"{target} is not on the walk")


@pytest.fixture
def world() -> World:
    return World()


# --- background ------------------------------------------------------------------------------------


@given("the media department contract with a granted worker for every role")
def _contract(world: World) -> None:
    assert world.config["department_id"] == "media"


@given(parsers.parse('objective "{objective}" is admitted with a cap of {cap:d} USD'))
def _objective(world: World, objective: str, cap: int) -> None:
    payload = {
        "title": "live estate film",
        "statement": "the founder sees agents' real work",
        "origin": "founder",
        "per_day_cap_usd": 10,
    }
    record = _record(
        "objective",
        "NEW",
        "run-objective",
        "portfolio-governor",
        payload,
        objective_id=objective,
        budget_cap_usd=float(cap),
    )
    assert world.submit(record, "agent-portfolio-governor").admitted


@given(parsers.parse('run "{run_id}" is opened as a new opportunity'))
def _opened(world: World, run_id: str) -> None:
    verdict = world.submit(
        _record("opportunity", "NEW", run_id, "portfolio-governor", _opportunity()),
        "agent-portfolio-governor",
    )
    assert verdict.admitted, verdict


@given(parsers.parse('run "{run_id}" has reached {state}'))
def _reached(world: World, run_id: str, state: str) -> None:
    world.walk_to(run_id, state)


@given(parsers.parse('source "{source}" is now at revision "{revision}"'))
def _moved(world: World, source: str, revision: str) -> None:
    world.revisions[source] = revision


@given("the media department config as committed")
def _committed(world: World) -> None:
    world.config = contract.load_config(_MEDIA)


# --- actions ---------------------------------------------------------------------------------------


def _triage(run_id: str, **over) -> dict:
    return _record(
        "opportunity", "TRIAGED", run_id, "portfolio-governor", _opportunity(), **over
    )


@when(
    parsers.parse(
        'the governor triages run "{run_id}" from source "{source}" at revision "{revision}"'
    )
)
def _triage_from(world: World, run_id: str, source: str, revision: str) -> None:
    world.submit(
        _triage(run_id, source_ref=source, source_revision=revision),
        "agent-portfolio-governor",
    )


@when(
    parsers.parse(
        'the governor triages run "{run_id}" from source "{source}" at revision "{revision}" again'
    )
)
def _triage_again(world: World, run_id: str, source: str, revision: str) -> None:
    world.submit(
        _triage(run_id, source_ref=source, source_revision=revision),
        "agent-portfolio-governor",
    )


@when(parsers.parse('the governor triages run "{run_id}" with an empty source_ref'))
def _triage_no_source(world: World, run_id: str) -> None:
    world.submit(_triage(run_id, source_ref=""), "agent-portfolio-governor")


@when(parsers.parse('the governor triages run "{run_id}" spending {spend:d} USD'))
def _triage_spend(world: World, run_id: str, spend: int) -> None:
    world.submit(_triage(run_id, spend_usd=float(spend)), "agent-portfolio-governor")


@when(parsers.parse('the delivery worker moves run "{run_id}" to SHIPPING'))
def _ship(world: World, run_id: str) -> None:
    world.submit(
        _record(
            "artifact",
            "SHIPPING",
            run_id,
            "delivery",
            _artifact("agent-delivery"),
            **BUILT,
        ),
        "agent-delivery",
    )


@when(parsers.parse('the door writes APPROVED for run "{run_id}" citing door "{door}"'))
def _approve(world: World, run_id: str, door: str) -> None:
    payload = {
        "door": door,
        "decision_id": "dec-self",
        "question": "approve?",
        "answer": "allow",
    }
    record = _record(
        "decision",
        "APPROVED",
        run_id,
        "authorization-door",
        payload,
        policy_decision={"door": door, "decision_id": "dec-self", "verdict": "allow"},
    )
    world.submit(record, "agent-authorization-door")


@when(parsers.parse('an ungranted agent triages run "{run_id}"'))
def _stranger(world: World, run_id: str) -> None:
    world.submit(_triage(run_id), "agent-stranger")


@when(parsers.parse('any agent triages run "{run_id}"'))
def _anyone(world: World, run_id: str) -> None:
    world.submit(_triage(run_id), "agent-portfolio-governor")


@when(
    parsers.parse(
        'the prototype\'s author reviews its own prototype for run "{run_id}"'
    )
)
def _self_review(world: World, run_id: str) -> None:
    record = _record(
        "review",
        "EVALUATING",
        run_id,
        "evaluator",
        _review(),
        **BUILT,
        evaluator_id="agent-prototype-studio",
    )
    world.submit(record, "agent-prototype-studio")


@when(
    parsers.parse(
        'the verifier marks run "{run_id}" OPERATING on generated evidence only'
    )
)
def _operate(world: World, run_id: str) -> None:
    record = _record(
        "review",
        "OPERATING",
        run_id,
        "verifier",
        _review(),
        evaluator_id="agent-verifier",
        verdict="pass",
        evidence_refs=[
            {
                "kind": "generated",
                "uri": "llm://summary-says-it-works",
                "observed_by": "agent-evaluator",
            }
        ],
    )
    world.submit(record, "agent-verifier")


# --- outcomes --------------------------------------------------------------------------------------


@then("the write is admitted")
def _admitted(world: World) -> None:
    assert world.verdicts[-1].admitted, world.verdicts[-1]


@then(parsers.parse('the write is refused as "{code}"'))
def _refused(world: World, code: str) -> None:
    verdict = world.verdicts[-1]
    assert not verdict.admitted and verdict.code == code, verdict


@then(parsers.parse('the second write is refused as "{code}"'))
def _second_refused(world: World, code: str) -> None:
    first, second = world.verdicts[-2], world.verdicts[-1]
    assert first.admitted, first
    assert not second.admitted and second.code == code, second


# --- the contract's own invariants, beyond the feature ---------------------------------------------


def test_the_full_walk_reaches_operating_on_an_independent_observation() -> None:
    w = World()
    _objective(w, OBJECTIVE, 5)
    _opened(w, "run-film-1")
    w.walk_to("run-film-1", "VERIFYING")
    record = _record(
        "review",
        "OPERATING",
        "run-film-1",
        "verifier",
        _review(),
        evaluator_id="agent-verifier",
        verdict="pass",
        evidence_refs=[
            {
                "kind": "observation",
                "uri": "log://voice-router/2026-10-29T11:59:00Z",
                "observed_by": "agent-evaluator",
            }
        ],
    )
    verdict = w.submit(record, "agent-verifier")
    assert verdict.admitted, verdict


def test_every_state_has_a_transition_row_and_rejected_is_terminal() -> None:
    assert set(contract.TRANSITIONS) - {None} == set(contract.STATES)
    for targets in contract.TRANSITIONS.values():
        assert targets <= set(contract.STATES)
    assert contract.TRANSITIONS["REJECTED"] == frozenset()
    assert "SHIPPING" not in contract.TRANSITIONS["RESEARCHING"]
    assert set(contract.WORK_ITEM_STATE) == set(contract.STATES)


def test_blocked_resumes_only_to_where_it_was_blocked_from() -> None:
    w = World()
    _objective(w, OBJECTIVE, 5)
    _opened(w, "run-film-1")
    w.walk_to("run-film-1", "RESEARCHING")
    blocked = _record(
        "experiment",
        "BLOCKED",
        "run-film-1",
        "research-scout",
        {"plan": "wait on cluster", "sandbox": "preview", "acceptance_fixtures": ["x"]},
    )
    assert w.submit(blocked, "agent-research-scout").admitted
    skip = _record(
        "artifact",
        "PROTOTYPING",
        "run-film-1",
        "prototype-studio",
        _artifact("agent-prototype-studio"),
        **BUILT,
    )
    assert w.submit(skip, "agent-prototype-studio").code == "illegal_transition"
    back = _record(
        "experiment",
        "RESEARCHING",
        "run-film-1",
        "research-scout",
        {"plan": "resume", "sandbox": "preview", "acceptance_fixtures": ["x"]},
        source_revision="r1",
        reason="resumed",
    )
    # same (run, kind, state, revision) as the first RESEARCHING write: a resume is a new input revision
    assert w.submit(back, "agent-research-scout").code == "duplicate_idempotency_key"
    w.revisions[SOURCE] = "r2"
    assert w.submit({**back, "source_revision": "r2"}, "agent-research-scout").admitted


def test_a_generative_artifact_is_refused_in_the_truth_lane() -> None:
    """ADR 0037: generative media lives only in the labelled creative lane."""
    record = _record(
        "artifact",
        "PROTOTYPING",
        "run-film-1",
        "prototype-studio",
        {**_artifact("agent-prototype-studio"), "generative": True},
        **BUILT,
    )
    errors = list(contract.VALIDATORS["artifact"].iter_errors(record))
    assert errors, "a generative artifact in the truth lane validated"
    record["payload"]["lane"] = "creative"
    assert not list(contract.VALIDATORS["artifact"].iter_errors(record))


def test_a_budget_spread_over_writes_cannot_exceed_the_objective_cap() -> None:
    w = World()
    _objective(w, OBJECTIVE, 5)
    assert w.submit(
        _record(
            "opportunity",
            "NEW",
            "run-alpha",
            "portfolio-governor",
            _opportunity(),
            spend_usd=3.0,
        ),
        "agent-portfolio-governor",
    ).admitted
    verdict = w.submit(
        _record(
            "opportunity",
            "NEW",
            "run-beta",
            "portfolio-governor",
            _opportunity(),
            spend_usd=3.0,
        ),
        "agent-portfolio-governor",
    )
    assert verdict.code == "budget_overflow", verdict


def test_an_expired_record_is_stale() -> None:
    w = World()
    _objective(w, OBJECTIVE, 5)
    verdict = w.submit(
        _record(
            "opportunity",
            "NEW",
            "run-alpha",
            "portfolio-governor",
            _opportunity(),
            expires_at="2026-10-29T11:00:00Z",
        ),
        "agent-portfolio-governor",
    )
    assert verdict.code == "stale_provenance", verdict


def test_admission_is_deterministic() -> None:
    def run() -> list:
        w = World()
        _objective(w, OBJECTIVE, 5)
        _opened(w, "run-film-1")
        w.walk_to("run-film-1", "VERIFYING")
        w.submit(copy.deepcopy(_triage("run-film-1")), "agent-portfolio-governor")
        return [(v.admitted, v.code, v.reason) for v in w.verdicts]

    assert run() == run()
