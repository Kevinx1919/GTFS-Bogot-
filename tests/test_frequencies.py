"""Frecuencias: horas extendidas, ventanas, referencias y contrato del Job."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch, sentinel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver import pipeline
from gtfs_silver.frequencies_spark import BUSINESS_TYPES, read_and_validate, read_source_header, validate_header
from gtfs_silver.job_config import build_job
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS

COLUMNS = ("trip_id", "start_time", "end_time", "headway_secs")
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def frequency_spec(version="2025-10-28", content_hash="a" * 64, path=None):
    return SnapshotSpec(version, content_hash, path or f"/fixture/{version}/{content_hash}/frequencies.txt", "frequencies")


def fixture(selected, **changes):
    row = dict(trip_id="T1", start_time="04:30:00", end_time="05:30:00", headway_secs="60", exact_times=None,
               source_feed_version=selected.feed_version, source_sha256=selected.sha256, source_file_path=selected.source_path,
               bronze_loaded_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
    row.update(changes)
    return row


def frequency_frame(spark, selected, rows=None, columns=COLUMNS):
    from pyspark.sql.types import StringType, StructField, StructType, TimestampType
    names = (*columns, *TECHNICAL_FIELDS)
    schema = StructType([StructField(n, TimestampType() if n == "bronze_loaded_at_utc" else StringType()) for n in names])
    return spark.createDataFrame([{n: r[n] for n in names} for r in (rows if rows is not None else [fixture(selected)])], schema)


def trips_frame(spark, selected, ids=("T1", "T2", "T3")):
    return spark.createDataFrame([(i, selected.feed_version, selected.sha256, "trips_v1") for i in ids],
                                 "trip_id string,source_feed_version string,source_sha256 string,silver_rule_version string")


class FrequenciesContractTests(unittest.TestCase):
    def test_header_requires_four_fields_allows_exact_times_and_reads_bom(self):
        self.assertEqual(validate_header(COLUMNS), COLUMNS)
        self.assertEqual(validate_header((*COLUMNS, "exact_times")), (*COLUMNS, "exact_times"))
        for fields in [(), COLUMNS[1:], (*COLUMNS, "extra"), (*COLUMNS, "trip_id"), (None,)]:
            with self.subTest(fields=fields), self.assertRaises(ValueError): validate_header(fields)
        with TemporaryDirectory(prefix="gtfs-frequencies-header-") as folder:
            path = Path(folder) / "frequencies.txt"
            path.write_text(",".join(COLUMNS) + "\n", encoding="utf-8-sig")
            self.assertEqual(read_source_header(str(path)), COLUMNS)

    def test_dispatch_pins_bronze_and_only_trips_with_plain_identifiers(self):
        spark = MagicMock(); spark.catalog.tableExists.return_value = True
        result = SimpleNamespace(reference_versions={})
        with patch.object(pipeline.frequencies_spark, "read_source_header", return_value=COLUMNS), \
             patch.object(pipeline, "_versioned_table", side_effect=[(sentinel.bronze, 3), (sentinel.trips, 7)]) as reader, \
             patch.object(pipeline.frequencies_spark, "read_and_validate", return_value=result) as validator, \
             patch.object(pipeline, "publish_snapshot", return_value={"persisted": False}) as publish:
            pipeline.run_entity(spark, catalog="workspace", schema="fixture", staging_volume="staging", entity="frequencies",
                                feed_version="2025-10-28", snapshot_sha256="a"*64, mode="validate")
        self.assertEqual([c.args[1] for c in reader.call_args_list],
                         ["workspace.fixture.bronze_gtfs_frequencies", "workspace.fixture.silver_gtfs_trips"])
        self.assertTrue(all(c.kwargs["with_version"] for c in reader.call_args_list))
        self.assertIs(validator.call_args.args[3], sentinel.trips)
        self.assertEqual(result.reference_versions["bronze_delta_version"], "3")
        self.assertEqual(result.reference_versions["trips_delta_version"], "7")
        self.assertEqual(publish.call_args.args[3].entity, "frequencies")

    def test_missing_trips_blocks_before_validation_or_publication(self):
        spark = MagicMock(); spark.catalog.tableExists.side_effect = [True, False]
        with patch.object(pipeline.frequencies_spark, "read_source_header", return_value=COLUMNS), \
             patch.object(pipeline, "_versioned_table", return_value=(sentinel.bronze, 0)), \
             patch.object(pipeline.frequencies_spark, "read_and_validate") as validator:
            with self.assertRaisesRegex(ValueError, "Publica trips"):
                pipeline.run_entity(spark, catalog="workspace", schema="fixture", staging_volume="staging", entity="frequencies",
                                    feed_version="2025-10-28", snapshot_sha256="a"*64)
        validator.assert_not_called()

    def test_job_adds_ninth_task_for_two_snapshots_without_horizon(self):
        job = build_job("/Workspace/Shared/example-project")
        self.assertEqual(len(job["tasks"]), 10)
        task = job["tasks"][8]
        self.assertEqual(task["task_key"], "publish_frequencies")
        self.assertEqual(task["depends_on"], [{"task_key": "publish_trips"}])
        self.assertEqual(task["for_each_task"]["inputs"], "{{job.parameters.frequencies_work_items}}")
        self.assertEqual(task["for_each_task"]["concurrency"], 1)
        params = {p["name"]: p["default"] for p in job["parameters"]}
        items = json.loads(params["frequencies_work_items"])
        self.assertEqual([i["entity"] for i in items], ["frequencies", "frequencies"])
        self.assertEqual([i["feed_version"] for i in items], ["2025-10-28", "2026-09-29"])
        self.assertNotIn("window_start", task["for_each_task"]["task"]["notebook_task"]["base_parameters"])


@unittest.skipUnless(HAS_SPARK, "Requiere Spark y Java.")
class FrequenciesSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("frequency-rules")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC"); cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls): cls.spark.stop()

    def validate(self, rows, columns=COLUMNS, parent=None):
        selected = frequency_spec()
        return read_and_validate(frequency_frame(self.spark, selected, rows, columns), columns, selected,
                                 trips_frame(self.spark, selected) if parent is None else parent)

    def test_copies_contiguous_windows_and_extended_hours_preserve_source_and_types(self):
        s = frequency_spec()
        rows = [fixture(s), fixture(s), fixture(s, start_time="05:30:00", end_time="25:10:00", headway_secs="16")]
        r = self.validate(rows)
        self.assertEqual((r.summary["input_rows"], r.summary["candidate_rows"], r.summary["identical_copies_consolidated"], r.summary["rejected_rows"]), (3, 2, 1, 0))
        output = r.frames["candidates"].orderBy("start_time_seconds").collect()
        self.assertEqual(output[1].end_time_seconds, 90600)
        self.assertEqual(output[1].end_time, "25:10:00")
        self.assertTrue(all(x.exact_times is None and x.exact_times_effective == 0 and "exact_times" not in x.source_columns for x in output))
        types = {f.name: f.dataType.simpleString() for f in r.frames["candidates"].schema.fields}
        self.assertEqual((types["headway_secs"], types["exact_times"], types["start_time_seconds"], types["end_time_seconds"]), ("int", "int", "bigint", "bigint"))
        self.assertTrue(r.summary["reconciled"])

    def test_exact_times_defaults_do_not_masquerade_as_source_and_exact_boundary_is_checked(self):
        s = frequency_spec(); cols = (*COLUMNS, "exact_times")
        rows = [fixture(s, exact_times=""), fixture(s, trip_id="T2", exact_times="0"),
                fixture(s, trip_id="T3", exact_times="1", end_time="05:30:01")]
        r = self.validate(rows, cols)
        self.assertEqual(r.summary["candidate_rows"], 3)
        result = {x.trip_id: x for x in r.frames["candidates"].collect()}
        self.assertIsNone(result["T1"].exact_times)
        self.assertEqual((result["T2"].exact_times, result["T3"].exact_times_effective), (0, 1))
        self.assertIn("exact_times", result["T1"].source_columns)
        boundary = self.validate([fixture(s, exact_times="1")], cols)
        self.assertIn("EXACT_TIMES_END_BOUNDARY_INVALID", boundary.frames["rejected"].first().error_codes)
        mixed = self.validate([fixture(s, exact_times="0"), fixture(s, start_time="05:30:00", end_time="06:30:01", exact_times="1")], cols)
        self.assertEqual(mixed.summary["rejected_rows"], 2)
        self.assertTrue(all("EXACT_TIMES_INCONSISTENT" in x.error_codes for x in mixed.frames["rejected"].collect()))

    def test_invalid_fields_and_provenance_retain_originals_without_ansi_errors(self):
        s = frequency_spec(); cols = (*COLUMNS, "exact_times")
        changes = [dict(start_time="04:60:00"), dict(start_time="-1:00:00"), dict(end_time="999999999999999999999999999999999999999:00:00"),
                   dict(start_time="2562047788015216:00:00"), dict(end_time="04:30:00"), dict(end_time="01:00:00"),
                   dict(headway_secs="0"), dict(headway_secs="-1"), dict(headway_secs="1.0"), dict(headway_secs="2147483648"),
                   dict(headway_secs=None), dict(trip_id=""), dict(trip_id=" T1"), dict(trip_id="T\u200b1"),
                   dict(start_time="4:30:0"), dict(exact_times="2"), dict(exact_times="false"),
                   dict(source_feed_version="2026-09-29"), dict(source_file_path="/wrong/frequencies.txt"), dict(bronze_loaded_at_utc=None)]
        r = self.validate([fixture(s, **change) for change in changes], cols)
        self.assertEqual(r.summary["rejected_rows"], len(changes))
        self.assertFalse(r.summary["ready_for_publication"])
        rejected = r.frames["rejected"].collect()
        self.assertTrue(all(x.original_row_json and x.error_codes for x in rejected))
        codes = {code for x in rejected for code in x.error_codes}
        self.assertTrue({"START_TIME_INVALID", "END_TIME_INVALID", "HEADWAY_SECS_INVALID", "WINDOW_NOT_INCREASING", "EXACT_TIMES_INVALID", "SOURCE_FILE_PATH_MISMATCH"} <= codes)

    def test_conflicts_and_canonical_time_collisions_reject_every_copy(self):
        s = frequency_spec()
        for rows, code in [([fixture(s), fixture(s), fixture(s, headway_secs="16")], "FREQUENCY_KEY_CONFLICT"),
                           ([fixture(s), fixture(s), fixture(s, start_time="4:30:00")], "FREQUENCY_CANONICAL_KEY_CONFLICT")]:
            r = self.validate(rows)
            self.assertEqual((r.summary["rejected_rows"], r.summary["identical_copies_consolidated"]), (3, 0))
            self.assertTrue(all(code in x.error_codes for x in r.frames["rejected"].collect()))

    def test_nested_overlaps_mark_both_ends_and_all_copies_but_keep_touching_window(self):
        s = frequency_spec()
        outer = fixture(s, start_time="00:00:00", end_time="00:10:00")
        rows = [outer, dict(outer), fixture(s, start_time="00:01:00", end_time="00:02:00"),
                fixture(s, start_time="00:03:00", end_time="00:04:00"),
                fixture(s, start_time="00:10:00", end_time="00:11:00")]
        r = self.validate(rows)
        self.assertEqual((r.summary["candidate_rows"], r.summary["rejected_rows"]), (1, 4))
        self.assertTrue(all("FREQUENCY_WINDOWS_OVERLAP" in x.error_codes for x in r.frames["rejected"].collect()))
        self.assertEqual(r.frames["candidates"].first().start_time_seconds, 600)

    def test_different_trips_remain_independent_and_long_headway_warns_without_changing_units(self):
        s = frequency_spec()
        r = self.validate([fixture(s), fixture(s, trip_id="T2", end_time="04:30:10", headway_secs="60")])
        self.assertEqual((r.summary["candidate_rows"], r.summary["rejected_rows"], r.summary["warning_rows"]), (2, 0, 1))
        self.assertTrue(r.summary["ready_for_publication"])
        self.assertEqual(r.frames["warnings"].first().warning_codes, ["HEADWAY_LONGER_THAN_WINDOW"])
        self.assertTrue(all(x.headway_secs == 60 for x in r.frames["candidates"].collect()))

    def test_parent_scope_rules_duplicates_and_key_types_block_before_join(self):
        from pyspark.sql import functions as F
        s = frequency_spec(); parent = trips_frame(self.spark, s)
        for frame in [parent.unionByName(parent), parent.withColumn("source_sha256", F.lit("b"*64)),
                      parent.withColumn("silver_rule_version", F.lit("wrong")),
                      parent.withColumn("trip_id", F.lit(" "))]:
            with self.assertRaisesRegex(ValueError, "Publica primero"):
                self.validate([fixture(s)], parent=frame)
        with self.assertRaisesRegex(ValueError, "string"):
            self.validate([fixture(s)], parent=parent.withColumn("trip_id", F.lit(1)))
        orphan = self.validate([fixture(s, trip_id="orphan")])
        self.assertEqual(orphan.summary["rejected_rows"], 1)
        self.assertIn("TRIP_ID_NOT_FOUND", orphan.frames["rejected"].first().error_codes)

    def test_empty_scope_wrong_entity_bronze_types_and_timezone_fail_explicitly(self):
        from pyspark.sql import functions as F
        s = frequency_spec(); parent = trips_frame(self.spark, s); source = frequency_frame(self.spark, s)
        with self.assertRaisesRegex(ValueError, "vacío"): self.validate([])
        with self.assertRaisesRegex(ValueError, "vacío"): self.validate([fixture(s, source_sha256="b"*64)])
        with self.assertRaisesRegex(ValueError, "string"):
            read_and_validate(source.withColumn("headway_secs", F.lit(1)), COLUMNS, s, parent)
        with self.assertRaisesRegex(ValueError, "SnapshotSpec"):
            read_and_validate(source, COLUMNS, SnapshotSpec(s.feed_version, s.sha256, "/fixture/trips.txt", "trips"), parent)
        self.spark.conf.set("spark.sql.session.timeZone", "America/Bogota")
        try:
            with self.assertRaisesRegex(ValueError, "UTC"): self.validate([fixture(s)])
        finally: self.spark.conf.set("spark.sql.session.timeZone", "UTC")


if __name__ == "__main__": unittest.main()
