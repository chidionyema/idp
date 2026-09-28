"""Real tests for the OR-Set CRDT — proves the join-semilattice properties."""

from __future__ import annotations


from idp_concurrency.crdt_doc import ORSet


def test_add_then_contains():
    s = ORSet(replica_id="r1")
    assert "a" not in s
    s.add("a")
    assert "a" in s
    assert len(s) == 1


def test_remove_observed_tags():
    s = ORSet(replica_id="r1")
    s.add("a")
    s.add("a")  # two tags for the same element
    assert "a" in s
    s.remove("a")
    assert "a" not in s


def test_re_add_after_remove_works():
    """Observed-remove: a fresh add after remove resurrects the element."""
    s = ORSet(replica_id="r1")
    s.add("a")
    s.remove("a")
    s.add("a")  # new tag, not in tombstones
    assert "a" in s


def test_concurrent_adds_on_two_replicas_converge():
    a = ORSet(replica_id="A")
    b = ORSet(replica_id="B")
    a.add("x")
    b.add("y")
    merged = a.merge(b)
    assert "x" in merged and "y" in merged
    assert len(merged) == 2


def test_concurrent_add_and_remove_converge_to_add():
    """Replica A adds, replica B removes the *prior* state — merge keeps both adds."""
    a = ORSet(replica_id="A")
    b = ORSet(replica_id="B")
    b.add("x")  # B's pre-existing state
    b_observed = ORSet(replica_id="B")
    b_observed.tags = {e: set(t) for e, t in b.tags.items()}
    b_observed._counter = b._counter

    a.add("x")  # A adds concurrently
    b_observed.remove("x")  # B removes the prior version

    merged = a.merge(b_observed)
    assert "x" in merged  # A's add survives B's remove of prior state


def test_merge_is_commutative():
    a = ORSet(replica_id="A")
    b = ORSet(replica_id="B")
    a.add("p")
    a.add("q")
    b.add("r")
    b.remove("q")  # b never had q, but the merge must not care
    assert sorted(a.merge(b)) == sorted(b.merge(a))


def test_merge_is_idempotent():
    a = ORSet(replica_id="A")
    a.add("p")
    a.add("q")
    a.remove("p")
    once = a.merge(a)
    twice = once.merge(once)
    assert sorted(once) == sorted(twice)


def test_merge_is_associative():
    a = ORSet(replica_id="A")
    b = ORSet(replica_id="B")
    c = ORSet(replica_id="C")
    a.add("p")
    b.add("q")
    c.add("r")
    left = (a.merge(b)).merge(c)
    right = a.merge(b.merge(c))
    assert sorted(left) == sorted(right)


def test_merge_is_monotonic_growth():
    """Adding an element after a merge must still be present."""
    a = ORSet(replica_id="A")
    b = ORSet(replica_id="B")
    a.add("p")
    merged = a.merge(b)
    merged.add("q")
    assert "p" in merged and "q" in merged


def test_stress_100_concurrent_adds():
    """100 replicas each add a unique element; merged set has all 100."""
    replicas = [ORSet(replica_id=f"r{i}") for i in range(100)]
    for i, r in enumerate(replicas):
        r.add(f"e{i}")
    merged = replicas[0]
    for r in replicas[1:]:
        merged = merged.merge(r)
    assert len(merged) == 100
    assert all(f"e{i}" in merged for i in range(100))
