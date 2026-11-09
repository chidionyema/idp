"""No false common-mode alerts and no duplicate incident writes."""
from greenlane.common_failure_reaction import classify, react

POLICY = "a" * 40
BASE = "b" * 12


def row(i, name="lane/a", base=BASE, gate="dof-gate", outcome="red"):
    return {
        "id": f"b{i}", "members": [name], "base": base,
        "outcome": outcome,
        "reason": f"ci-success failure https://github.com/x/y/actions/runs/{i} -- {gate} > refused",
    }


def test_common_failure_requires_two_distinct_lanes():
    assert classify({"history": [row(1), row(2, name="lane/b")]}, POLICY).status == "COMMON_MODE"
    assert classify({"history": [row(1), row(2)]}, POLICY).status == "INSUFFICIENT"
    assert classify({"history": [row(1), row(2, name="lane/b", gate="bdd")]}, POLICY).status == "INSUFFICIENT"


def test_policy_and_main_changes_invalidate_epoch():
    prior = classify({"history": [row(1), row(2, name="lane/b")]}, POLICY)
    after = classify({"history": [row(1), row(2, name="lane/b")]}, "c"*40)
    assert prior.fingerprint != after.fingerprint
    assert classify({"history": [row(1), row(2, name="lane/b", base="c"*12)]}, POLICY).status == "INSUFFICIENT"
    assert classify({"history": [row(1), row(2, name="lane/b"),
                                  row(3, gate="", outcome="landed")]}, POLICY).status == "INSUFFICIENT"


def test_unknown_evidence_is_blind_not_healthy():
    assert classify({}, POLICY).status == "BLIND"
    assert classify({"history": [row(1)]}, "garbage").status == "BLIND"


def test_fingerprint_dedupes_new_retries_in_same_epoch():
    a = classify({"history": [row(1), row(2, name="lane/b")]}, POLICY)
    b = classify({"history": [row(1), row(2, name="lane/b"),
                             row(3, name="lane/c")]}, POLICY)
    assert a.fingerprint == b.fingerprint


def test_existing_comment_prevents_new_action():
    finding = classify({"history": [row(1), row(2, name="lane/b")]}, POLICY)
    calls = []
    def fake(repo, *args):
        calls.append(args)
        if args[0].endswith("issues/7800"): return {"state": "open"}
        if "comments" in args[0]:
            return [{"body": f"greenlane-common-mode-fingerprint: {finding.fingerprint}"}]
        raise AssertionError("unexpected API write")
    assert react(finding, "chidionyema/idp", call=fake).startswith("deduplicated")
    assert len(calls) == 2


def test_real_incident_post_is_exactly_once():
    finding = classify({"history": [row(1), row(2, name="lane/b")]}, POLICY)
    calls = []
    def fake(repo, *args):
        calls.append(args)
        if args[0].endswith("issues/7800"): return {"state": "open"}
        if "comments?" in args[0]: return []
        if args[0] == "-X" and args[1] == "POST": return {"id": 123}
        raise AssertionError(args)
    assert react(finding, "chidionyema/idp", call=fake).startswith("reaction recorded")
    assert len(calls) == 3 and finding.fingerprint in calls[-1][-1]


def test_no_write_when_canonical_owner_is_closed():
    finding = classify({"history": [row(1), row(2, name="lane/b")]}, POLICY)
    def fake(*args): return {"state": "closed"}
    try:
        react(finding, "chidionyema/idp", call=fake)
    except RuntimeError as error:
        assert "missing or closed" in str(error)
    else:
        raise AssertionError("must not write to a closed canonical issue")
