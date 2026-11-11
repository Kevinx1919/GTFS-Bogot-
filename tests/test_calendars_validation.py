"""Fixtures de calendarios: fechas fuente, modos y clave compuesta sin llamadas de red."""
from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver.calendars_spark import BUSINESS_TYPES, WEEKDAYS, calendar_source_present, read_and_validate, read_source_header, validate_header
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS

STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def selected(entity, version="2025-10-28", sha="a" * 64):
    return SnapshotSpec(version, sha, f"/fixture/{version}/{sha}/{entity}.txt", entity)


def fixture(spec, identifier="001", **changes):
    row = dict(service_id=identifier, source_feed_version=spec.feed_version, source_sha256=spec.sha256,
               source_file_path=spec.source_path, bronze_loaded_at_utc=STAMP)
    if spec.entity == "calendar":
        row.update({day: "1" if day not in {"saturday", "sunday"} else "0" for day in WEEKDAYS})
        row.update(start_date="20000101", end_date="20990101")
    else:
        row.update(date="20230101", exception_type="1")
    row.update(changes)
    return row


def frame(spark, spec, rows):
    from pyspark.sql.types import StringType, StructField, StructType, TimestampType
    fields = [StructField(c, StringType(), True) for c in (*BUSINESS_TYPES[spec.entity], *TECHNICAL_FIELDS[:3])]
    fields.append(StructField("bronze_loaded_at_utc", TimestampType(), True))
    return spark.createDataFrame(rows, StructType(fields))


class CalendarContractTests(unittest.TestCase):
    def test_headers_require_all_known_fields_and_reject_duplicates_or_extensions(self):
        for entity, types in BUSINESS_TYPES.items():
            columns = tuple(types)
            self.assertEqual(validate_header(columns, entity), columns)
            for invalid in ((), columns[:-1], columns + ("extra",), columns + (columns[0],), (None,)):
                with self.subTest(entity=entity, invalid=invalid), self.assertRaises(ValueError):
                    validate_header(invalid, entity)
        with self.assertRaises(ValueError):
            validate_header(("service_id",), "trips")

    def test_bom_headers_and_optional_calendar_presence_use_temp_files(self):
        with TemporaryDirectory(prefix="gtfs-calendar-headers-") as directory:
            path = Path(directory) / "calendar_dates.txt"
            path.write_text("\ufeffservice_id,date,exception_type\n", encoding="utf-8")
            self.assertEqual(read_source_header(str(path)), tuple(BUSINESS_TYPES["calendar_dates"]))
            self.assertFalse(calendar_source_present(str(path)))
            (Path(directory) / "calendar.txt").write_text(",".join(BUSINESS_TYPES["calendar"]) + "\n", encoding="utf-8")
            self.assertTrue(calendar_source_present(str(path)))


@unittest.skipUnless(HAS_SPARK, "Requiere Spark y Java.")
class CalendarValidationSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("calendar-contracts")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def evaluate(self, spec, rows, **options):
        return read_and_validate(frame(self.spark, spec, rows), tuple(BUSINESS_TYPES[spec.entity]), spec, **options)

    def dependency(self, **changes):
        spec = selected("calendar")
        return self.evaluate(spec, [fixture(spec, **changes)]).frames["candidates"]

    def test_calendar_casts_preserves_long_interval_and_identical_patterns_with_other_ids(self):
        spec = selected("calendar")
        result = self.evaluate(spec, [fixture(spec), fixture(spec, "002"),
                                     fixture(spec, "003", **{d: "0" for d in WEEKDAYS})])
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual(result.summary["candidate_rows"], 3)
        self.assertEqual(result.summary["interval_over_ten_years_rows"], 3)
        self.assertEqual(result.summary["no_weekly_service_rows"], 1)
        rows = result.frames["candidates"].collect()
        self.assertEqual(rows[0].start_date, date(2000, 1, 1))
        self.assertEqual(rows[0].end_date, date(2099, 1, 1))
        self.assertEqual(result.frames["candidates"].schema["monday"].dataType.simpleString(), "int")
        self.assertEqual(result.frames["candidates"].schema["start_date"].dataType.simpleString(), "date")
        self.assertEqual({r.service_id for r in rows}, {"001", "002", "003"})
        self.assertEqual(len(result.frames["candidates"].columns), 16)

    def test_exception_composite_key_keeps_multiple_dates_and_copies_preserve_oldest_timestamp(self):
        spec = selected("calendar_dates")
        first = fixture(spec, "a|b")
        result = self.evaluate(spec, [first, {**first, "bronze_loaded_at_utc": STAMP + timedelta(days=1)},
                                     fixture(spec, "a|b", date="20230102", exception_type="2")])
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual((result.summary["candidate_rows"], result.summary["identical_copies_consolidated"]), (2, 1))
        self.assertEqual(result.summary["different_snapshot_year_rows"], 2)
        self.assertEqual(result.summary["warning_rows"], 3)
        self.assertEqual(result.summary["calendar_mode"], "dates_only")
        rows = result.frames["candidates"].orderBy("date").collect()
        self.assertEqual([r.date for r in rows], [date(2023, 1, 1), date(2023, 1, 2)])
        self.assertEqual(rows[0].bronze_loaded_at_utc.replace(tzinfo=timezone.utc), STAMP)
        self.assertEqual(rows[1].exception_type, 2)
        self.assertEqual(result.frames["warnings"].columns, ["service_id", "date", "warning_codes"])

    def test_raw_conflicts_reject_all_variants_without_rejecting_other_dates(self):
        spec = selected("calendar_dates")
        result = self.evaluate(spec, [fixture(spec), fixture(spec, exception_type="01"),
                                     fixture(spec, date="20230102")])
        self.assertEqual(result.summary["candidate_rows"], 1)
        self.assertEqual(result.summary["rejected_rows"], 2)
        self.assertFalse(result.summary["ready_for_publication"])
        self.assertTrue(all("SERVICE_KEY_CONFLICT" in r.error_codes for r in result.frames["rejected"].collect()))

    def test_invalid_calendar_values_and_provenance_are_explicit_rejections(self):
        spec = selected("calendar")
        cases = [({"start_date": "20250230"}, "START_DATE_INVALID"),
                 ({"start_date": "2025-01-01"}, "START_DATE_INVALID"),
                 ({"start_date": "00000101"}, "START_DATE_INVALID"),
                 ({"start_date": None}, "START_DATE_MISSING"),
                 ({"start_date": "20260101", "end_date": "20250101"}, "CALENDAR_INTERVAL_REVERSED"),
                 ({"monday": "2"}, "MONDAY_INVALID"), ({"monday": " 1 "}, "MONDAY_INVALID"),
                 ({"monday": "1.0"}, "MONDAY_INVALID"), ({"monday": "2147483648"}, "MONDAY_INVALID"),
                 ({"service_id": " id "}, "SERVICE_ID_EDGE_WHITESPACE"),
                 ({"service_id": ""}, "SERVICE_ID_MISSING"),
                 ({"service_id": "x\u0085y"}, "SERVICE_ID_CONTROL_CHARACTER"),
                 ({"source_feed_version": "2026-09-29"}, "SOURCE_FEED_VERSION_MISMATCH"),
                 ({"source_file_path": None}, "SOURCE_FILE_PATH_MISMATCH"),
                 ({"bronze_loaded_at_utc": None}, "BRONZE_TIMESTAMP_INVALID")]
        rows = [fixture(spec, str(i), **changes) for i,(changes,_) in enumerate(cases)]
        result = self.evaluate(spec, rows)
        rejected = {r.service_id: r for r in result.frames["rejected"].collect()}
        for i,(changes,code) in enumerate(cases):
            self.assertIn(code, rejected[changes.get("service_id",str(i))].error_codes)
        self.assertEqual(result.summary["rejected_rows"], len(cases))
        self.assertTrue(result.summary["reconciled"])

    def test_invalid_exception_dates_codes_and_missing_values_never_become_silent_nulls(self):
        spec = selected("calendar_dates")
        cases = [({"date": "20250229"}, "DATE_INVALID"), ({"date": "20251301"}, "DATE_INVALID"),
                 ({"date": "2025-01-01"}, "DATE_INVALID"), ({"date": "2025011"}, "DATE_INVALID"),
                 ({"date": "\u2003"}, "DATE_MISSING"), ({"exception_type": None}, "EXCEPTION_TYPE_MISSING"),
                 ({"exception_type": "3"}, "EXCEPTION_TYPE_INVALID"), ({"service_id": None}, "SERVICE_ID_MISSING")]
        result = self.evaluate(spec, [fixture(spec,str(i),**changes) for i,(changes,_) in enumerate(cases)])
        rejected = {r.service_id: r for r in result.frames["rejected"].collect()}
        for i,(changes,code) in enumerate(cases):
            self.assertIn(code,rejected[changes.get("service_id",str(i))].error_codes)
        self.assertEqual(result.summary["candidate_rows"],0)
        self.assertEqual(result.summary["rejected_rows"],len(cases))

    def test_weekly_dependency_matches_snapshot_and_outside_dates_only_warn(self):
        spec = selected("calendar_dates")
        dependency = self.dependency(start_date="20250101",end_date="20251231")
        result = self.evaluate(spec, [fixture(spec,date="20250101"),fixture(spec,date="20260101")],
                               calendar_df=dependency,calendar_published=True)
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertEqual(result.summary["outside_calendar_interval_rows"],1)
        self.assertEqual(result.summary["calendar_mode"],"weekly_and_exceptions")
        missing = self.evaluate(spec,[fixture(spec,"not-in-calendar")],calendar_df=dependency,calendar_published=True)
        self.assertIn("CALENDAR_SERVICE_ID_NOT_FOUND",missing.frames["rejected"].first().error_codes)

    def test_missing_duplicate_wrong_snapshot_or_bad_calendar_dependency_blocks(self):
        from pyspark.sql import functions as F
        spec = selected("calendar_dates");dependency=self.dependency()
        for invalid in [dependency.unionByName(dependency),
                        dependency.withColumn("source_sha256",F.lit("b"*64)),
                        dependency.withColumn("silver_rule_version",F.lit("other")),
                        dependency.withColumn("service_id",F.lit("")),
                        dependency.withColumn("start_date",F.lit(None).cast("date")),
                        dependency.withColumn("start_date",F.col("start_date").cast("string"))]:
            with self.assertRaises(ValueError):
                self.evaluate(spec,[fixture(spec)],calendar_df=invalid,calendar_published=True)
        with self.assertRaises(ValueError):self.evaluate(spec,[fixture(spec)],calendar_published=True)
        with self.assertRaises(ValueError):self.evaluate(spec,[fixture(spec)],calendar_df=dependency)

    def test_schema_timezone_and_empty_hash_guards_remain_active(self):
        from pyspark.sql import functions as F
        spec = selected("calendar")
        with self.assertRaises(ValueError):self.evaluate(spec,[])
        with self.assertRaises(ValueError):
            read_and_validate(frame(self.spark,spec,[fixture(spec)]).withColumn("monday",F.lit(1)),tuple(BUSINESS_TYPES[spec.entity]),spec)
        self.spark.conf.set("spark.sql.session.timeZone","America/Bogota")
        try:
            with self.assertRaises(ValueError):self.evaluate(spec,[fixture(spec)])
        finally:self.spark.conf.set("spark.sql.session.timeZone","UTC")
        with self.assertRaises(ValueError):self.evaluate(spec,[fixture(spec)],calendar_df=self.dependency())


if __name__ == "__main__":
    unittest.main()
