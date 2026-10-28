import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from aei.core import Store, make_event, validate
from aei.analysis import analyse, compare
from aei.contract import validate_manifest
from aei.client import Emitter
from aei.demo import populate

IDENTITY = dict(
    run_id="r",
    task_id="t",
    agent_id="a",
    harness_id="h",
    trace_id="trace",
    revision="sha",
)


class AEITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "aei.db"

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, typ="task.started", **kw):
        return make_event(typ, **IDENTITY, **kw)

    def test_identity(self):
        e = self.event()
        self.assertEqual(e["run_id"], "r")
        self.assertEqual(e["schema"], "aei.event.v1")

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            self.event("invented.action")

    def test_secret_redaction(self):
        e = self.event(
            attributes={
                "reason_code": "token=super-secret-value",
                "private_prompt": "do not store",
            }
        )
        self.assertNotIn("private_prompt", e["attributes"])
        self.assertIn("[REDACTED]", e["attributes"]["reason_code"])

    def test_unclassified_rejected(self):
        e = self.event()
        e["attributes"]["raw_prompt"] = "sensitive"
        with self.assertRaises(ValueError):
            validate(e)

    def test_idempotent_and_conflict(self):
        s = Store(self.path)
        e = self.event()
        self.assertTrue(s.append(e)["accepted"])
        self.assertFalse(s.append(e)["accepted"])
        changed = copy.deepcopy(e)
        changed["attributes"] = {"status": "changed"}
        with self.assertRaises(ValueError):
            s.append(changed)
        self.assertEqual(len(s.events("r")), 1)
        s.close()

    def test_reopen(self):
        s = Store(self.path)
        s.append(self.event())
        s.close()
        s = Store(self.path)
        self.assertEqual(len(s.events("r")), 1)
        s.close()

    def test_missing_cost(self):
        self.assertIsNone(analyse([self.event()])["metrics"]["observed_cost_usd"])

    def test_no_invented_spans(self):
        self.assertEqual(analyse([self.event("model.requested")])["waterfall"], [])

    def test_compare_not_verified(self):
        e = self.event()
        self.assertFalse(compare([e], [e])["comparable"])

    def test_manifest(self):
        d = json.loads(
            (Path(__file__).parent.parent / "examples/router.manifest.json").read_text()
        )
        self.assertTrue(validate_manifest(d))
        d["visualisations"] = []
        with self.assertRaises(ValueError):
            validate_manifest(d)

    def test_demo(self):
        s = Store(self.path)
        rid = populate(s)
        e = analyse(s.events(rid))
        self.assertTrue(e["coverage"]["task_terminal"])
        self.assertTrue(e["coverage"]["verification_observed"])
        s.close()

    def test_nonblocking_emitter(self):
        c = Emitter("http://127.0.0.1:1", "invalid", IDENTITY, timeout=0.05)
        start = time.monotonic()
        self.assertIsNotNone(c.emit("task.started"))
        self.assertLess(time.monotonic() - start, 0.1)
        c.close()

    def test_parent_is_observed_only(self):
        e = self.event()
        self.assertEqual(analyse([e])["graph"]["edges"], [])

    def test_bad_timestamp(self):
        e = self.event()
        e["timestamp"] = "nonsenseZ"
        with self.assertRaises(ValueError):
            validate(e)


if __name__ == "__main__":
    unittest.main()
