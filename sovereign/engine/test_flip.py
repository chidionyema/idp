"""unittest for sovereign/engine/flip.py (cp13). Run:
    PYTHONPATH=. sovereign/.venv/bin/python -m unittest sovereign.engine.test_flip -v

Never opens maestro's real database -- every test builds its own
disposable sqlite3 file and points config.SIDECAR_TARGET at that, same
pattern as sovereign/sidecar/test_sidecar.py.
"""
from __future__ import annotations

import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sovereign import config
from sovereign.engine import flip, receipts
from sovereign.sidecar import core as sidecar_core

_FIXED_KEY = b"\x0d" * 32


class FlipTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.db_path = root / "legacy.db"
        for name, val in (
            ("SB_RECEIPTS", root / "receipts.jsonl"),
            ("RECEIPTS_HEAD", root / "receipts.head"),
            ("SHADOW_HEADS_DIR", root / "heads"),
            ("SIDECAR_TARGET", f"{self.db_path}#episodes"),
        ):
            p = patch.object(config, name, val)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(receipts, "get_or_create_key", lambda: (_FIXED_KEY, "software_file"))
        p.start()
        self.addCleanup(p.stop)

        # HardwareTrustAnchor() with no backend override defaults to
        # trust.backend="auto", which on Darwin shells out to `xcrun
        # swiftc` to compile sovereign/trust/presence_helper.swift on
        # first use (sovereign/trust/anchor.py:_ensure_swift_helper_
        # compiled). In a non-interactive test/CI shell without Xcode's
        # licence already accepted, that subprocess blocks forever on a
        # licence prompt with no TTY to answer it -- confirmed via
        # faulthandler.dump_traceback_later, which caught the test process
        # parked in subprocess.communicate() inside anchor.py's
        # _run_helper. Every other suite that signs (sovereign/trust/
        # test_trust.py) already pins backend="software_key" per instance;
        # this env override does the same for the instance receipts.append
        # constructs internally, which this module has no other way to
        # reach.
        p = patch.dict("os.environ", {"SB_TRUST_BACKEND": "software_key"})
        p.start()
        self.addCleanup(p.stop)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY, lane TEXT, note TEXT)")
        self.conn.execute("INSERT INTO episodes (id, lane, note) VALUES ('seed', 'ops', 'n')")
        self.conn.commit()
        self.addCleanup(self._close_conn)
        self.sc = sidecar_core.attach(self.conn, "episodes", dag_dir=root / "dag")
        self.sc.drain()

    def _close_conn(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    def _restore_writable_for_cleanup(self) -> None:
        # tempfile cleanup needs the dir/file writable regardless of
        # what a test left it in
        try:
            self.db_path.chmod(0o644)
        except OSError:
            pass


class FlipPropertyTest(FlipTestBase):
    def test_property_flip_sets_readonly_fast_and_signs_the_exact_receipt_line(self) -> None:
        self.addCleanup(self._restore_writable_for_cleanup)
        for i in range(20):
            self.assertFalse(flip.is_read_only(self.db_path), f"iteration {i}: starts writable")
            result = flip.flip(by="founder", signed=True)
            self.assertLess(result["downtime_ms"], config.FLIP_MAX_DOWNTIME_MS)
            self.assertTrue(flip.is_read_only(self.db_path), "the legacy DB is set read-only")

            last = receipts.read_all()[-1]
            self.assertEqual(last["kind"], "flip")
            self.assertEqual(last["text"], config.FLIP_RECEIPT_TEMPLATE.format(root=result["root"]))
            self.assertIn("hw_sig", last, "--signed reaches receipts.append(signed=True)")

            # a *fresh* writer's open() is what the OS permission bit
            # gates -- self.conn already holds an fd opened before the
            # chmod, so it must use a new connection to demonstrate the
            # invariant the module docstring claims: "every future
            # writer, in this process or any other, hits an OS
            # PermissionError". Reads are unaffected either way.
            self.conn.execute("SELECT * FROM episodes").fetchall()
            fresh = sqlite3.connect(str(self.db_path))
            self.addCleanup(fresh.close)
            fresh.execute("SELECT * FROM episodes").fetchall()
            with self.assertRaises(sqlite3.OperationalError):
                fresh.execute("INSERT INTO episodes (id, lane, note) VALUES ('x', 'ops', 'n')")
                fresh.commit()
            fresh.close()

            rb = flip.rollback(by="founder", signed=True)
            self.assertEqual(rb["legacy"], "writable")
            self.assertFalse(flip.is_read_only(self.db_path), "writable again after rollback")
            last = receipts.read_all()[-1]
            self.assertEqual(last["kind"], "flip_rollback")
            self.assertEqual(last["text"], config.FLIP_ROLLBACK_RECEIPT_TEMPLATE.format(root=rb["root"]))


class FlipRollbackTest(FlipTestBase):
    def test_rollback_refuses_with_no_prior_flip(self) -> None:
        with self.assertRaises(flip.FlipError):
            flip.rollback(by="founder")

    def test_incident_cp13_rollback_refuses_when_legacy_bytes_changed_while_flipped(self) -> None:
        """cp13's own safety bar: rollback() must never hand back write
        access to a legacy DB whose bytes no longer match the sha256 the
        flip receipt recorded -- that is the one way "consistent with
        the root at flip time" can be violated (something bypassing the
        OS permission bit while flipped), and it must fail closed, not
        silently."""
        self.addCleanup(self._restore_writable_for_cleanup)
        flip.flip(by="founder", signed=True)
        self.assertTrue(flip.is_read_only(self.db_path))

        # simulate an out-of-band bypass of the permission bit (e.g. root)
        self.db_path.chmod(0o644)
        with open(self.db_path, "r+b") as f:
            f.seek(0)
            f.write(b"\x00")
        self.db_path.chmod(0o444)

        with self.assertRaises(flip.FlipError):
            flip.rollback(by="founder", signed=True)
        self.assertTrue(flip.is_read_only(self.db_path), "refused rollback leaves the file exactly as it was")


if __name__ == "__main__":
    unittest.main()
