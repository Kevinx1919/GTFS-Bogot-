"""Contrato routes con fixtures sintéticos; nunca consulta Databricks."""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS
from gtfs_silver.routes_spark import BUSINESS_TYPES, read_and_validate, validate_header

COLUMNS = ("route_id", "agency_id", "route_short_name", "route_long_name", "route_desc",
           "route_type", "route_color", "route_text_color")
SPEC = SnapshotSpec("2025-10-28", "a" * 64, "/fixture/routes.txt", "routes")
STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def fixture(identifier="001", **changes):
    row = dict(route_id=identifier, agency_id="2", route_short_name="007", route_long_name="Ruta ejemplo",
               route_desc="Descripción", route_type="3", route_color="ff0000", route_text_color="ffffff",
               source_feed_version=SPEC.feed_version, source_sha256=SPEC.sha256,
               source_file_path=SPEC.source_path, bronze_loaded_at_utc=STAMP)
    row.update(changes)
    return row


class RoutesContractTests(unittest.TestCase):
    def test_header_requires_identity_type_and_one_name_and_blocks_unimplemented_extensions(self):
        self.assertEqual(validate_header(COLUMNS), COLUMNS)
        self.assertTrue(validate_header(tuple(c for c in COLUMNS if c != "route_long_name")))
        for columns in ((), COLUMNS[1:], COLUMNS + ("route_id",), COLUMNS + ("network_id",),
                        tuple(c for c in COLUMNS if c not in {"route_short_name", "route_long_name"})):
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                validate_header(columns)

    def test_snapshot_entity_and_source_file_must_match(self):
        with self.assertRaises(ValueError):
            SnapshotSpec(SPEC.feed_version, SPEC.sha256, "/fixture/agency.txt", "routes")
        self.assertEqual(SPEC.entity, "routes")


@unittest.skipUnless(HAS_SPARK, "Requiere Spark y Java.")
class RoutesValidationSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("routes-contract")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1")
                     .getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def frame(self, rows, columns=COLUMNS):
        from pyspark.sql.types import StringType, StructField, StructType, TimestampType
        fields = [StructField(c, StringType(), True) for c in (*columns, *TECHNICAL_FIELDS[:3])]
        fields.append(StructField("bronze_loaded_at_utc", TimestampType(), True))
        return self.spark.createDataFrame(rows, StructType(fields))

    def agencies(self, rows=None):
        values = [("2", SPEC.feed_version, SPEC.sha256, "agency_v1")] if rows is None else rows
        return self.spark.createDataFrame(values, "agency_id string, source_feed_version string, "
                                           "source_sha256 string, silver_rule_version string")

    def evaluate(self, rows, columns=COLUMNS, agencies=None):
        return read_and_validate(self.frame(rows, columns), columns, SPEC,
                                 self.agencies() if agencies is None else agencies)

    def test_casts_integer_preserves_codes_colors_and_valid_null_name(self):
        result = self.evaluate([fixture(route_long_name=None, route_type="03", route_sort_order="12")],
                               COLUMNS + ("route_sort_order",))
        self.assertTrue(result.summary["ready_for_publication"])
        frame = result.frames["candidates"]
        row = frame.first()
        self.assertEqual((row.route_id, row.route_short_name, row.route_type, row.route_sort_order),
                         ("001", "007", 3, 12))
        self.assertEqual(row.route_color, "ff0000")
        self.assertEqual(frame.schema["route_type"].dataType.simpleString(), "int")
        self.assertEqual(frame.schema["route_sort_order"].dataType.simpleString(), "int")
        self.assertIsNone(row.route_long_name)
        self.assertIsNone(row.route_url)
        self.assertEqual(result.frames["rejected"].count(), 0)

    def test_absent_field_ignores_historical_bronze_value_and_keeps_presence(self):
        columns = tuple(c for c in COLUMNS if c != "route_desc")
        result = read_and_validate(self.frame([fixture()]), columns, SPEC, self.agencies())
        row = result.frames["candidates"].first()
        self.assertIsNone(row.route_desc)
        self.assertNotIn("route_desc", row.source_columns)

    def test_bad_values_rejected_instead_of_silent_null_or_id_cleanup(self):
        cases = [
            ({"route_id": " bad "}, "ROUTE_ID_EDGE_WHITESPACE"),
            ({"route_type": "3.5"}, "ROUTE_TYPE_INVALID"),
            ({"route_type": "2147483648"}, "ROUTE_TYPE_INVALID"),
            ({"route_type": "999"}, "ROUTE_TYPE_INVALID"),
            ({"route_short_name": None, "route_long_name": "  "}, "ROUTE_NAME_MISSING"),
            ({"agency_id": "99"}, "AGENCY_ID_NOT_FOUND"),
            ({"route_color": "#ffffff"}, "ROUTE_COLOR_INVALID"),
            ({"route_text_color": "fffffg"}, "ROUTE_TEXT_COLOR_INVALID"),
            ({"route_short_name": "x\ny"}, "ROUTE_SHORT_NAME_CONTROL_CHARACTER"),
            ({"source_feed_version": "2024-01-01"}, "SOURCE_FEED_VERSION_MISMATCH"),
            ({"source_file_path": None}, "SOURCE_FILE_PATH_MISMATCH"),
            ({"bronze_loaded_at_utc": None}, "BRONZE_TIMESTAMP_INVALID"),
            ({"route_sort_order": "-1"}, "ROUTE_SORT_ORDER_INVALID"),
            ({"route_url": "not a URL"}, "ROUTE_URL_INVALID"),
        ]
        rows = [fixture(str(i), **changes) if "route_id" not in changes else fixture(**changes)
                for i, (changes, _) in enumerate(cases)]
        result = self.evaluate(rows, COLUMNS + ("route_sort_order", "route_url"))
        rejected = {row.route_id: row for row in result.frames["rejected"].collect()}
        self.assertEqual(result.summary["rejected_rows"], len(cases))
        for i, (changes, code) in enumerate(cases):
            with self.subTest(code=code):
                self.assertIn(code, rejected[changes.get("route_id", str(i))].error_codes)
        self.assertTrue(result.summary["reconciled"])
        self.assertFalse(result.summary["ready_for_publication"])

    def test_copies_conflicts_provenance_and_earliest_valid_timestamp(self):
        early = fixture(bronze_loaded_at_utc=STAMP - timedelta(days=1))
        rows = [fixture(), early, fixture(source_file_path="/wrong/routes.txt"),
                fixture("002"), fixture("002", route_short_name="Otra"), fixture("002")]
        result = self.evaluate(rows)
        self.assertEqual(result.summary["input_rows"], 6)
        self.assertEqual(result.summary["candidate_rows"], 1)
        self.assertEqual(result.summary["rejected_rows"], 4)
        self.assertEqual(result.summary["identical_copies_consolidated"], 1)
        self.assertTrue(result.summary["reconciled"])
        chosen = result.frames["candidates"].first()
        self.assertEqual(chosen.bronze_loaded_at_utc, early["bronze_loaded_at_utc"].replace(tzinfo=None))
        conflicts = result.frames["rejected"].filter("route_id = '002'").collect()
        self.assertTrue(all("ROUTE_ID_CONFLICT" in row.error_codes for row in conflicts))

    def test_missing_wrong_snapshot_duplicate_or_unversioned_agency_blocks(self):
        bad_dependencies = [[], [("2", "2026-09-29", "b" * 64, "agency_v1")],
                            [("2", SPEC.feed_version, SPEC.sha256, None)],
                            [("2", SPEC.feed_version, SPEC.sha256, "agency_v1")] * 2]
        for rows in bad_dependencies:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.evaluate([fixture()], agencies=self.agencies(rows))

    def test_more_than_one_thousand_routes_and_hash_selection_stay_in_spark(self):
        from pyspark.sql import functions as F
        base = self.frame([fixture()]).drop("route_id")
        many = self.spark.range(1045).select(F.col("id").cast("string").alias("route_id")).crossJoin(base)
        other_hash = self.frame([fixture("other", source_sha256="b" * 64)])
        result = read_and_validate(many.unionByName(other_hash), COLUMNS, SPEC, self.agencies())
        self.assertEqual(result.summary["candidate_rows"], 1045)
        self.assertEqual(result.summary["input_rows"], 1045)

    def test_optional_blanks_and_warnings_preserve_text_and_do_not_invent_defaults(self):
        result = self.evaluate([fixture(route_desc="007", route_color="", route_text_color="  ",
                                        route_long_name=" Nombre ")])
        row = result.frames["candidates"].first()
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual(result.summary["warning_rows"], 1)
        self.assertIsNone(row.route_color)
        self.assertIsNone(row.route_text_color)
        self.assertEqual(row.route_long_name, " Nombre ")
        codes = result.frames["warnings"].first().warning_codes
        self.assertIn("ROUTE_DESC_REPEATS_NAME", codes)
        self.assertIn("ROUTE_LONG_NAME_EDGE_WHITESPACE", codes)


if __name__ == "__main__":
    unittest.main()
