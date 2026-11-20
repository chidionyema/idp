"""Regression for #8350: an unusable first slot must not stop formation."""
from greenlane import engine as E

MAIN = "a" * 40


class World:
    def __init__(self, conflict=(), missing=(), red=()):
        self.conflict = set(conflict)
        self.missing = set(missing)
        self.red = set(red)
        self.calls = []
        self.pushed = []

    def main(self):
        return MAIN

    def now(self):
        return 10.0

    def unclaimed(self, head, base):
        return ""

    def rebase(self, head, onto, lane=""):
        self.calls.append((head, onto))
        if head in self.missing:
            raise E.UnavailableLaneObject(head)
        if head in self.conflict:
            return None
        return "candidate-" + head

    def preflight(self, base, tip):
        return (tip.removeprefix("candidate-") not in self.red, "preflight")

    def report(self, *args):
        pass

    def push_candidate(self, batch, tip):
        self.pushed.append((batch, tip))


def state(*heads):
    s = E.State()
    for seq, head in enumerate(heads):
        name = "lane/" + head
        s.lanes[name] = E.Lane(name, head, seq=seq)
    return s


def form(world, s):
    E.Engine(world, s, batch_size=1)._start_batch()
    return None if s.batch is None else s.batch.members[0][0]


def test_conflicting_first_slot_does_not_starve_good_lane():
    w, s = World(conflict=["bad"]), state("bad", "good")
    assert form(w, s) == "lane/good"
    assert s.lanes["lane/bad"].status == E.CONFLICT
    assert len(w.pushed) == 1


def test_missing_object_is_deferred_not_conflicted():
    w, s = World(missing=["missing"]), state("missing", "good")
    assert form(w, s) == "lane/good"
    assert s.lanes["lane/missing"].status == E.PENDING
    assert len([c for c in w.calls if c[0] == "missing"]) == 1


def test_preflight_rejection_releases_slot():
    w, s = World(red=["bad"]), state("bad", "good")
    assert form(w, s) == "lane/good"
    assert s.lanes["lane/bad"].status == E.RED


def test_all_missing_ends_without_candidate_and_preserves_lanes():
    w, s = World(missing=["a", "b"]), state("a", "b")
    assert form(w, s) is None
    assert len(w.calls) == 2
    assert not w.pushed
    assert all(x.status == E.PENDING for x in s.lanes.values())


def test_empty_bisection_group_does_not_starve_pending():
    w, s = World(), state("good")
    s.queued = [["lane/absent"]]
    assert form(w, s) == "lane/good"


def test_conflicting_bisection_group_does_not_starve_next_group():
    w, s = World(conflict=["bad"]), state("bad", "good")
    s.queued = [["lane/bad"], ["lane/good"]]
    assert form(w, s) == "lane/good"
    assert s.queued == []


def test_many_conflicts_do_not_recurse():
    heads = ["x" + str(i) for i in range(1100)]
    w, s = World(conflict=heads), state(*heads, "good")
    assert form(w, s) == "lane/good"
    assert len(w.calls) == len(heads) + 2
    assert len(w.pushed) == 1
