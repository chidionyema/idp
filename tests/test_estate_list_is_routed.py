"""estate_list must serve the few intents a task needs, and still be able to show all of them.

Measured 2026-11-11 (docs/diagnoses/2026-11-11-reactive-wakeup-signaling-gap.md, section 12 item
3): a full estate_list rendered every intent with its description and args. On this machine that
was 377-381 intents and 34,146 chars -- about 8,536 tokens -- on a call whose commonest answer is
"there is no door for this". Every agent paid it at least once per session, and the diagnosis
graded it the estate's largest single schema cost.

These tests hold the routed view to a budget and prove the full list is still reachable, because
a router that hides a capability is worse than the token bill it saves.
"""

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "mcp" / "plugins" / "estate_mcp.py"

# ~500 tokens at four chars per token is the section 12 target. The routed view measured 394
# tokens (1,577 chars) when this was written, so the budget has room but can still fail: a
# regression that put the full list back, or doubled the per-intent rendering, breaks it.
ROUTED_BUDGET_TOKENS = 500


def _load():
    spec = importlib.util.spec_from_file_location("estate_mcp_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def em():
    return _load()


def _tokens(text):
    return len(text) // 4


def test_routed_view_fits_the_token_budget(em):
    """The whole point: a default call must stay under the budget."""
    out = em._estate_list({})
    assert _tokens(out) < ROUTED_BUDGET_TOKENS, (
        "routed estate_list is {} tokens ({} chars), over the {} budget".format(
            _tokens(out), len(out), ROUTED_BUDGET_TOKENS
        )
    )


def test_routed_view_is_smaller_than_the_full_list(em):
    """Relative proof, so the budget above cannot be met by a machine with few intents."""
    routed = em._estate_list({})
    full = em._estate_list({"full": True})
    assert len(full) > len(routed) * 5, (
        "full list is {} chars and routed is {} -- a router that saves almost nothing is "
        "not worth the indirection".format(len(full), len(routed))
    )


def test_full_list_is_reachable_and_complete(em):
    """Additive, never subtractive: every intent stays obtainable."""
    full = em._estate_list({"full": True})
    names_in_full = [line[3:] for line in full.splitlines() if line.startswith("## ")]
    loaded = [i["name"] for i in em._load_intents()]
    assert names_in_full == loaded, "full=true must render every intent that loads"
    assert len(names_in_full) > 50, (
        "only {} intents rendered; if the estate really has this few, revisit the budget "
        "rather than deleting this assertion".format(len(names_in_full))
    )


def test_routed_view_says_how_to_see_the_rest(em):
    """A shorter answer that does not name the way to the longer one is a dead end."""
    out = em._estate_list({})
    assert "full=true" in out, "the routed view must name full=true"
    assert 'query="' in out, "the routed view must name query= as the real router"


def test_routed_view_reports_how_many_it_hid(em):
    """Silently truncating is the fail-open shape: the reader must see the denominator."""
    out = em._estate_list({})
    total = len(em._load_intents())
    first = out.splitlines()[0]
    assert "of {} intents".format(total) in first, (
        "first line must say how many of how many, got: {!r}".format(first)
    )


def test_limit_bounds_the_view_and_cannot_exceed_the_list(em):
    small = em._estate_list({"limit": 3})
    n_small = len([line for line in small.splitlines() if line.startswith("## ")])
    assert n_small == 3, "limit=3 must return 3 intents, got {}".format(n_small)
    # A limit larger than the estate must not invent or repeat entries.
    huge = em._estate_list({"limit": 10**6})
    names_huge = [line[3:] for line in huge.splitlines() if line.startswith("## ")]
    assert len(names_huge) == len(set(names_huge)), "limit must not duplicate intents"


def test_a_bad_limit_does_not_crash_the_door(em):
    """The door must answer, not raise: a tool call that explodes teaches nothing."""
    out = em._estate_list({"limit": "not-a-number"})
    assert "intents" in out, (
        "a malformed limit must fall back to the default, got: %r" % out[:80]
    )


def test_query_still_routes_on_relevance_not_the_starting_set(em):
    """`query=` is the real router and must remain distinct from the default view."""
    out = em._estate_list({"query": "is my lane landed"})
    assert "lane" in out.lower(), "a lane query must surface a lane intent"


def test_the_starting_set_names_real_intents(em):
    """FIRST_CONTACT is a promise about doors that exist; a stale name is a lie to the agent."""
    intents = {i["name"] for i in em._load_intents()}
    missing = [n for n in em.FIRST_CONTACT if n not in intents]
    # Not asserted empty: an estate may legitimately retire a door. It is asserted small.
    assert len(missing) <= 2, (
        "{} of {} starting intents do not exist ({}); the starting set has drifted".format(
            len(missing), len(em.FIRST_CONTACT), ", ".join(missing)
        )
    )
