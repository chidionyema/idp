"""Offline adversarial regression tests for estate recovery dump selection."""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from verify_source_schema import count_target_table_definitions, verified_copy_provenance

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
            "CREATE DATABASE estate WITH TEMPLATE = template0;\n"
            "\\connect estate\n-- bootstrap intentionally has no user table\n"
            "CREATE DATABASE backstage WITH TEMPLATE = template0;\n"
            "\\connect backstage\n"
            "CREATE TABLE public.catalog_entities (id integer);\n"
            "CREATE TABLE public.knex_migrations (id integer);\n"
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
            "CREATE DATABASE estate WITH TEMPLATE = template0;\n"
            "\\connect estate\nCREATE TABLE public.bootstrap (id integer);\n"
            "CREATE DATABASE postgres WITH TEMPLATE = template0;\n"
            "\\connect postgres\nCREATE TABLE public.fake (id integer);\n"
            "CREATE DATABASE backstage WITH TEMPLATE = template0;\n"
            "\\connect backstage\n-- Backstage data missing\n"
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


    def _copy_receipt(self, **overrides):
        obj = "estate-db/estate-20261106T193738Z.sql.gz"
        self.archive.write_bytes(b"postgresql-backup-test-bytes")
        receipt = {
            "object": obj,
            "complete": True,
            "bytes": self.archive.stat().st_size,
            "sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            "stamp": "20261106T193738Z",
            "mode": "restored-from-surviving-dump",
            "source": "db/2026-09-08/estate-db-estate-2.sql.gz",
            "data_as_of": "2026-09-08T12:35:08.967000+00:00",
        }
        receipt.update(overrides)
        path = Path(self.tmp.name) / "latest.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        return obj, path

    def test_recopied_archive_never_launders_its_original_data_age(self):
        obj, path = self._copy_receipt()
        source, as_of = verified_copy_provenance(self.archive, path, obj)
        self.assertEqual(source, "db/2026-09-08/estate-db-estate-2.sql.gz")
        self.assertEqual(as_of, "2026-09-08T12:35:08.967000+00:00")
        run = subprocess.run(
            [sys.executable, str(SCRIPT), "--copy-provenance",
             str(self.archive), str(path), obj],
            capture_output=True, text=True
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(), [source, as_of])

    def test_tampered_copy_bytes_cannot_inherit_a_trusted_receipt(self):
        obj, path = self._copy_receipt()
        self.archive.write_bytes(b"modified-at-rest-with-same-length")
        with self.assertRaises(ValueError):
            verified_copy_provenance(self.archive, path, obj)

    def test_receipt_for_different_object_or_incomplete_copy_is_refused(self):
        obj, path = self._copy_receipt(object="estate-db/another.sql.gz")
        with self.assertRaisesRegex(ValueError, "does not attest"):
            verified_copy_provenance(self.archive, path, obj)
        obj, path = self._copy_receipt(complete=False)
        with self.assertRaisesRegex(ValueError, "does not attest"):
            verified_copy_provenance(self.archive, path, obj)

    def test_copy_with_source_time_newer_than_its_stamp_is_refused(self):
        obj, path = self._copy_receipt(data_as_of="2026-11-07T00:00:00+00:00")
        with self.assertRaisesRegex(ValueError, "newer"):
            verified_copy_provenance(self.archive, path, obj)

    def test_unattributed_regenerated_copy_is_refused(self):
        obj, path = self._copy_receipt(data_as_of=None)
        with self.assertRaisesRegex(ValueError, "no unambiguous"):
            verified_copy_provenance(self.archive, path, obj)

    def test_original_live_dump_without_as_of_uses_its_signed_copy_stamp(self):
        obj, path = self._copy_receipt(
            mode="dump-from-running-cluster", source=None, data_as_of=None
        )
        source, as_of = verified_copy_provenance(self.archive, path, obj)
        self.assertEqual(source, obj)
        self.assertEqual(as_of, "2026-11-06T19:37:38+00:00")

    def test_fetch_path_does_not_reset_recopied_data_age(self):
        source = SCRIPT.with_name("estate-db-backup.sh").read_text()
        self.assertIn('if name.startswith("db/") and label in base:', source)
        self.assertIn('elif name.startswith(label + "/"):', source)
        self.assertIn("--copy-provenance", source)
        self.assertIn('printf \'%s\\n\' "$provenance"', source)
        self.assertIn('provenance=$(printf', source)


if __name__ == "__main__":
    unittest.main()
