"""Tests for the CRDT-backed ShadowMemory."""

from __future__ import annotations

from idp_concurrency.ttcs.shadow_memory import ShadowMemory, Triplet


def test_add_and_retrieve():
    sm = ShadowMemory(replica_id="r1")
    sm.add("edit X", "ok", "X is correct")
    out = sm.top_k(symbol="", k=8)
    assert len(out) == 1
    assert out[0].action == "edit X"
    assert out[0].result == "ok"


def test_top_k_filters_by_symbol():
    sm = ShadowMemory(replica_id="r1")
    sm.add("edit A", "ok", "A works", symbol="alpha")
    sm.add("edit B", "ok", "B works", symbol="beta")
    sm.add("edit A2", "ok", "A2 works", symbol="alpha")
    out = sm.top_k(symbol="alpha", k=8)
    assert all(t.symbol == "alpha" for t in out)
    assert len(out) == 2


def test_top_k_sorts_by_created_at_desc():
    sm = ShadowMemory(replica_id="r1")
    sm.add("first", "ok", "old", symbol="s")
    sm.add("second", "ok", "newer", symbol="s")
    sm.add("third", "ok", "newest", symbol="s")
    out = sm.top_k(symbol="s", k=8)
    assert [t.takeaway for t in out] == ["newest", "newer", "old"]


def test_top_k_respects_k():
    sm = ShadowMemory(replica_id="r1")
    for i in range(10):
        sm.add(f"a{i}", "ok", f"t{i}", symbol="s")
    out = sm.top_k(symbol="s", k=3)
    assert len(out) == 3


def test_add_negative():
    sm = ShadowMemory(replica_id="r1")
    sm.add_negative("verify failed", symbol="alpha")
    out = sm.top_k(symbol="alpha", k=8)
    assert len(out) == 1
    assert out[0].negative is True
    assert out[0].action == "verification"
    assert out[0].result == "failed"


def test_truncate_to_keeps_first_n():
    """`truncate_to(N)` keeps the first N triplets; drops the rest."""
    sm = ShadowMemory(replica_id="r1")
    for i in range(5):
        sm.add(f"a{i}", "ok", f"t{i}", symbol="s")
    sm.truncate_to(2)
    out = sm.top_k(symbol="s", k=8)
    assert len(out) == 2
    takeaways = {t.takeaway for t in out}
    assert "t0" in takeaways and "t1" in takeaways
    assert "t4" not in takeaways


def test_truncate_to_more_than_size_is_noop():
    sm = ShadowMemory(replica_id="r1")
    sm.add("a", "ok", "x")
    sm.truncate_to(99)  # larger than len()
    out = sm.top_k(symbol="", k=8)
    assert len(out) == 1


def test_two_replicas_merge_converge():
    a = ShadowMemory(replica_id="A")
    b = ShadowMemory(replica_id="B")
    a.add("X", "ok", "x-from-a", symbol="x")
    b.add("Y", "ok", "y-from-b", symbol="y")
    merged = a.merge(b)
    out_x = merged.top_k(symbol="x", k=8)
    out_y = merged.top_k(symbol="y", k=8)
    assert len(out_x) == 1 and out_x[0].takeaway == "x-from-a"
    assert len(out_y) == 1 and out_y[0].takeaway == "y-from-b"


def test_merge_is_commutative():
    a = ShadowMemory(replica_id="A")
    b = ShadowMemory(replica_id="B")
    a.add("p", "ok", "p-a", symbol="p")
    b.add("q", "ok", "q-b", symbol="q")
    a.add_negative("bad-a", symbol="p")
    left = a.merge(b)
    right = b.merge(a)
    assert sorted(t.takeaway for t in left.top_k(symbol="", k=16)) == sorted(
        t.takeaway for t in right.top_k(symbol="", k=16)
    )


def test_merge_preserves_negative_flag():
    a = ShadowMemory(replica_id="A")
    b = ShadowMemory(replica_id="B")
    a.add_negative("oops", symbol="x")
    merged = a.merge(b)
    out = merged.top_k(symbol="x", k=8)
    assert out[0].negative is True
