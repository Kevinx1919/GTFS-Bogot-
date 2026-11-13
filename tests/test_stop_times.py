"""Stop_times: visitas, horas extendidas, referencias y publicación repetible."""
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
from gtfs_silver.stop_times_spark import read_and_validate, read_source_header, validate_header
from gtfs_silver.job_config import build_job
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS

COLUMNS = ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "timepoint")
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def stop_time_spec(version="2025-10-28", content_hash="a" * 64, path=None):
    return SnapshotSpec(version, content_hash, path or f"/fixture/{version}/{content_hash}/stop_times.txt", "stop_times")


def fixture(selected, **changes):
    row = dict(trip_id="T1", arrival_time="08:00:00", departure_time="08:00:00", stop_id="A", stop_sequence="0",
               timepoint="0", stop_headsign=None, shape_dist_traveled=None, source_feed_version=selected.feed_version,
               source_sha256=selected.sha256, source_file_path=selected.source_path,
               bronze_loaded_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
    row.update(changes)
    return row


def visit_rows(selected):
    return [fixture(selected), fixture(selected, stop_id="B", stop_sequence="5", arrival_time="08:10:00", departure_time="08:11:00"),
            fixture(selected, stop_sequence="9", arrival_time="25:20:00", departure_time="25:20:00")]


def stop_time_frame(spark, selected, rows=None, columns=COLUMNS):
    from pyspark.sql.types import StringType, StructField, StructType, TimestampType
    names = (*columns, *TECHNICAL_FIELDS)
    schema = StructType([StructField(n, TimestampType() if n == "bronze_loaded_at_utc" else StringType()) for n in names])
    return spark.createDataFrame([{n: r[n] for n in names} for r in (rows if rows is not None else visit_rows(selected))], schema)


def dependency_frames(spark, selected, ids=("T1",)):
    trips = spark.createDataFrame([(i, selected.feed_version, selected.sha256, "trips_v1") for i in ids],
                                  "trip_id string,source_feed_version string,source_sha256 string,silver_rule_version string")
    stops = spark.createDataFrame([(i, t, selected.feed_version, selected.sha256, "stops_v1") for i, t in (("A", 0), ("B", None), ("P", 1))],
                                  "stop_id string,location_type int,source_feed_version string,source_sha256 string,silver_rule_version string")
    return {"trips_df": trips, "stops_df": stops, "frequencies_df": None}


def frequencies_frame(spark, selected):
    return spark.createDataFrame([("T1", v, 0, selected.feed_version, selected.sha256, "frequencies_v1") for v in (0, 3600)],
        "trip_id string,start_time_seconds long,exact_times_effective int,source_feed_version string,source_sha256 string,silver_rule_version string")


class StopTimesContractTests(unittest.TestCase):
    def test_header_bom_optional_columns_and_new_scope(self):
        self.assertEqual(validate_header(COLUMNS), COLUMNS)
        self.assertEqual(validate_header(COLUMNS[:-1]), COLUMNS[:-1])
        self.assertEqual(validate_header((*COLUMNS, "stop_headsign", "shape_dist_traveled"))[-1], "shape_dist_traveled")
        for fields in [(), COLUMNS[1:], (*COLUMNS, "location_id"), (*COLUMNS, "pickup_type"), (*COLUMNS, "trip_id"), (None,)]:
            with self.subTest(fields=fields), self.assertRaises(ValueError): validate_header(fields)
        with TemporaryDirectory(prefix="gtfs-stop-times-header-") as folder:
            path = Path(folder) / "stop_times.txt"; path.write_text(",".join(COLUMNS)+"\n", encoding="utf-8-sig")
            self.assertEqual(read_source_header(str(path)), COLUMNS)

    def test_dispatch_pins_inputs_and_releases_disk_result_on_success_and_failure(self):
        for fail in (False, True):
            spark = MagicMock(); spark.catalog.tableExists.return_value = True
            cached = MagicMock(); result = SimpleNamespace(reference_versions={}, frames={"_checked": cached})
            inputs = {"trips_df": sentinel.trips, "stops_df": sentinel.stops, "frequencies_df": sentinel.frequencies}
            with patch.object(pipeline.stop_times_spark, "read_source_header", return_value=COLUMNS), \
                 patch.object(pipeline, "_versioned_table", return_value=(sentinel.bronze, 3)) as reader, \
                 patch.object(pipeline, "_stop_times_dependencies", return_value=(inputs, {"stops_delta_version": "7"})), \
                 patch.object(pipeline.stop_times_spark, "read_and_validate", return_value=result) as validator, \
                 patch.object(pipeline, "publish_snapshot", side_effect=RuntimeError("fixture failure") if fail else None) as publish:
                arguments = dict(catalog="workspace", schema="fixture", staging_volume="staging", entity="stop_times",
                                 feed_version="2025-10-28", snapshot_sha256="a"*64, mode="validate")
                if fail:
                    with self.assertRaisesRegex(RuntimeError, "fixture failure"): pipeline.run_entity(spark, **arguments)
                else: pipeline.run_entity(spark, **arguments)
            self.assertEqual(reader.call_args.args[1], "workspace.fixture.bronze_gtfs_stop_times")
            self.assertTrue(reader.call_args.kwargs["with_version"])
            self.assertEqual(validator.call_args.kwargs, {**inputs, "persist_result": False})
            self.assertEqual(result.reference_versions["bronze_delta_version"], "3")
            self.assertEqual(publish.call_args.args[3].entity, "stop_times")
            cached.unpersist.assert_called_once()

    def test_dependencies_use_audit_and_optional_frequencies(self):
        for published in (("stop_times.txt",), ("stop_times.txt", "frequencies.txt")):
            spark = MagicMock(); spark.catalog.tableExists.return_value = True
            spark.table.return_value.filter.return_value.select.return_value.distinct.return_value.limit.return_value.collect.return_value = [
                SimpleNamespace(source_file_name=n) for n in published]
            with patch("pyspark.sql.functions.col", return_value=MagicMock()), \
                 patch.object(pipeline, "_versioned_table", return_value=(sentinel.frame, 4)) as reader:
                inputs, refs = pipeline._stop_times_dependencies(spark, "workspace", "fixture", stop_time_spec())
            expected = ["trips", "stops"] + (["frequencies"] if len(published) == 2 else [])
            self.assertEqual([c.args[1] for c in reader.call_args_list], [f"workspace.fixture.silver_gtfs_{e}" for e in expected])
            self.assertTrue(all(c.kwargs["with_version"] for c in reader.call_args_list))
            self.assertEqual(inputs["frequencies_df"], sentinel.frame if len(published) == 2 else None)
            self.assertEqual(refs["frequencies_source_published"], str(len(published) == 2).lower())
        spark.catalog.tableExists.return_value = False
        with self.assertRaisesRegex(ValueError, "auditoría"): pipeline._stop_times_dependencies(spark, "workspace", "fixture", stop_time_spec())

    def test_job_appends_tenth_task_preserving_the_existing_prefix(self):
        job = build_job("/Workspace/Shared/example-project")
        self.assertEqual([t["task_key"] for t in job["tasks"]], ["publish_snapshots", "publish_routes", "publish_stops",
            "publish_calendar", "publish_calendar_dates", "publish_service_dates", "publish_shape_points", "publish_trips",
            "publish_frequencies", "publish_stop_times"])
        task = job["tasks"][-1]
        self.assertEqual(task["depends_on"], [{"task_key": "publish_frequencies"}])
        self.assertEqual(task["for_each_task"]["inputs"], "{{job.parameters.stop_times_work_items}}")
        self.assertEqual(task["for_each_task"]["concurrency"], 1)
        params = {p["name"]: p["default"] for p in job["parameters"]}; items = json.loads(params["stop_times_work_items"])
        self.assertEqual([i["entity"] for i in items], ["stop_times", "stop_times"])
        self.assertEqual([i["feed_version"] for i in items], ["2025-10-28", "2026-09-29"])
        self.assertNotIn("window_start", task["for_each_task"]["task"]["notebook_task"]["base_parameters"])


@unittest.skipUnless(HAS_SPARK, "Requiere Spark y Java.")
class StopTimesSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("stop-time-rules")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC"); cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls): cls.spark.stop()

    def validate(self, rows, columns=COLUMNS, deps=None, **options):
        s = stop_time_spec()
        return read_and_validate(stop_time_frame(self.spark, s, rows, columns), columns, s,
                                 **(dependency_frames(self.spark, s) if deps is None else deps), **options)

    def test_visits_keep_repeated_stops_gaps_extended_hours_and_typed_columns(self):
        s = stop_time_spec(); rows = visit_rows(s); rows.append(dict(rows[1]))
        r = self.validate(rows)
        self.assertEqual((r.summary["input_rows"], r.summary["candidate_rows"], r.summary["identical_copies_consolidated"], r.summary["rejected_rows"]), (4, 3, 1, 0))
        out = r.frames["candidates"].orderBy("stop_sequence").collect()
        self.assertEqual([x.stop_id for x in out], ["A", "B", "A"])
        self.assertEqual(out[-1].arrival_time_seconds, 91200)
        self.assertTrue(all(x.stop_headsign is None and x.shape_dist_traveled is None and not x.is_frequency_template for x in out))
        types = {f.name: f.dataType.simpleString() for f in r.frames["candidates"].schema.fields}
        self.assertEqual([types[n] for n in ("stop_sequence", "timepoint", "shape_dist_traveled", "arrival_time_seconds", "timepoint_effective", "is_frequency_template")],
                         ["int", "int", "double", "bigint", "int", "boolean"])
        self.assertEqual(r.summary["trips_without_visits"], 0)

    def test_missing_intermediate_times_are_not_interpolated_and_regressions_cross_gaps(self):
        s = stop_time_spec(); rows = visit_rows(s); rows[1].update(arrival_time="", departure_time=None)
        r = self.validate(rows)
        self.assertEqual(r.summary["candidate_rows"], 3)
        middle = r.frames["candidates"].filter("stop_sequence=5").first()
        self.assertIsNone(middle.arrival_time_seconds); self.assertIsNone(middle.arrival_time)
        rows[-1].update(arrival_time="07:00:00", departure_time="07:00:00")
        bad = self.validate(rows)
        self.assertEqual(bad.summary["rejected_rows"], 1)
        self.assertIn("VISIT_TIME_BACKWARDS", bad.frames["rejected"].first().error_codes)

    def test_timepoint_total_absence_and_partial_absence_have_distinct_semantics(self):
        s = stop_time_spec(); cols = COLUMNS[:-1]
        r = self.validate(visit_rows(s), cols)
        self.assertTrue(all(x.timepoint is None and x.timepoint_effective == 1 and "timepoint" not in x.source_columns for x in r.frames["candidates"].collect()))
        rows = visit_rows(s); rows[1].update(timepoint=None)
        r = self.validate(rows)
        self.assertEqual(r.summary["warning_rows"], 1)
        middle = r.frames["candidates"].filter("stop_sequence=5").first()
        self.assertIsNone(middle.timepoint_effective)
        rows[1].update(arrival_time=None, departure_time=None)
        r = self.validate(rows)
        self.assertIn("TIMEPOINT_AMBIGUOUS_MISSING_TIMES", r.frames["rejected"].first().error_codes)
        rows[1].update(timepoint="1")
        r = self.validate(rows)
        self.assertIn("ARRIVAL_TIME_REQUIRED", r.frames["rejected"].first().error_codes)
        self.assertIn("DEPARTURE_TIME_REQUIRED", r.frames["rejected"].first().error_codes)

    def test_cast_collisions_and_business_conflicts_reject_all_original_copies(self):
        s = stop_time_spec(); row = fixture(s, stop_sequence="01")
        r = self.validate([row, dict(row), fixture(s, stop_sequence="1")])
        self.assertEqual((r.summary["rejected_rows"], r.summary["identical_copies_consolidated"]), (3, 0))
        self.assertTrue(all("VISIT_KEY_CONFLICT" in x.error_codes and x.original_row_json for x in r.frames["rejected"].collect()))

    def test_invalid_source_values_are_rejected_without_ansi_errors(self):
        s = stop_time_spec(); cols = (*COLUMNS, "shape_dist_traveled", "stop_headsign")
        changes = [dict(stop_sequence="-1"), dict(stop_sequence="1.0"), dict(stop_sequence="2147483648"),
                   dict(arrival_time="08:60:00"), dict(departure_time="-1:00:00"),
                   dict(departure_time="2562047788015216:00:00"), dict(arrival_time="09:00:00"),
                   dict(timepoint="2"), dict(stop_id="P"), dict(stop_id="missing"), dict(stop_id=" A"),
                   dict(trip_id=" T1"), dict(stop_headsign="X\u200bY"), dict(shape_dist_traveled="NaN"),
                   dict(shape_dist_traveled="Infinity"), dict(shape_dist_traveled="-1"), dict(shape_dist_traveled="x"),
                   dict(source_feed_version="2026-09-29"), dict(source_file_path="/wrong/stop_times.txt"),
                   dict(bronze_loaded_at_utc=None), dict(arrival_time=None)]
        rows = [fixture(s, **{"trip_id": f"T{i}", **change}) for i, change in enumerate(changes)]
        deps = dependency_frames(self.spark, s, tuple(f"T{i}" for i in range(len(changes))))
        r = self.validate(rows, cols, deps=deps)
        self.assertEqual(r.summary["rejected_rows"], len(changes))
        codes = {c for x in r.frames["rejected"].collect() for c in x.error_codes}
        self.assertNotIn("VISIT_KEY_CONFLICT", codes)
        self.assertTrue({"STOP_SEQUENCE_INVALID", "ARRIVAL_TIME_INVALID", "DEPARTURE_TIME_INVALID", "ARRIVAL_AFTER_DEPARTURE",
                         "STOP_LOCATION_TYPE_INVALID", "SHAPE_DIST_TRAVELED_INVALID", "SOURCE_FEED_VERSION_MISMATCH"} <= codes)

    def test_distance_and_headsign_preserve_source_without_filling_units_or_labels(self):
        s = stop_time_spec(); cols = (*COLUMNS, "shape_dist_traveled", "stop_headsign"); rows = visit_rows(s)
        for row, d, headsign in zip(rows, ("0", "10.5", "10.5"), ("Destino A", None, "Destino C")):
            row.update(shape_dist_traveled=d, stop_headsign=headsign)
        r = self.validate(rows, cols)
        self.assertEqual((r.summary["candidate_rows"], r.summary["warning_rows"]), (3, 1))
        self.assertEqual(r.frames["warnings"].first().warning_codes, ["SHAPE_DISTANCE_REPEATED"])
        self.assertIsNone(r.frames["candidates"].filter("stop_sequence=5").first().stop_headsign)
        rows[-1]["shape_dist_traveled"]="1"
        r = self.validate(rows, cols)
        self.assertIn("SHAPE_DISTANCE_BACKWARDS", r.frames["rejected"].first().error_codes)

    def test_frequency_multiple_windows_do_not_multiply_visits_or_generate_departures(self):
        s = stop_time_spec(); deps = dependency_frames(self.spark, s); deps["frequencies_df"] = frequencies_frame(self.spark, s)
        r = self.validate(visit_rows(s), deps=deps)
        self.assertEqual((r.summary["candidate_rows"], r.summary["rejected_rows"]), (3, 0))
        self.assertTrue(all(x.is_frequency_template for x in r.frames["candidates"].collect()))
        rows = visit_rows(s); rows[0]["departure_time"]=None
        r = self.validate(rows, deps=deps)
        self.assertIn("FREQUENCY_BASE_DEPARTURE_MISSING", r.frames["rejected"].first().error_codes)

    def test_single_visit_and_trips_without_visits_remain_explicit_diagnostics(self):
        s = stop_time_spec(); deps = dependency_frames(self.spark, s, ("T1", "T2"))
        r = self.validate([fixture(s)], deps=deps)
        self.assertEqual((r.summary["candidate_rows"], r.summary["warning_rows"], r.summary["trips_without_visits"]), (1, 1, 1))
        self.assertTrue(r.summary["ready_for_publication"])
        self.assertEqual(r.reference_versions["diagnostic_trips_without_visits"], "1")
        self.assertEqual(r.frames["warnings"].first().warning_codes, ["TRIP_TOO_FEW_VISITS"])

    def test_dependency_ambiguity_scope_rule_and_schema_fail_before_join(self):
        from pyspark.sql import functions as F
        s = stop_time_spec(); deps = dependency_frames(self.spark, s)
        for entity in ("trips", "stops"):
            key = entity + "_df"; frame = deps[key]
            for changed in (frame.unionByName(frame), frame.withColumn("source_sha256", F.lit("b"*64)),
                            frame.withColumn("silver_rule_version", F.lit("wrong"))):
                with self.assertRaisesRegex(ValueError, "Publica primero"):
                    self.validate(visit_rows(s), deps={**deps, key: changed})
        with self.assertRaisesRegex(ValueError, "location_type"):
            self.validate(visit_rows(s), deps={**deps, "stops_df": deps["stops_df"].withColumn("location_type", F.lit("0"))})
        bad_freq = frequencies_frame(self.spark, s).unionByName(frequencies_frame(self.spark, s))
        with self.assertRaisesRegex(ValueError, "frequencies_v1"):
            self.validate(visit_rows(s), deps={**deps, "frequencies_df": bad_freq})

    def test_empty_scope_bronze_types_timezone_and_disk_cleanup(self):
        from pyspark.sql import functions as F
        s = stop_time_spec(); source = stop_time_frame(self.spark, s); deps = dependency_frames(self.spark, s)
        with self.assertRaisesRegex(ValueError, "vacío"): self.validate([])
        with self.assertRaisesRegex(ValueError, "vacío"): self.validate([fixture(s, source_sha256="b"*64)])
        with self.assertRaisesRegex(ValueError, "string"):
            read_and_validate(source.withColumn("stop_sequence", F.lit(1)), COLUMNS, s, **deps)
        self.spark.conf.set("spark.sql.session.timeZone", "America/Bogota")
        try:
            with self.assertRaisesRegex(ValueError, "UTC"): self.validate(visit_rows(s))
        finally: self.spark.conf.set("spark.sql.session.timeZone", "UTC")
        r = self.validate(visit_rows(s), persist_result=True)
        try:
            self.assertTrue(r.frames["_checked"].storageLevel.useDisk)
            self.assertEqual(r.frames["candidates"].count(), 3)
        finally: r.frames["_checked"].unpersist()


if __name__ == "__main__": unittest.main()
