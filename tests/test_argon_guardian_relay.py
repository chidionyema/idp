"""bin/argon-guardian-relay: refuses unverified argon commits, never passes when blind, and never
leaks argon's private commit text or paths into this public repository's logs."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RELAY = os.path.join(os.path.dirname(HERE), "bin", "argon-guardian-relay")
FOUNDER = "a" * 64
PRIVATE_PATH = "private/argon-only-path.txt"
PRIVATE_MSG = "argon private subject line"

STUB = (
    """
import fs from 'node:fs';
const report = JSON.parse(fs.readFileSync(process.env.STUB_REPORT, 'utf8'));
report.base = process.env.GENESIS_BASE_SHA; report.end = process.env.GENESIS_END_SHA;
if (process.env.GENESIS_FOUNDER_CHAT_SHA256 !== '%s') { process.exit(9); }
console.log(process.env.STUB_RAW || JSON.stringify(report, null, 2));
process.exitCode = report.ok ? 0 : 1;
"""
    % FOUNDER
)


def git(cwd, *a):
    return subprocess.run(
        ["git", "-C", cwd, *a], capture_output=True, text=True, check=True
    ).stdout.strip()


class Relay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "argon")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        self.base = self._commit("seed.txt", "seed")
        self.end = self._commit(PRIVATE_PATH, PRIVATE_MSG)
        self.verifier = os.path.join(self.tmp.name, "verify_handoff.mjs")
        with open(self.verifier, "w") as fh:
            fh.write(STUB)

    def tearDown(self):
        self.tmp.cleanup()

    def _commit(self, path, msg):
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as fh:
            fh.write(msg)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)
        return git(self.repo, "rev-parse", "HEAD")

    def run_relay(
        self, ok, raw=None, base=None, end=None, verifier=None, founder=FOUNDER
    ):
        report = {
            "ok": ok,
            "commits": [
                {
                    "sha": self.end,
                    "ok": ok,
                    "changedFiles": [PRIVATE_PATH],
                    "failures": []
                    if ok
                    else [f"missing Genesis-Instruction-Id: {PRIVATE_MSG}"],
                }
            ],
        }
        rp = os.path.join(self.tmp.name, "report.json")
        with open(rp, "w") as fh:
            json.dump(report, fh)
        env = dict(os.environ, STUB_REPORT=rp)
        if raw is not None:
            env["STUB_RAW"] = raw
        out = os.path.join(self.tmp.name, "summary.json")
        r = subprocess.run(
            [
                sys.executable,
                "-I",
                RELAY,
                "--repo",
                self.repo,
                "--verifier",
                verifier or self.verifier,
                "--base",
                base or self.base,
                "--end",
                end or self.end,
                "--founder-chat-sha256",
                founder,
                "--json",
                out,
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        return r

    def assert_no_leak(self, r):
        for text in (r.stdout, r.stderr):
            self.assertNotIn(PRIVATE_PATH, text)
            self.assertNotIn(PRIVATE_MSG, text)

    def test_unverified_commit_is_refused_by_sha_without_leaking(self):
        r = self.run_relay(ok=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(f"REFUSED argon-guardian  {self.end}", r.stdout)
        self.assert_no_leak(r)
        with open(os.path.join(self.tmp.name, "summary.json")) as fh:
            summary = fh.read()
        self.assertNotIn(PRIVATE_PATH, summary)
        self.assertNotIn(PRIVATE_MSG, summary)

    def test_verified_range_passes(self):
        r = self.run_relay(ok=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("1 commit(s) verified", r.stdout)
        self.assert_no_leak(r)

    def test_empty_range_is_nothing_new(self):
        r = self.run_relay(ok=True, base=self.end, end=self.end)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("nothing new", r.stdout)

    def test_missing_verifier_is_blind_not_pass(self):
        r = self.run_relay(ok=True, verifier=os.path.join(self.tmp.name, "absent.mjs"))
        self.assertEqual(r.returncode, 2, r.stdout)

    def test_unreadable_report_is_blind_and_does_not_echo_it(self):
        r = self.run_relay(ok=True, raw=f"not json {PRIVATE_MSG}")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assert_no_leak(r)

    def test_wrong_trust_anchor_is_blind(self):
        r = self.run_relay(ok=True, founder="b" * 64)
        self.assertEqual(r.returncode, 2, r.stdout)

    def test_malformed_sha_is_blind(self):
        r = self.run_relay(ok=True, base="HEAD^")
        self.assertEqual(r.returncode, 2, r.stdout)

    def test_rewritten_history_is_refused(self):
        git(self.repo, "checkout", "-q", "--orphan", "other")
        other = self._commit("x.txt", "unrelated root")
        r = self.run_relay(ok=True, base=self.end, end=other)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("history was rewritten", r.stdout)


if __name__ == "__main__":
    unittest.main()
