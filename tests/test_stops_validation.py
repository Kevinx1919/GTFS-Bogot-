"""Fixtures de stops_v1: no consultan fuentes reales ni escriben en Databricks."""

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS
from gtfs_silver.stops_spark import BUSINESS_TYPES, read_and_validate, validate_header

COLUMNS = tuple(BUSINESS_TYPES)
SPEC = SnapshotSpec("2025-10-28", "a" * 64, "/fixture/stops.txt", "stops")
STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def fixture(identifier="001", **changes):
    row = dict(stop_id=identifier, stop_code="0007", stop_name="Lugar de ejemplo",
               stop_lat="4.65", stop_lon="-74.08", location_type="0", parent_station=None,
               zone_id="0", wheelchair_boarding=None, source_feed_version=SPEC.feed_version,
               source_sha256=SPEC.sha256, source_file_path=SPEC.source_path, bronze_loaded_at_utc=STAMP)
    row.update(changes)
    return row


class StopsContractTests(unittest.TestCase):
    def test_header_handles_conditional_columns_but_requires_identity_and_known_fields(self):
        self.assertEqual(validate_header(COLUMNS), COLUMNS)
        self.assertEqual(validate_header(("stop_id",)), ("stop_id",))
        for columns in ((), ("stop_name",), COLUMNS + ("stop_id",), COLUMNS + ("stop_access",),
                        ("stop_id", ""), ("stop_id", None)):
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                validate_header(columns)


@unittest.skipUnless(HAS_SPARK, "Requiere Spark y Java.")
class StopsValidationSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("stops-contract")
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

    def evaluate(self, rows, columns=COLUMNS):
        return read_and_validate(self.frame(rows, columns), columns, SPEC)

    def test_valid_hierarchy_all_types_casts_and_unicode_name_cleanup(self):
        result = self.evaluate([
            fixture("S", location_type="1", stop_name="\u00a0Central \u2003"),
            fixture("001", parent_station="S", wheelchair_boarding="01"),
            fixture("E", location_type="2", parent_station="S"),
            fixture("N", location_type="3", parent_station="S", stop_name=None, stop_lat=None, stop_lon=None),
            fixture("B", location_type="4", parent_station="001", stop_name=None, stop_lat=None, stop_lon=None),
            fixture("002", stop_lat="4.65e0"),
        ])
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual((result.summary["candidate_rows"], result.summary["name_trimmed_rows"],
                          result.summary["stations_without_children"]), (6, 1, 0))
        rows = {r.stop_id: r for r in result.frames["candidates"].collect()}
        self.assertEqual(rows["S"].stop_name, "Central")
        self.assertEqual((rows["001"].stop_code, rows["001"].wheelchair_boarding), ("0007", 1))
        self.assertEqual(rows["002"].stop_lat, 4.65)
        self.assertIsNone(rows["N"].stop_lat)
        schema = result.frames["candidates"].schema
        self.assertEqual(schema["stop_lat"].dataType.simpleString(), "double")
        self.assertEqual(schema["location_type"].dataType.simpleString(), "int")
        self.assertEqual(len(schema.fields), 15)
        codes = result.frames["warnings"].first().warning_codes
        self.assertIn("STOP_NAME_EDGE_WHITESPACE", codes)

    def test_absent_historical_fields_and_optional_blanks_remain_null(self):
        columns = tuple(c for c in COLUMNS if c not in {"wheelchair_boarding", "location_type"})
        row = fixture(wheelchair_boarding="1", location_type="1", stop_code="\u2003", zone_id="")
        result = read_and_validate(self.frame([row]), columns, SPEC)
        value = result.frames["candidates"].first()
        self.assertIsNone(value.wheelchair_boarding)
        self.assertIsNone(value.location_type)
        self.assertIsNone(value.stop_code)
        self.assertIsNone(value.zone_id)
        self.assertNotIn("wheelchair_boarding", value.source_columns)
        self.assertTrue(result.summary["ready_for_publication"])
        missing = read_and_validate(self.frame([fixture()]), ("stop_id",), SPEC)
        self.assertIn("STOP_NAME_MISSING", missing.frames["rejected"].first().error_codes)

    def test_bad_values_are_explicit_rejections_and_never_silent_casts(self):
        cases = [
            ({"stop_id": " bad "}, "STOP_ID_EDGE_WHITESPACE"),
            ({"stop_id": "\u2003"}, "STOP_ID_MISSING"),
            ({"stop_name": "  "}, "STOP_NAME_MISSING"),
            ({"stop_name": "A\u0085B"}, "STOP_NAME_CONTROL_CHARACTER"),
            ({"stop_lat": None}, "STOP_LAT_MISSING"),
            ({"stop_lat": "abc"}, "STOP_LAT_INVALID"),
            ({"stop_lat": "NaN"}, "STOP_LAT_INVALID"),
            ({"stop_lon": "Infinity"}, "STOP_LON_INVALID"),
            ({"stop_lat": "1e309"}, "STOP_LAT_INVALID"),
            ({"stop_lat": "91"}, "STOP_LAT_INVALID"),
            ({"stop_lon": "-181"}, "STOP_LON_INVALID"),
            ({"stop_lat": " 4.65 "}, "STOP_LAT_INVALID"),
            ({"location_type": "5"}, "LOCATION_TYPE_INVALID"),
            ({"location_type": "1.0"}, "LOCATION_TYPE_INVALID"),
            ({"wheelchair_boarding": "2147483648"}, "WHEELCHAIR_BOARDING_INVALID"),
            ({"wheelchair_boarding": "3"}, "WHEELCHAIR_BOARDING_INVALID"),
            ({"parent_station": " S "}, "PARENT_STATION_EDGE_WHITESPACE"),
            ({"zone_id": " 0"}, "ZONE_ID_EDGE_WHITESPACE"),
            ({"source_feed_version": "2026-09-29"}, "SOURCE_FEED_VERSION_MISMATCH"),
            ({"source_file_path": None}, "SOURCE_FILE_PATH_MISMATCH"),
            ({"bronze_loaded_at_utc": None}, "BRONZE_TIMESTAMP_INVALID"),
        ]
        input_rows = [fixture(str(i), **changes) for i, (changes, _) in enumerate(cases)
                      if "stop_id" not in changes]
        input_rows += [fixture(**changes) for changes, _ in cases if "stop_id" in changes]
        result = self.evaluate(input_rows)
        rejected = {r.stop_id: r for r in result.frames["rejected"].collect()}
        for i, (changes, code) in enumerate(cases):
            with self.subTest(code=code):
                self.assertIn(code, rejected[changes.get("stop_id", str(i))].error_codes)
        self.assertEqual(result.summary["rejected_rows"], len(cases))
        self.assertTrue(result.summary["reconciled"])
        self.assertFalse(result.summary["ready_for_publication"])

    def test_missing_self_forbidden_and_wrong_type_parents_are_rejected(self):
        result = self.evaluate([
            fixture("S", location_type="1"), fixture("P", parent_station="S"),
            fixture("missing", parent_station="not-present"),
            fixture("self", parent_station="self"),
            fixture("forbidden", location_type="1", parent_station="S"),
            fixture("required", location_type="2"),
            fixture("wrong", parent_station="P"),
            fixture("boarding", location_type="4", parent_station="S"),
        ])
        rejected = {r.stop_id: r for r in result.frames["rejected"].collect()}
        for identifier, code in [("missing", "PARENT_STATION_NOT_FOUND"),
                                 ("self", "PARENT_STATION_SELF_REFERENCE"),
                                 ("forbidden", "PARENT_STATION_FORBIDDEN"),
                                 ("required", "PARENT_STATION_MISSING"),
                                 ("wrong", "PARENT_STATION_TYPE_INVALID"),
                                 ("boarding", "PARENT_STATION_TYPE_INVALID")]:
            self.assertIn(code, rejected[identifier].error_codes)
        self.assertEqual(result.summary["input_rows"], 8)
        self.assertEqual(result.summary["candidate_rows"], 2)

    def test_parent_copies_do_not_multiply_children_and_raw_conflicts_stay_visible(self):
        station = fixture("S", location_type="1")
        early = {**station, "bronze_loaded_at_utc": STAMP - timedelta(days=1)}
        result = self.evaluate([station, early, fixture("P", parent_station="S")])
        self.assertEqual((result.summary["input_rows"], result.summary["candidate_rows"],
                          result.summary["identical_copies_consolidated"]), (3, 2, 1))
        chosen = result.frames["candidates"].filter("stop_id = 'S'").first()
        self.assertEqual(chosen.bronze_loaded_at_utc, early["bronze_loaded_at_utc"].replace(tzinfo=None))
        conflict = self.evaluate([station, {**station, "stop_name": " Lugar de ejemplo "},
                                  fixture("P", parent_station="S")])
        self.assertEqual(conflict.summary["rejected_rows"], 3)
        self.assertEqual(conflict.summary["input_rows"], 3)
        child = conflict.frames["rejected"].filter("stop_id = 'P'").first()
        self.assertIn("PARENT_STATION_CONFLICT", child.error_codes)

    def test_parent_from_another_snapshot_or_bad_provenance_never_matches(self):
        for changes in [{"source_sha256": "b" * 64}, {"source_feed_version": "2026-09-29"},
                        {"source_file_path": "/other/stops.txt"}, {"bronze_loaded_at_utc": None}]:
            with self.subTest(changes=changes):
                result = self.evaluate([fixture("S", location_type="1", **changes),
                                        fixture("P", parent_station="S")])
                row = result.frames["rejected"].filter("stop_id = 'P'").first()
                self.assertIn("PARENT_STATION_NOT_FOUND", row.error_codes)
                self.assertFalse(result.summary["ready_for_publication"])

    def test_warning_diagnostics_do_not_block_and_count_unique_candidates(self):
        row = fixture("S", location_type="1", stop_name=" Nombre ", stop_lat="0", stop_lon="0")
        result = self.evaluate([row, row])
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual(result.summary["warning_rows"], 2)
        self.assertEqual(result.summary["name_trimmed_rows"], 1)
        self.assertEqual(result.summary["stations_without_children"], 1)
        self.assertEqual(result.summary["identical_copies_consolidated"], 1)
        self.assertIn("STATION_WITHOUT_CHILDREN", result.frames["warnings"].first().warning_codes)
        self.assertIn("COORDINATES_ZERO_PAIR", result.frames["warnings"].first().warning_codes)

    def test_schema_entity_timezone_and_empty_selection_fail_before_publication(self):
        from pyspark.sql import functions as F
        with self.assertRaises(ValueError):
            read_and_validate(self.frame([fixture()]).withColumn("stop_lat", F.col("stop_lat").cast("double")), COLUMNS, SPEC)
        with self.assertRaises(ValueError):
            read_and_validate(self.frame([fixture()]).drop("stop_id"), COLUMNS, SPEC)
        with self.assertRaises(ValueError):
            read_and_validate(self.frame([fixture()]), COLUMNS,
                              SnapshotSpec(SPEC.feed_version, SPEC.sha256, "/fixture/routes.txt", "routes"))
        with self.assertRaises(ValueError):
            self.evaluate([fixture(source_sha256="b" * 64)])
        try:
            self.spark.conf.set("spark.sql.session.timeZone", "America/Bogota")
            with self.assertRaises(ValueError):
                self.evaluate([fixture()])
        finally:
            self.spark.conf.set("spark.sql.session.timeZone", "UTC")

    def test_large_snapshot_stays_in_spark_without_agency_driver_limit(self):
        from pyspark.sql import functions as F
        base = self.frame([fixture()]).drop("stop_id")
        many = self.spark.range(1100).select(F.col("id").cast("string").alias("stop_id")).crossJoin(base)
        result = read_and_validate(many, COLUMNS, SPEC)
        self.assertEqual(result.summary["candidate_rows"], 1100)
        self.assertEqual(result.summary["rejected_rows"], 0)


if __name__ == "__main__":
    unittest.main()
