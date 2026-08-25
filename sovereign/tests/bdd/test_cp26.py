"""cp26 acceptance: Predictive pre-authorization -- approve futures, not events

Owner: W5 (sovereign/shadow/preauth.py). Steps drive the real planner and
the real signed receipt chain against the scenario's temporary estate. The
trust backend is pinned to software_key so no Keychain prompt can reach a
test run; the receipt chain itself is real.

"bin/sb approve <session_id> --by founder" is applied as the founder's
gesture on the planner's waiting session. The estate's `sb approve` also
verifies a signature and signals a Temporal workflow; the signature is
the trust lane's (cp29) and the workflow is the engine's, and neither is
what this feature is about -- what it asserts is that one approval covers
the whole predicted trajectory.
"""
from __future__ import annotations

import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sovereign.engine import receipts as receipts_mod
from sovereign.shadow import config_keys as ck
from sovereign.shadow import preauth

scenarios("features/sovereign-bus/cp26_predictive_preauth.feature")

_K_RE = re.compile(r"(\d+)k", re.IGNORECASE)


def _tokens(text: str) -> int:
    m = _K_RE.search(text)
    assert m, f"no <n>k token figure in {text!r}"
    return int(m.group(1)) * 1000


@pytest.fixture(autouse=True)
def _software_trust(estate_home: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")


def _seed_founder_decisions(kind: str, boundary: str, count: int) -> None:
    for i in range(count):
        receipts_mod.append(
            {"session_id": f"seed-{i}", "kind": kind, "by": str(ck.get("shadow.founder")), "text": boundary,
             "boundary": boundary, "step": i, "status": "running"}
        )


def _shadow_auth_rows() -> list[dict[str, Any]]:
    return [r for r in receipts_mod.read_all() if r.get("kind") == str(ck.get("shadow.auth_receipt_kind"))]


# ---- scenario 1 --------------------------------------------------------------


@given(parsers.parse("a session with budget {budget} tokens and {n:d} predicted steps costing {cost}"), target_fixture="session")
def _session(budget: str, n: int, cost: str, context: dict[str, Any]) -> preauth.Session:
    total = _tokens(cost)
    per_step = total // n
    session = preauth.Session("sb-cp26", _tokens(budget), [per_step] * n)
    context["budget"] = _tokens(budget)
    context["n"] = n
    session.plan()
    return session


@then(parsers.parse('the session status is "{status}" before the boundary is reached'))
def _status_before_boundary(session: preauth.Session, status: str, context: dict[str, Any]) -> None:
    assert session.status == status
    assert session.steps_run == 0, "the ask came before any predicted step ran"
    assert session.remaining == context["budget"], "nothing was spent before the ask"


@then("the ask names the refill amount and the steps it covers")
def _ask_names_refill(session: preauth.Session, context: dict[str, Any]) -> None:
    assert session.asking, "no ask text"
    assert session.pending is not None
    assert str(session.pending.refill) in session.asking
    assert f"{context['n']} step" in session.asking
    assert session.pending.refill + context["budget"] >= sum(session.predicted_costs)


@when(parsers.parse('I run "bin/sb approve <session_id> --by {by}"'))
def _approve(session: preauth.Session, by: str, context: dict[str, Any]) -> None:
    context["approve_receipt"] = session.approve(by)


@then("all three steps run without another ask")
def _all_steps_run(session: preauth.Session) -> None:
    asks_before = session.asks
    ran = session.run_predicted_steps()
    assert ran == 3, f"ran {ran} of 3 predicted steps"
    assert session.asks == asks_before, "a second ask was raised"
    assert session.status == "running"


# ---- scenario 2 --------------------------------------------------------------


@given(parsers.parse('the receipts hold at least {count:d} founder approvals of "{boundary}" with no denials'))
def _seed_approvals(count: int, boundary: str) -> None:
    _seed_founder_decisions(str(ck.get("shadow.approve_kind")), boundary, count)
    hist = preauth.history(boundary)
    assert hist.approvals >= count and hist.denials == 0


@when("the same boundary is predicted", target_fixture="session")
def _same_boundary(context: dict[str, Any], messages: Any) -> preauth.Session:
    session = preauth.Session("sb-cp26-shadow", 10_000, [4_000, 4_000, 4_000])
    context["asks_before"] = session.asks
    session.plan()
    return session


@then(parsers.re(r'the kernel writes a receipt kind "(?P<kind>[^"]+)" with a confidence (?:≥|>=) (?P<threshold>[0-9.]+)'))
def _shadow_auth_receipt(kind: str, threshold: str, session: preauth.Session) -> None:
    rows = [r for r in receipts_mod.read_all() if r.get("kind") == kind and r.get("session_id") == session.session_id]
    assert len(rows) == 1, f"expected one {kind} receipt, got {len(rows)}"
    assert float(rows[0]["confidence"]) >= float(threshold)
    assert rows[0]["founder_notified"] is False
    assert isinstance(session.verdict, preauth.ShadowAuth)


@then("the founder is not asked")
def _not_asked(session: preauth.Session, messages: Any, context: dict[str, Any]) -> None:
    assert session.status == "running"
    assert session.asking is None
    assert session.asks == context["asks_before"]
    messages.assert_silent()


# ---- scenario 3 --------------------------------------------------------------


@given(parsers.parse('the receipts hold {count:d} founder approvals of "{op}"'))
def _seed_op_approvals(count: int, op: str) -> None:
    _seed_founder_decisions(str(ck.get("shadow.approve_kind")), op, count)
    assert preauth.history(op).approvals == count


@when(parsers.parse('a step asks for "{op}"'), target_fixture="session")
def _step_asks(op: str) -> preauth.Session:
    session = preauth.Session("sb-cp26-force", 10_000, [100])
    session.plan(op)
    return session


@then(parsers.parse('the session status is "{status}"'))
def _status_is(session: preauth.Session, status: str) -> None:
    assert session.status == status
    assert isinstance(session.verdict, preauth.Ask)
    assert session.verdict.reason in ("destructive", "unknown")


@then(parsers.parse('no "{kind}" receipt is written'))
def _no_receipt(kind: str) -> None:
    assert [r for r in receipts_mod.read_all() if r.get("kind") == kind] == []
