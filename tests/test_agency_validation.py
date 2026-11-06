"""Reglas de agency con fixtures sintéticos; no hay red ni escrituras Delta."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "databricks"))
from gtfs_silver.agency_validation import (
    BUSINESS_FIELDS, SnapshotSpec, read_source_header, reference_versions,
    valid_language, valid_url, validate_header, validate_snapshot,
)

COLUMNS = BUSINESS_FIELDS[:6]
SPEC = SnapshotSpec("2025-10-28", "a" * 64, "/fixture/agency.txt")
STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def fixture(identifier="001", name="Agencia de ejemplo", **changes):
    row = dict(
        agency_id=identifier, agency_name=name, agency_url="https://example.org/",
        agency_timezone="America/Bogota", agency_lang="es", agency_phone="+57 (601) 123",
        source_feed_version=SPEC.feed_version, source_sha256=SPEC.sha256,
        source_file_path=SPEC.source_path, bronze_loaded_at_utc=STAMP,
    )
    row.update(changes)
    return row


class AgencyValidationTests(unittest.TestCase):
    def evaluate(self, rows, columns=COLUMNS, spec=SPEC):
        return validate_snapshot(rows, columns, spec)

    def assert_rejected(self, changes, code):
        result = self.evaluate([fixture(**changes)])
        self.assertFalse(result.summary["ready_for_publication"])
        self.assertEqual(result.summary["rejected_rows"], 1)
        self.assertIn(code, result.rejected[0]["error_codes"])
        self.assertTrue(result.summary["reconciled"])
        return result

    def test_references_are_pinned_and_iana_values_are_not_bogota_only(self):
        self.assertEqual(reference_versions(), {"langcodes": "3.5.1", "tzdata": "2026.6"})
        result = self.evaluate([fixture(agency_timezone="Europe/Madrid", agency_lang="es-ES")])
        self.assertTrue(result.summary["ready_for_publication"])

    def test_valid_row_preserves_id_name_phone_and_input(self):
        original = fixture(name="NOMBRE PUBLICADO", agency_phone="503-238-RIDE")
        before = deepcopy(original)
        result = self.evaluate([original])
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual(result.candidates[0]["agency_id"], "001")
        self.assertEqual(result.candidates[0]["agency_name"], "NOMBRE PUBLICADO")
        self.assertEqual(result.candidates[0]["agency_phone"], "503-238-RIDE")
        self.assertEqual(original, before)
        self.assertEqual(result.candidates[0]["source_columns"], list(COLUMNS))

    def test_missing_required_content_blocks_publication(self):
        for field in ("agency_id", "agency_name", "agency_url", "agency_timezone"):
            for value in (None, "", "   "):
                with self.subTest(field=field, value=value):
                    self.assert_rejected({field: value}, f"{field.upper()}_MISSING")

    def test_absent_optional_ignores_historical_values_and_preserves_presence(self):
        result = self.evaluate([fixture(agency_fare_url="https://another-version.example/")])
        self.assertIsNone(result.candidates[0]["agency_fare_url"])
        self.assertIsNone(result.candidates[0]["agency_email"])
        self.assertNotIn("agency_fare_url", result.candidates[0]["source_columns"])

    def test_optional_published_absences_become_null(self):
        for value in (None, "", "   "):
            with self.subTest(value=value):
                result = self.evaluate([fixture(agency_fare_url=value)], (*COLUMNS, "agency_fare_url"))
                self.assertTrue(result.summary["ready_for_publication"])
                self.assertIsNone(result.candidates[0]["agency_fare_url"])
                self.assertIn("agency_fare_url", result.candidates[0]["source_columns"])

    def test_url_structure_accepts_http_and_rejects_malformed_values(self):
        for value in ("http://example.org", "HTTPS://example.org/path?q=1"):
            with self.subTest(value=value):
                self.assertTrue(valid_url(value))
        for value in ("/relative", "example.org", "ftp://example.org", "https://",
                      "https://exa mple.org", "https://example.org:99999", "http://[bad]"):
            with self.subTest(value=value):
                self.assertFalse(valid_url(value))

    def test_invalid_optional_url_keeps_original_and_blocks(self):
        result = self.evaluate([fixture(agency_fare_url="relative/path")], (*COLUMNS, "agency_fare_url"))
        self.assertFalse(result.summary["ready_for_publication"])
        self.assertIn("AGENCY_FARE_URL_FORMAT_INVALID", result.rejected[0]["error_codes"])
        self.assertEqual(json.loads(result.rejected[0]["original_row_json"])["agency_fare_url"], "relative/path")

    def test_unknown_and_inconsistent_timezones_block(self):
        self.assert_rejected({"agency_timezone": "Mars/Unknown"}, "AGENCY_TIMEZONE_UNKNOWN")
        result = self.evaluate([fixture(), fixture("002", agency_timezone="Europe/Madrid")])
        self.assertEqual(result.summary["rejected_rows"], 2)
        self.assertTrue(all("SNAPSHOT_TIMEZONE_INCONSISTENT" in row["error_codes"] for row in result.rejected))

    def test_language_uses_registered_tags_without_accepting_underscores(self):
        for value in ("es", "es-CO", "en-US", "zh-Hant-TW"):
            with self.subTest(value=value):
                self.assertTrue(valid_language(value))
        for value in ("xx", "es_CO", "not a language", "es-"):
            with self.subTest(value=value):
                self.assertFalse(valid_language(value))
                self.assert_rejected({"agency_lang": value}, "AGENCY_LANG_INVALID")

    def test_optional_email_basic_structure_only_when_published(self):
        columns = (*COLUMNS, "agency_email")
        result = self.evaluate([fixture(agency_email="contact@example.org")], columns)
        self.assertTrue(result.summary["ready_for_publication"])
        bad = self.evaluate([fixture(agency_email="missing-at")], columns)
        self.assertIn("AGENCY_EMAIL_FORMAT_INVALID", bad.rejected[0]["error_codes"])

    def test_id_spaces_are_not_removed_and_name_spaces_are_warned(self):
        result = self.assert_rejected({"identifier": " 001 "}, "AGENCY_ID_EDGE_WHITESPACE")
        self.assertEqual(json.loads(result.rejected[0]["original_row_json"])["agency_id"], " 001 ")
        result = self.evaluate([fixture(name=" Agencia ")])
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual(result.candidates[0]["agency_name"], " Agencia ")
        self.assertEqual(result.summary["warning_rows"], 1)

    def test_control_characters_are_errors_even_in_blank_optional_values(self):
        self.assert_rejected({"agency_phone": "\t"}, "AGENCY_PHONE_CONTROL_CHARACTER")
        self.assert_rejected({"agency_name": "A\nB"}, "AGENCY_NAME_CONTROL_CHARACTER")

    def test_identical_copies_consolidate_with_earliest_bronze_timestamp(self):
        first = fixture(bronze_loaded_at_utc=STAMP + timedelta(hours=1))
        second = fixture(bronze_loaded_at_utc=STAMP)
        for rows in ([first, second], [second, first]):
            result = self.evaluate(rows)
            self.assertEqual(result.summary["candidate_rows"], 1)
            self.assertEqual(result.summary["identical_copies_consolidated"], 1)
            self.assertEqual(result.candidates[0]["bronze_loaded_at_utc"], STAMP)
            self.assertTrue(result.summary["reconciled"])

    def test_conflict_rejects_all_rows_without_double_counting_copies(self):
        result = self.evaluate([fixture(name="A"), fixture(name="A"), fixture(name="B"), fixture("002")])
        self.assertEqual(result.summary["candidate_rows"], 1)
        self.assertEqual(result.summary["rejected_rows"], 3)
        self.assertEqual(result.summary["identical_copies_consolidated"], 0)
        self.assertTrue(result.summary["reconciled"])
        self.assertFalse(result.summary["ready_for_publication"])
        self.assertTrue(all("AGENCY_ID_CONFLICT" in row["error_codes"] for row in result.rejected))

    def test_multiple_errors_count_the_row_once(self):
        result = self.evaluate([fixture(identifier=None, agency_url="/relative")])
        self.assertEqual(result.summary["rejected_rows"], 1)
        self.assertGreaterEqual(len(result.rejected[0]["error_codes"]), 2)
        self.assertTrue(result.summary["reconciled"])

    def test_distinct_ids_with_shared_attributes_are_not_duplicates(self):
        result = self.evaluate([fixture("001"), fixture("002")])
        self.assertEqual(result.summary["candidate_rows"], 2)
        self.assertEqual(result.summary["identical_copies_consolidated"], 0)

    def test_bad_provenance_blocks_and_never_relabels_original(self):
        for field in ("source_feed_version", "source_sha256", "source_file_path"):
            with self.subTest(field=field):
                result = self.assert_rejected({field: "wrong"}, f"{field.upper()}_MISMATCH")
                self.assertEqual(json.loads(result.rejected[0]["original_row_json"])[field], "wrong")
        self.assert_rejected({"bronze_loaded_at_utc": None}, "BRONZE_TIMESTAMP_INVALID")

    def test_snapshots_with_same_id_keep_distinct_names(self):
        other_spec = SnapshotSpec("2026-09-29", "b" * 64, "/fixture-2026/agency.txt")
        old = self.evaluate([fixture("2", name="Marca anterior")])
        new = self.evaluate([fixture(
            "2", name="Marca nueva", source_feed_version=other_spec.feed_version,
            source_sha256=other_spec.sha256, source_file_path=other_spec.source_path,
        )], spec=other_spec)
        self.assertEqual(old.candidates[0]["agency_name"], "Marca anterior")
        self.assertEqual(new.candidates[0]["agency_name"], "Marca nueva")
        self.assertNotEqual(old.candidates[0]["source_sha256"], new.candidates[0]["source_sha256"])

    def test_empty_or_excessive_input_is_not_approved(self):
        with self.assertRaises(ValueError):
            self.evaluate([])
        with self.assertRaises(ValueError):
            validate_snapshot([fixture(), fixture("002")], COLUMNS, SPEC, max_rows=1)

    def test_schema_changes_block_before_field_validation(self):
        for columns in ((), COLUMNS[1:], (*COLUMNS, "agency_id"), (*COLUMNS, "new_field")):
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                validate_header(columns)

    def test_non_string_business_value_is_rejected(self):
        self.assert_rejected({"agency_phone": 1234}, "AGENCY_PHONE_TYPE_INVALID")

    def test_header_supports_bom(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary, "agency.txt")
            path.write_text(",".join(COLUMNS) + "\n", encoding="utf-8-sig")
            self.assertEqual(read_source_header(str(path)), COLUMNS)

    def test_snapshot_parameters_are_explicit_and_valid(self):
        for version, content_hash in (("2025-02-30", "a" * 64), ("20251028", "a" * 64),
                                      ("2025-10-28", "g" * 64)):
            with self.subTest(version=version, content_hash=content_hash), self.assertRaises(ValueError):
                SnapshotSpec(version, content_hash, "/fixture/agency.txt")


@unittest.skipUnless(HAS_SPARK, "Requiere PySpark y Java para comprobar el adaptador nativo.")
class AgencyValidationSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("agency-validation")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def frame(self, rows):
        from pyspark.sql.types import StringType, StructField, StructType, TimestampType
        columns = list(COLUMNS) + ["source_feed_version", "source_sha256", "source_file_path"]
        schema = StructType([StructField(name, StringType(), True) for name in columns]
                            + [StructField("bronze_loaded_at_utc", TimestampType(), True)])
        return self.spark.createDataFrame(rows, schema)

    def test_adapter_filters_hash_but_detects_wrong_version(self):
        from gtfs_silver.agency_spark import read_and_validate
        rows = [fixture(), fixture("002", source_feed_version="2024-01-01"),
                fixture("003", source_sha256="b" * 64)]
        result = read_and_validate(self.frame(rows), COLUMNS, SPEC)
        self.assertEqual(result.summary["input_rows"], 2)
        self.assertEqual(result.summary["rejected_rows"], 1)

    def test_empty_rejection_and_optional_columns_have_explicit_schemas(self):
        from gtfs_silver.agency_spark import read_and_validate, result_frames
        result = read_and_validate(self.frame([fixture()]), COLUMNS, SPEC)
        frames = result_frames(self.spark, result)
        self.assertEqual(frames["rejected"].count(), 0)
        self.assertEqual(frames["candidates"].schema["agency_fare_url"].dataType.simpleString(), "string")
        self.assertIsNone(frames["candidates"].first().agency_fare_url)

    def test_adapter_fails_when_bound_is_exceeded(self):
        from gtfs_silver.agency_spark import read_and_validate
        with self.assertRaises(ValueError):
            read_and_validate(self.frame([fixture(), fixture("002")]), COLUMNS, SPEC, max_rows=1)


if __name__ == "__main__":
    unittest.main()
