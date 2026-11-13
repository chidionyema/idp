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


def _git(cwd, *args):
    import subprocess

    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@estate.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@estate.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "PATH": __import__("os").environ["PATH"],
    }
    p = subprocess.run(  # noqa: S603
        ["git", *args], cwd=cwd, capture_output=True, text=True, env=env
    )
    assert p.returncode == 0, (args, p.stderr)
    return p.stdout.strip()


def _origin_with_a_published_board(tmp_path, monkeypatch):
    """A bare origin that already holds refs/chronos/state, and a FRESH clone that never saw it.

    That is every scheduled runner: actions/checkout fetches the branch, never refs/chronos/*.
    """
    for key, val in (
        ("GIT_AUTHOR_NAME", "t"),
        ("GIT_AUTHOR_EMAIL", "t@estate.invalid"),
        ("GIT_COMMITTER_NAME", "t"),
        ("GIT_COMMITTER_EMAIL", "t@estate.invalid"),
        ("GIT_CONFIG_GLOBAL", "/dev/null"),
        ("GIT_CONFIG_SYSTEM", "/dev/null"),
    ):
        monkeypatch.setenv(key, val)
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    runner = tmp_path / "runner"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "init", "-q", "-b", "main", str(seed))
    (seed / "f").write_text("1\n")
    _git(seed, "add", "f")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", str(origin), "main", "main:refs/chronos/state")
    _git(tmp_path, "clone", "-q", "-b", "main", str(origin), str(runner))
    first = _git(origin, "rev-parse", "refs/chronos/state")
    assert _git(runner, "for-each-ref", "refs/chronos") == "", (
        "the clone must not hold the ref"
    )
    return origin, seed, runner, first


def test_a_fresh_runner_that_never_fetched_the_ref_still_publishes_over_it(
    tmp_path, monkeypatch
):
    """Run 43265495031 (2026-11-12): `! [rejected] ... refs/chronos/state (stale info)`.

    The lease was read only when the ref existed LOCALLY. A fresh checkout has no local
    refs/chronos/state, so the lease was empty, which tells git "the ref must not exist" --
    and once the first board was published every later runner was refused. The lease is the
    REMOTE's value, so it is read from the remote whatever the local clone holds.
    """
    mod = _load()
    origin, _seed, runner, first = _origin_with_a_published_board(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "REPO_ROOT", runner)
    commit = mod.publish(
        mod.build_payload({"legion": "estate-clocks", "obligations": []})
    )
    now = _git(origin, "rev-parse", "refs/chronos/state")
    assert now == commit and now != first, (first, commit, now)


def test_a_publisher_that_lost_the_race_is_refused_and_the_winner_stays(
    tmp_path, monkeypatch
):
    """The falsifier for the fix above: reading the lease from origin must not become a blind force."""
    import pytest

    mod = _load()
    origin, seed, runner, _first = _origin_with_a_published_board(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "REPO_ROOT", runner)
    real_run = mod.run

    def racing_run(cmd, **kw):
        if cmd[:2] == ["git", "push"]:
            (seed / "f").write_text("winner\n")
            _git(seed, "commit", "-q", "-am", "winner")
            _git(seed, "push", "-q", "-f", str(origin), "main:refs/chronos/state")
        return real_run(cmd, **kw)

    monkeypatch.setattr(mod, "run", racing_run)
    with pytest.raises(RuntimeError):
        mod.publish(mod.build_payload({"legion": "estate-clocks", "obligations": []}))
    assert _git(origin, "rev-parse", "refs/chronos/state") == _git(
        seed, "rev-parse", "main"
    )
