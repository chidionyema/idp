"""The Chronos board reaches the founder's surface, and a blind board never replaces a true one.

The founder's live surface is ARGON (`~/.estate/argon/.genesis/live-surface`, 127.0.0.1:3000,
verified 200 on 2026-11-08). It reads idp state by ONE shallow TOKENLESS git fetch of
`refs/greenlane/state` (`src/engine/greenlaneFeed.ts`), so Chronos publishes a sibling ref
rather than opening a second transport, a second token or a second REST channel -- AGENTS.md
section 6: one of each layer, a second copy is a stitch.

The tests never touch origin. They grade the payload contract and the one refusal that keeps
the founder's board honest: when the registry cannot be graded the detector exits 2, and a
blind board must not be published over the last true one.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "bin/idp-estate-clocks-publish"


def _load():
    loader = importlib.machinery.SourceFileLoader("estate_clocks_publish", str(PUBLISH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_ref_is_a_sibling_of_the_one_argon_already_reads():
    """The same shape as refs/greenlane/state, which greenlaneFeed.ts already fetches.

    A different ref is a deliberate choice, not an oversight: greenlane's state.json is written
    under the lane's own compare-and-swap lease, and a second writer into that file is the
    two-owners-one-file defect that stranded lanes b2953/b2954.
    """
    mod = _load()
    assert mod.STATE_REF == "refs/chronos/state", mod.STATE_REF
    assert mod.STATE_REF.startswith("refs/"), mod.STATE_REF
    assert mod.STATE_REF != "refs/greenlane/state"


def test_the_payload_carries_the_board_and_the_moment_it_was_measured():
    """A board without its measurement time cannot be judged: it is only as true as its tick."""
    mod = _load()
    board = {
        "legion": "estate-clocks",
        "obligations": [{"id": "ping", "verdict": "MEASURED_OK"}],
    }
    payload = json.loads(mod.build_payload(board))
    assert payload["schema"] == "chronos/1", payload
    assert payload["board"] == board, payload
    assert isinstance(payload["tickAt"], int) and payload["tickAt"] > 0, payload
    assert payload["publishedAt"].endswith("Z"), payload


def test_the_reader_stamps_its_own_fetched_at_and_the_publisher_never_invents_one():
    """`fetchedAt` is the reader's fact. A publisher that wrote it would claim to know when
    someone else looked at the board."""
    mod = _load()
    payload = json.loads(mod.build_payload({"obligations": []}))
    assert "fetchedAt" not in payload, payload


def test_a_blind_registry_publishes_nothing():
    """THE REFUSAL. If the registry cannot be graded, the board on the founder's surface must
    keep its last true value. Publishing an empty board would render as 'everything is fine'
    when the truth is 'we cannot see' -- the fail-open defect AGENTS.md section 9 R1 names."""
    mod = _load()
    published = []
    mod.publish = lambda text, **kw: published.append(text) or "deadbeef"
    mod.measure_registry = lambda: (
        2,
        None,
        "BLIND chronos: /tmp/nope.json: the registry does not exist, "
        "so nothing can be graded",
    )
    rc = mod.main(["--no-push"])
    assert rc == 2, rc
    assert published == [], "a BLIND registry must publish nothing"


def test_a_missed_cadence_is_published_because_it_is_a_finding():
    """Exit 1 is not blindness: a missed cycle is exactly what the founder must be able to see.
    Only exit 2 (nothing could be measured) refuses."""
    mod = _load()
    published = []
    mod.publish = lambda text, **kw: published.append(text) or "deadbeef"
    mod.measure_registry = lambda: (
        1,
        {"obligations": [{"id": "ping", "verdict": "MISSED_CYCLE"}]},
        "{}",
    )
    rc = mod.main(["--no-push"])
    assert rc == 0, rc
    assert len(published) == 1, published
    assert '"MISSED_CYCLE"' in published[0], published[0]


def test_dry_run_touches_nothing():
    """A dry run must be safe to run anywhere, including on a machine with no push rights."""
    mod = _load()
    called = []
    mod.publish = lambda text, **kw: called.append(text) or "deadbeef"
    mod.measure_registry = lambda: (0, {"obligations": []}, "{}")
    rc = mod.main(["--dry-run"])
    assert rc == 0, rc
    assert called == [], "dry-run must not write a ref"


def _fake_git_publisher(monkeypatch, mod, *, remote_sha, lookup_rc=0):
    calls = []

    def fake_run(cmd, *, check=True, stdin=None):
        calls.append(cmd)
        if cmd[:2] == ["git", "rev-parse"]:
            return 1, ""  # a fresh Actions checkout has no local chronos ref
        if cmd[:3] == ["git", "ls-remote", "--refs"]:
            return lookup_rc, f"{remote_sha}\trefs/chronos/state" if remote_sha else ""
        if cmd[:2] == ["git", "hash-object"]:
            return 0, "b" * 40
        if cmd[:2] == ["git", "mktree"]:
            return 0, "c" * 40
        if cmd[:2] == ["git", "commit-tree"]:
            return 0, "d" * 40
        if cmd[:2] == ["git", "update-ref"]:
            return 0, ""
        if cmd[:2] == ["git", "push"]:
            return 0, ""
        raise AssertionError(f"unexpected git command: {cmd}")

    monkeypatch.setattr(mod, "run", fake_run)
    return calls


def test_fresh_runner_uses_existing_remote_lease_not_empty_lease(monkeypatch):
    mod = _load()
    sha = "a" * 40
    calls = _fake_git_publisher(monkeypatch, mod, remote_sha=sha)
    assert mod.publish('{"schema":"chronos/1"}') == "d" * 40
    assert ["git", "ls-remote", "--refs", "origin", mod.STATE_REF] in calls
    pushes = [c for c in calls if c[:2] == ["git", "push"]]
    assert len(pushes) == 1
    assert f"--force-with-lease={mod.STATE_REF}:{sha}" in pushes[0]


def test_remote_lease_lookup_failure_refuses_publish_before_writing(monkeypatch):
    import pytest

    mod = _load()
    calls = _fake_git_publisher(monkeypatch, mod, remote_sha="", lookup_rc=128)
    with pytest.raises(RuntimeError, match="cannot read remote Chronos lease"):
        mod.publish('{"schema":"chronos/1"}')
    assert not any(c[:2] == ["git", "push"] for c in calls)
    assert not any(c[:2] == ["git", "update-ref"] for c in calls)


def test_first_ever_remote_ref_can_be_created_with_empty_lease(monkeypatch):
    mod = _load()
    calls = _fake_git_publisher(monkeypatch, mod, remote_sha="")
    assert mod.publish('{"schema":"chronos/1"}') == "d" * 40
    pushes = [c for c in calls if c[:2] == ["git", "push"]]
    assert f"--force-with-lease={mod.STATE_REF}:" in pushes[0]
