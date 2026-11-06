"""Offline adversarial regression tests for estate recovery dump selection."""
from __future__ import annotations

import gzip
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from verify_source_schema import count_target_table_definitions

SCRIPT = Path(__file__).with_name("verify_source_schema.py")


class DumpSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.archive = Path(self.tmp.name) / "source.sql.gz"

    def tearDown(self):
        self.tmp.cleanup()

    def write_dump(self, sql: str):
        self.archive.write_bytes(gzip.compress(sql.encode("utf-8")))

    def test_pg18_connect_and_target_table_passes(self):
        self.write_dump(
            "CREATE DATABASE estate WITH TEMPLATE = template0;\n"
            '\\connect -reuse-previous=on "dbname=\'estate\'"\n'
            "CREATE TABLE public.receipts (id integer);\n"
        )
        self.assertEqual(count_target_table_definitions(self.archive, "estate"), 1)
        run = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.archive), "estate"],
            capture_output=True, text=True
        )
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_database_declaration_without_tables_is_rejected(self):
        self.write_dump("CREATE DATABASE estate WITH TEMPLATE = template0;\n"
                        "\\connect estate\n-- no user tables\n")
        self.assertEqual(count_target_table_definitions(self.archive, "estate"), 0)
        run = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.archive), "estate"],
            capture_output=True, text=True
        )
        self.assertEqual(run.returncode, 1)
        self.assertIn("no target-scoped", run.stderr)

    def test_other_database_tables_cannot_falsify_coverage(self):
        self.write_dump(
            "CREATE DATABASE estate WITH TEMPLATE = template0;\n"
            "\\connect postgres\nCREATE TABLE public.unrelated (id integer);\n"
            "\\connect estate\n-- estate intentionally empty\n"
        )
        self.assertEqual(count_target_table_definitions(self.archive, "estate"), 0)

    def test_comments_and_sql_strings_are_not_table_ddl(self):
        self.write_dump(
            "\\connect estate\n-- CREATE TABLE bogus (id int);\n"
            "SELECT 'CREATE TABLE fake (id int)';\n"
        )
        self.assertEqual(count_target_table_definitions(self.archive, "estate"), 0)

    def test_corrupt_gzip_fails_closed(self):
        self.archive.write_bytes(b"not-gzip")
        run = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.archive), "estate"],
            capture_output=True, text=True
        )
        self.assertNotEqual(run.returncode, 0)

    def test_switching_away_from_target_stops_count(self):
        self.write_dump(
            "\\connect estate\nCREATE TABLE public.real (id integer);\n"
            "\\connect postgres\nCREATE TABLE public.other (id integer);\n"
        )
        self.assertEqual(count_target_table_definitions(self.archive, "estate"), 1)


if __name__ == "__main__":
    unittest.main()
