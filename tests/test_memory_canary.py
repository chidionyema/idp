import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")


def load(name, fname):
    loader = importlib.machinery.SourceFileLoader(name, os.path.join(BIN, fname))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


canary = load("estate_memory_canary", "estate-memory-canary")
audit = load("estate_memory_audit", "estate-memory-audit")

RT = ["a", "b", "c"]


class Store(object):
    """A fake shared memory: what was planted, and how each reader renders it."""

    def __init__(self):
        self.facts = []


def make_registry(store, down=(), blind=(), poison_label=None):
    """Writers append to the store. Readers show it, except `blind` (sees nothing) and `down`."""
    reg = {"runtimes": {}, "surfaces": {}}

    def writer(name):
        def w(ctx, marker, fact):
            if name in down:
                raise canary.Unreachable("%s down" % name)
            store.facts.append(fact)

        return w

    def reader(name):
        def r(ctx, marker):
            if name in down:
                raise canary.Unreachable("%s down" % name)
            if name in blind:
                return "nothing here"
            out = []
            for f in store.facts:
                if "FALSE" in f and poison_label:
                    out.append(poison_label + "\n" + f)
                else:
                    out.append(f)
            return "\n".join(out)

        return r

    for n in RT:
        reg["runtimes"][n] = canary.Adapter(n, writer(n), reader(n))
    for s in canary.SURFACES:
        reg["surfaces"][s] = canary.Adapter(s, writer(s), reader(s))
    return reg


def run(reg):
    return canary.run_canary(reg, canary.Ctx(env={}), RT, canary.SURFACES, run_id="t1")


class CanaryTests(unittest.TestCase):
    def test_all_true_is_clean(self):
        r = run(make_registry(Store(), poison_label="UNVERIFIED:"))
        self.assertTrue(all(v is True for v in r["pairs"].values()))
        self.assertEqual(len(r["pairs"]), 6)
        self.assertTrue(all(v is True for v in r["surfaces"].values()))
        self.assertIs(r["poison"]["ok"], True)
        self.assertEqual(r["unproven"], 0)
        self.assertEqual(canary.exit_code(r), 0)

    def test_pair_false_when_reader_misses_marker(self):
        r = run(make_registry(Store(), blind=["b"], poison_label="unverified"))
        self.assertIs(r["pairs"]["a->b"], False)
        self.assertIs(r["pairs"]["a->c"], True)
        self.assertEqual(canary.exit_code(r), 1)

    def test_unreachable_is_null_not_true(self):
        r = run(make_registry(Store(), down=["c"], poison_label="unverified"))
        self.assertIsNone(r["pairs"]["a->c"])  # reader down
        self.assertIsNone(r["pairs"]["c->a"])  # writer down
        self.assertIs(r["pairs"]["a->b"], True)
        self.assertGreaterEqual(r["unproven"], 2)
        ids = [x["id"] for x in r["unproven_reasons"]]
        self.assertIn("a->c", ids)
        self.assertFalse(r["all_proven"])
        self.assertEqual(canary.exit_code(r), 2)

    def test_unreachable_surface_is_null(self):
        reg = make_registry(Store(), poison_label="unverified")
        reg["surfaces"]["telegram"].reader = canary_stub("no bot")
        r = run(reg)
        self.assertIsNone(r["surfaces"]["telegram"])
        self.assertIn("surface:telegram", [x["id"] for x in r["unproven_reasons"]])
        self.assertNotEqual(canary.exit_code(r), 0)

    def test_adapter_crash_is_never_true(self):
        reg = make_registry(Store(), poison_label="unverified")

        def boom(ctx, marker):
            raise ValueError("bug")

        reg["runtimes"]["b"].reader = boom
        r = run(reg)
        self.assertIsNone(r["pairs"]["a->b"])

    def test_poison_served_as_current_fails(self):
        r = run(make_registry(Store()))  # no unverified label anywhere
        self.assertIs(r["poison"]["ok"], False)
        self.assertTrue(r["poison"]["served_as_current"])
        self.assertEqual(canary.exit_code(r), 1)
        self.assertIn("SERVED AS CURRENT", r["summary"])

    def test_poison_absent_is_fine(self):
        reg = make_registry(Store(), blind=RT + canary.SURFACES)
        r = run(reg)
        self.assertIs(r["poison"]["ok"], True)

    def test_poison_unreadable_is_unproven(self):
        reg = make_registry(Store(), down=RT + canary.SURFACES)
        r = run(reg)
        self.assertIsNone(r["poison"]["ok"])
        self.assertNotEqual(canary.exit_code(r), 0)

    def test_audit_accepts_fully_true_result_and_rejects_null(self):
        r = run(make_registry(Store(), poison_label="unverified"))
        with tempfile.TemporaryDirectory() as home:
            out = os.path.join(home, "canary-result.json")
            canary.write_result(r, out)
            now = audit.datetime.now(audit.timezone.utc)
            self.assertEqual(
                audit.live_probe({"t": "canary", "path": out}, home, RT, now, False),
                ("ok", ""),
            )
            for s in canary.SURFACES:
                p = {"t": "canary_surface", "path": out, "surface": s}
                self.assertEqual(audit.live_probe(p, home, RT, now, False), ("ok", ""))
            # the same run with one unreachable reader must not pass the audit
            r2 = run(make_registry(Store(), down=["c"], poison_label="unverified"))
            canary.write_result(r2, out)
            st, why = audit.live_probe(
                {"t": "canary", "path": out}, home, RT, now, False
            )
            self.assertEqual(st, "fail")

    def test_real_tool_with_nothing_reachable_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as home:
            out = os.path.join(home, "x", "canary-result.json")
            env = dict(
                os.environ,
                ESTATE_GRAPH_SPOOL=os.path.join(home, "spool"),
                ESTATE_CANARY_CLAIM_BRIEF=os.path.join(home, "absent"),
                ESTATE_CANARY_FLEET_URL="http://127.0.0.1:1",
                MCP_GATEWAY_KEY="",
                HOME=home,
            )
            p = subprocess.run(
                [
                    sys.executable,
                    os.path.join(BIN, "estate-memory-canary"),
                    "--out",
                    out,
                ],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            res = json.load(open(out))
            self.assertNotIn(True, res["pairs"].values())
            self.assertGreater(res["unproven"], 0)
            self.assertFalse(os.path.exists(os.path.join(home, "spool")))

    def test_claim_brief_reader_reads_planted_spool_fact(self):
        with tempfile.TemporaryDirectory() as home:
            stub = os.path.join(home, "brief")
            open(stub, "w").write(
                "import os,glob,sys\n"
                "for f in glob.glob(os.environ['ESTATE_GRAPH_SPOOL']+'/*.md'):\n"
                "    sys.stdout.write(open(f).read())\n"
            )
            ctx = canary.Ctx(
                env={
                    "ESTATE_GRAPH_SPOOL": os.path.join(home, "s"),
                    "ESTATE_CANARY_CLAIM_BRIEF": stub,
                }
            )
            canary.runtime_writer("a")(ctx, "M-1", "fact M-1")
            self.assertIn("M-1", canary.claim_brief_reader("b")(ctx, "M-1"))
            canary.cleanup(ctx)
            self.assertFalse(os.path.exists(os.path.join(home, "s")))


def canary_stub(reason):
    return canary.stub(reason)


if __name__ == "__main__":
    unittest.main()
