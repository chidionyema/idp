"""I-8096-REV2: the two zero-click channels land one sanitized commit with no human input.

These tests drive the real edge engine (platform/lifeboat/src/aistudio.js) through its
scenario harness. Nothing here reimplements the pipeline: a simulated AI Studio stream turn
and a simulated Google Drive changes.watch push are fed in, and the assertions grade the Git
calls, the OMNIFLOW assignment, the Greenlane dispatch and the 59effb8f4 digest rule.
"""

import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "platform/lifeboat/test/aistudio-scenario.mjs"
NODE = shutil.which("node")

FIXTURE = "src/data/generalPurposePersonaData.ts"
SOURCE = "src/engine/routerCore.ts"
FILES = {
    SOURCE: "const lanes = 4;\n",
    FIXTURE: "export const personas = [];\n",
}


def encode(path):
    raw = FILES[path].encode()
    return {
        "path": path,
        "content_b64": base64.b64encode(raw).decode(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


@unittest.skipUnless(NODE, "node is required for the edge engine")
class ZeroClickIngest(unittest.TestCase):
    def run_scenario(self, mode, source, files=None):
        payload = {
            "source": source,
            "files": files or [encode(SOURCE), encode(FIXTURE)],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle)
            path = handle.name
        result = subprocess.run(
            [NODE, str(HARNESS), "--mode", mode, "--payload", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        Path(path).unlink(missing_ok=True)
        return result, json.loads(result.stdout) if result.stdout else {}

    def test_stream_turn_commits_sanitized_tree_and_wakes_the_fleet(self):
        result, data = self.run_scenario("stream", "stream")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = data["receipt"]

        self.assertTrue(receipt["ok"])
        self.assertFalse(receipt["deduped"])
        self.assertEqual(receipt["intake_rule"], "59effb8f4")
        self.assertEqual(receipt["lane"], "lane/aistudio-auto-intake")
        self.assertEqual([f["path"] for f in receipt["files"]], [SOURCE])
        self.assertEqual(receipt["sanitized"][0]["path"], FIXTURE)
        self.assertEqual(receipt["sanitized"][0]["reason"], "MOCK_FIXTURE")

        calls = [(entry["method"], entry["path"]) for entry in data["journal"]]
        self.assertEqual(
            sum(1 for m, p in calls if m == "POST" and p.endswith("/git/commits")), 1
        )
        comments = [
            e for e in data["journal"] if e["path"].endswith("/issues/8133/comments")
        ]
        self.assertEqual(len(comments), 1)
        body = comments[0]["body"]["body"]
        self.assertIn("OMNIFLOW-EVENT/v1", body)
        self.assertIn("aistudio-auto-land", body)
        self.assertIn("lane/aistudio-auto-intake", body)
        self.assertTrue(
            any(
                p.endswith("/actions/workflows/greenlane.yml/dispatches")
                for _, p in calls
            )
        )
        self.assertTrue(any(p == "/realtime" for _, p in calls))
        self.assertNotIn("test-token", result.stdout)

    def test_drive_push_dedupes_into_the_same_commit(self):
        result, data = self.run_scenario("dedup", "drive")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = data["receipt"]

        self.assertTrue(receipt["deduped"])
        self.assertEqual(receipt["source"], "drive")
        calls = [(entry["method"], entry["path"]) for entry in data["journal"]]
        self.assertEqual(
            sum(1 for m, p in calls if m == "POST" and p.endswith("/git/commits")), 0
        )
        self.assertTrue(any(p.endswith("/issues/8133/comments") for _, p in calls))

    def test_partial_flush_never_reaches_a_commit(self):
        broken = encode(SOURCE)
        broken["sha256"] = "0" * 64
        result, data = self.run_scenario("partial", "stream", [broken, encode(FIXTURE)])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data["error"], "PARTIAL_FLUSH_REJECTED")
        calls = [(entry["method"], entry["path"]) for entry in data["journal"]]
        self.assertEqual(
            sum(1 for m, p in calls if m == "POST" and p.endswith("/git/commits")), 0
        )


if __name__ == "__main__":
    unittest.main()
