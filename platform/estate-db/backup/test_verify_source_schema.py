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


    def test_empty_estate_bootstrap_is_not_data_loss_when_backstage_has_tables(self):
        """The real 2026-10-26 bootstrap DB had ZERO tables by design."""
        self.write_dump(
            "CREATE DATABASE estate WITH TEMPLATE = template0;\\n"
            "\\connect estate\\n-- bootstrap intentionally has no user table\\n"
            "CREATE DATABASE backstage WITH TEMPLATE = template0;\\n"
            "\\connect backstage\\n"
            "CREATE TABLE public.catalog_entities (id integer);\\n"
            "CREATE TABLE public.knex_migrations (id integer);\\n"
        )
        self.assertEqual(count_target_table_definitions(self.archive, "estate"), 0)
        self.assertEqual(count_target_table_definitions(self.archive, "backstage"), 2)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.archive), "backstage"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TARGET_TABLE_DDL_COUNT=2", result.stdout)

    def test_bootstrap_and_unrelated_tables_cannot_fake_backstage_recovery(self):
        self.write_dump(
            "CREATE DATABASE estate WITH TEMPLATE = template0;\\n"
            "\\connect estate\\nCREATE TABLE public.bootstrap (id integer);\\n"
            "CREATE DATABASE postgres WITH TEMPLATE = template0;\\n"
            "\\connect postgres\\nCREATE TABLE public.fake (id integer);\\n"
            "CREATE DATABASE backstage WITH TEMPLATE = template0;\\n"
            "\\connect backstage\\n-- Backstage data missing\\n"
        )
        self.assertEqual(count_target_table_definitions(self.archive, "backstage"), 0)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.archive), "backstage"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("no target-scoped", result.stderr)

    def test_backup_validates_real_application_database_not_empty_bootstrap(self):
        script = SCRIPT.with_name("estate-db-backup.sh").read_text()
        self.assertIn('PROOF_DB="backstage"', script)
        self.assertIn('"$file" "$PROOF_DB"', script)
        self.assertIn('psql -d "$PROOF_DB"', script)
        self.assertNotIn('psql -d estate -Atc', script)
        self.assertIn('CREATE DATABASE ${ESTATE_DB_NAME}', script)
        self.assertIn('the application proof database restored with no tables', script)


if __name__ == "__main__":
    unittest.main()
