"""The Greenlane tests a candidate commit and lands each lane as its own commit: a different sha with
the same tree. Measured 2026-11-13: candidate c40017e, landed head 469db1b, both tree 667b30c0.
The gate refused that land ("the proof names c40017e…, but the head is 469db1b") and Greenlane
landed nothing after 06:26Z. These falsifiers pin the fix: same tree passes, a different tree, an
unreadable tree, or a non-Greenlane proof does not."""

import importlib.machinery
import importlib.util
import pathlib
import unittest

GATE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-bdd-proof-gate"
loader = importlib.machinery.SourceFileLoader("bdd_proof_gate", str(GATE))
spec = importlib.util.spec_from_loader("bdd_proof_gate", loader)
g = importlib.util.module_from_spec(spec)
loader.exec_module(g)

CAND, HEAD, OTHER = (
    "c40017eca4c433fa09e9b521b473e35f2e9f6a55",
    "469db1bb238a" + "0" * 28,
    "deadbeef" + "1" * 32,
)
TREES = {
    CAND: "667b30c0ff5b672bf14b60eab052a934b302db9d",
    HEAD: "667b30c0ff5b672bf14b60eab052a934b302db9d",
    OTHER: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
}
LANDER = (
    "BDD-PROOF\nhead: %s\nrequired checks green on candidate %s: fast-gate / fast-gate, ci-success\n"
    "END-BDD-PROOF\n" % (CAND, CAND)
)


class SameTestedBytes(unittest.TestCase):
    def test_lander_proof_on_a_different_sha_with_the_same_tree_passes(self):
        rc, why = g.grade(LANDER, HEAD, "PR", tree_lookup=TREES.get)
        self.assertEqual(rc, g.EXIT_PROVED, why)

    def test_a_different_tree_is_refused(self):
        rc, why = g.grade(LANDER, OTHER, "PR", tree_lookup=TREES.get)
        self.assertEqual(rc, g.EXIT_REFUSED, why)

    def test_an_unreadable_tree_is_refused(self):
        rc, why = g.grade(LANDER, HEAD, "PR", tree_lookup=lambda s: None)
        self.assertEqual(rc, g.EXIT_REFUSED, why)

    def test_a_runner_proof_is_still_bound_to_the_exact_head(self):
        runner = "BDD-PROOF\nhead: %s\n12 passed, 0 failed\nEND-BDD-PROOF\n" % CAND
        rc, why = g.grade(runner, HEAD, "PR", tree_lookup=TREES.get)
        self.assertEqual(rc, g.EXIT_REFUSED, why)


if __name__ == "__main__":
    unittest.main()
