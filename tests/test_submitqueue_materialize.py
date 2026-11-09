"""Adversarial assurance for the upstream SubmitQueue GitHub path builder."""

import importlib.util
import json
from pathlib import Path

import pytest

PATH = (
    Path(__file__).resolve().parents[1] / "platform" / "submitqueue" / "materialize.py"
)
spec = importlib.util.spec_from_file_location("ferrari_materialize", PATH)
materialize_module = importlib.util.module_from_spec(spec)
import sys

sys.modules[spec.name] = materialize_module
spec.loader.exec_module(materialize_module)

parse_uri = materialize_module.parse_uri
parse_path = materialize_module.parse_path
materialize = materialize_module.materialize
REPO = "chidionyema/idp"
A = "a" * 40
B = "b" * 40


def u(pr, sha=A, repo=REPO, host="github.com"):
    return f"github://{host}/{repo}/pull/{pr}/{sha}"


def test_canonical_uri_roundtrip():
    item = parse_uri(u(42), REPO)
    assert (item.owner, item.repo, item.number, item.sha) == (
        "chidionyema",
        "idp",
        42,
        A,
    )


@pytest.mark.parametrize(
    "bad",
    [
        u(0),
        u("01"),
        u(3, sha="ABC"),
        u(3, sha="A" * 40),
        u(3, host="evil.com"),
        u(3, repo="chidionyema/other"),
        u(3) + "?sq-fake=build-pass",
        u(3) + "#bad",
        "https://github.com/chidionyema/idp/pull/3/" + A,
        "github://github.com@evil.com/chidionyema/idp/pull/3/" + A,
        "github://github.com/chidionyema/idp/pull/3/" + A + "/extra",
    ],
)
def test_reject_noncanonical_sources(bad):
    with pytest.raises(ValueError):
        parse_uri(bad, REPO)


def test_full_dependency_path_in_order():
    refs = parse_path(json.dumps([u(1)]), json.dumps([u(2, B)]), REPO)
    assert [r.number for r in refs] == [1, 2]
    assert [r.sha for r in refs] == [A, B]


def test_never_certify_duplicate_or_empty_batch():
    for base, head in [
        ([], []),
        ([u(1)], [u(1)]),
        ([u(1), u(1)], [u(2)]),
        ([], ["xyz"]),
        ([], [None]),
        ([], [u(3)] * 33),
    ]:
        with pytest.raises(ValueError):
            parse_path(json.dumps(base), json.dumps(head), REPO)


def test_materialization_checks_exact_pr_refs_and_dependency_order(monkeypatch):
    seen = []

    def fake_git(*args, authenticated=False):
        seen.append((args, authenticated))
        if args[0] == "status":
            return ""
        if args[0] == "rev-parse":
            if args[1] == "HEAD":
                return A if len(seen) < 8 else B
            return A if args[1].endswith("1") else B
        if args[0] == "diff":
            return "src/changed.py"
        return ""

    monkeypatch.setattr(materialize_module, "git", fake_git)
    result = materialize(parse_path(json.dumps([u(1)]), json.dumps([u(2, B)]), REPO))
    assert [x["pr"] for x in result["applied"]] == [1, 2]
    fetches = [v for v in seen if v[0][0] == "fetch"]
    assert len(fetches) == 2 and all(auth for _, auth in fetches)
    assert "refs/pull/1/head" in fetches[0][0][-1]
    assert "refs/pull/2/head" in fetches[1][0][-1]


def test_sha_mismatch_fails_before_any_candidate_merge(monkeypatch):
    calls = []

    def fake_git(*args, authenticated=False):
        calls.append(args)
        if args[0] == "status":
            return ""
        if args[0] == "rev-parse" and args[1] == "HEAD":
            return A
        if args[0] == "rev-parse":
            return B
        return ""

    monkeypatch.setattr(materialize_module, "git", fake_git)
    with pytest.raises(RuntimeError, match="moved"):
        materialize(parse_path("[]", json.dumps([u(1)]), REPO))
    assert not any(args[0] == "merge" for args in calls)
