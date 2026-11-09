#!/usr/bin/env python3
"""Falsifiers for bws-sync: mapped names move, unmapped never do, a missing secret refuses, and no
value is ever printed."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("bws", Path(__file__).with_name("bws-sync.py"))
bws = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bws)


class SyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.written: list[tuple[str, str]] = []
        self.available = {"CLOUDFLARE_ROOT_TOKEN": {"id": "id-1", "value": "cf-value"},
                          "UNMAPPED_EXTRA": {"id": "id-9", "value": "should-not-move"}}
        bws.bws_secrets = lambda: {k: v["id"] for k, v in self.available.items()}
        bws.bws_value = lambda sid: next(v["value"] for v in self.available.values() if v["id"] == sid)
        bws.vault_write = lambda entry, key, value: (self.written.append((entry, key, value)), True)[1]
        # A one-entry map for the behaviour tests; the real map is exercised by its own test.
        self.mapfile = Path(self.available and "/tmp/bws/.test-map.json")
        self.mapfile.write_text(json.dumps({"CLOUDFLARE_ROOT_TOKEN": {"entry": "SEED_CLOUDFLARE_ROOT_TOKEN", "key": "token"}}))
        self.real_map, bws.MAP = bws.MAP, self.mapfile

    def test_only_mapped_names_are_planned(self) -> None:
        rows = bws.plan({"CLOUDFLARE_ROOT_TOKEN": {"entry": "SEED_CLOUDFLARE_ROOT_TOKEN", "key": "token"}})
        self.assertEqual([r["bws"] for r in rows], ["CLOUDFLARE_ROOT_TOKEN"])
        self.assertNotIn("UNMAPPED_EXTRA", [r["bws"] for r in rows])

    def test_apply_writes_the_mapped_entry_and_nothing_else(self) -> None:
        rc = bws.main(["--apply"])
        self.assertEqual(rc, 0)
        names = [w[0] for w in self.written]
        self.assertIn("SEED_CLOUDFLARE_ROOT_TOKEN", names)
        self.assertNotIn("UNMAPPED_EXTRA", names)

    def test_a_missing_mapped_secret_refuses_before_writing(self) -> None:
        self.available.pop("CLOUDFLARE_ROOT_TOKEN")
        rc = bws.main(["--apply"])
        self.assertEqual(rc, 1)
        self.assertFalse([w for w in self.written if w[0] == "SEED_CLOUDFLARE_ROOT_TOKEN"])

    def test_the_value_is_never_printed(self) -> None:
        import io
        from contextlib import redirect_stdout, redirect_stderr
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            bws.main(["--plan"])
        self.assertNotIn("cf-value", out.getvalue() + err.getvalue())

    def test_the_map_covers_the_credential_that_broke(self) -> None:
        mapping = json.loads(Path(self.real_map).read_text())
        self.assertEqual(mapping["CLOUDFLARE_ROOT_TOKEN"]["entry"], "SEED_CLOUDFLARE_ROOT_TOKEN")
        self.assertEqual(mapping["CLOUDFLARE_ROOT_TOKEN"]["key"], "token")


if __name__ == "__main__":
    unittest.main(verbosity=2)
