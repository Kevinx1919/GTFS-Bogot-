"""Puntos de trazado: identidad, geometría y reglas con fixtures pequeños."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch, sentinel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver import pipeline
from gtfs_silver.job_config import build_job
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS
from gtfs_silver.shape_points_spark import BUSINESS_TYPES, read_and_validate, read_source_header, validate_header

COLUMNS = ("shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence")
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def shape_spec(version="2025-10-28", content_hash="a" * 64, path=None):
    return SnapshotSpec(version, content_hash, path or f"/fixture/{version}/{content_hash}/shapes.txt", "shape_points")


def fixture(selected, **changes):
    row = dict(shape_id="A", shape_pt_sequence="1", shape_pt_lat="4.6", shape_pt_lon="-74.1",
               shape_dist_traveled=None, source_feed_version=selected.feed_version, source_sha256=selected.sha256,
               source_file_path=selected.source_path, bronze_loaded_at_utc=datetime(2026, 1, 1, tzinfo=timezone.utc))
    row.update(changes)
    return row


def shape_frame(spark, selected, rows=None, columns=COLUMNS):
    from pyspark.sql.types import StringType, StructField, StructType, TimestampType
    names = (*columns, *TECHNICAL_FIELDS)
    schema = StructType([StructField(name, TimestampType() if name == "bronze_loaded_at_utc" else StringType()) for name in names])
    return spark.createDataFrame([{name: row[name] for name in names} for row in (rows if rows is not None else [fixture(selected)])], schema)


class ShapePointsContractTests(unittest.TestCase):
    def test_snapshot_maps_shape_points_to_real_source_and_preserves_other_entities(self):
        selected = shape_spec()
        self.assertEqual(selected.source_entity, "shapes")
        with self.assertRaises(ValueError):
            SnapshotSpec(selected.feed_version, selected.sha256, "/fixture/shape_points.txt", "shape_points")
        agency = SnapshotSpec(selected.feed_version, selected.sha256, "/fixture/agency.txt")
        self.assertEqual(agency.source_entity, "agency")
        with self.assertRaises(ValueError):
            SnapshotSpec(selected.feed_version, selected.sha256, "/fixture/shapes.txt", "stops")

    def test_header_handles_optional_distance_bom_and_rejects_incomplete_or_new_fields(self):
        self.assertEqual(validate_header(COLUMNS), COLUMNS)
        self.assertEqual(len(validate_header((*COLUMNS, "shape_dist_traveled"))), 5)
        for bad in [(), COLUMNS[:-1], (*COLUMNS, "unknown"), (*COLUMNS, "shape_id"), (None,)]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_header(bad)
        with TemporaryDirectory(prefix="gtfs-shapes-header-") as folder:
            path = Path(folder) / "shapes.txt"
            path.write_text(",".join(COLUMNS) + "\n", encoding="utf-8-sig")
            self.assertEqual(read_source_header(str(path)), COLUMNS)

    def test_pipeline_uses_shapes_bronze_and_header_without_downstream_dependencies(self):
        spark = MagicMock()
        spark.catalog.tableExists.return_value = True
        spark.sql.return_value.first.return_value = {"version": 4}
        spark.read.option.return_value.table.return_value = sentinel.bronze
        with patch.object(pipeline.shape_points_spark, "read_source_header", return_value=COLUMNS) as header, \
             patch.object(pipeline.shape_points_spark, "read_and_validate", return_value=sentinel.result) as validate, \
             patch.object(pipeline, "publish_snapshot", return_value={"persisted": False}) as publish:
            pipeline.run_entity(spark, catalog="workspace", schema="fixture", staging_volume="staging",
                                entity="shape_points", feed_version="2025-10-28", snapshot_sha256="a"*64, mode="validate")
        selected = validate.call_args.args[2]
        self.assertEqual(selected.entity, "shape_points")
        self.assertTrue(header.call_args.args[0].endswith("/shapes.txt"))
        self.assertEqual(spark.catalog.tableExists.call_count, 1)
        self.assertEqual(spark.sql.call_args.args[0], "describe history `workspace`.`fixture`.`bronze_gtfs_shapes` limit 1")
        self.assertEqual(publish.call_args.args[2], selected)
        self.assertEqual(publish.call_args.args[3].entity, "shape_points")

    def test_wrong_source_mapping_stops_before_io(self):
        spark = MagicMock()
        with patch.object(pipeline, "load_registry", return_value={"shape_points": {
                "enabled": True, "validator": "shape_points_v1", "bronze_table": "bronze_gtfs_shape_points"}}):
            with self.assertRaises(ValueError):
                pipeline.run_entity(spark, catalog="workspace", schema="fixture", staging_volume="staging",
                                    entity="shape_points", feed_version="2025-10-28", snapshot_sha256="a"*64)
        spark.catalog.tableExists.assert_not_called()
        spark.conf.set.assert_not_called()

    def test_job_preserves_six_tasks_and_adds_serial_shapes_for_both_snapshots(self):
        job = build_job("/Workspace/Shared/example-project")
        self.assertEqual([t["task_key"] for t in job["tasks"]], ["publish_snapshots", "publish_routes", "publish_stops",
                         "publish_calendar", "publish_calendar_dates", "publish_service_dates", "publish_shape_points", "publish_trips", "publish_frequencies"])
        task = next(t for t in job["tasks"] if t["task_key"] == "publish_shape_points")
        self.assertEqual(task["depends_on"], [{"task_key": "publish_service_dates"}])
        self.assertEqual(task["for_each_task"]["concurrency"], 1)
        self.assertEqual(task["for_each_task"]["inputs"], "{{job.parameters.shape_points_work_items}}")
        params = {p["name"]: p["default"] for p in job["parameters"]}
        items = json.loads(params["shape_points_work_items"])
        self.assertEqual([i["feed_version"] for i in items], ["2025-10-28", "2026-09-29"])
        self.assertTrue(all(i["entity"] == "shape_points" for i in items))
        self.assertNotIn("window_start", task["for_each_task"]["task"]["notebook_task"]["base_parameters"])


@unittest.skipUnless(HAS_SPARK, "Requiere Spark y Java.")
class ShapePointsSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master("local[1]").appName("shape-points-rules")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def validate(self, rows, columns=COLUMNS):
        selected = shape_spec()
        return read_and_validate(shape_frame(self.spark, selected, rows, columns), columns, selected)

    def test_copies_do_not_create_false_segments_and_revisits_are_preserved(self):
        from pyspark.sql import functions as F
        selected = shape_spec()
        rows = [fixture(selected, shape_pt_sequence=str(seq), shape_pt_lat=str(lat), shape_pt_lon=str(lon))
                for seq, lat, lon in [(0,4.6,-74.1),(6,4.7,-74.2),(11,4.7,-74.2),(20,4.6,-74.1)]]
        rows += [fixture(selected, shape_id="B", shape_pt_sequence=str(seq), shape_pt_lat=str(lat))
                 for seq, lat in [(1,4.5),(9,4.6)]]
        rows.append(dict(rows[1], bronze_loaded_at_utc=datetime(2026,2,1,tzinfo=timezone.utc)))
        bronze = shape_frame(self.spark, selected, rows).withColumn("shape_dist_traveled", F.lit("999"))
        result = read_and_validate(bronze, COLUMNS, selected)
        self.assertEqual((result.summary["input_rows"],result.summary["candidate_rows"],result.summary["identical_copies_consolidated"]),(7,6,1))
        self.assertEqual(result.summary["warning_rows"],1)
        self.assertEqual(result.summary["consecutive_position_repeated_rows"],1)
        output = result.frames["candidates"].collect()
        self.assertTrue(all(r.shape_dist_traveled is None for r in output))
        self.assertTrue(all(r.source_columns == list(COLUMNS) for r in output))
        self.assertEqual(result.frames["candidates"].schema["shape_pt_sequence"].dataType.simpleString(),"int")
        self.assertEqual(result.frames["candidates"].schema["shape_pt_lat"].dataType.simpleString(),"double")
        warning = result.frames["warnings"].first()
        self.assertEqual((warning.shape_id,warning.shape_pt_sequence),("A","11"))
        self.assertEqual(warning.warning_codes,["CONSECUTIVE_POSITION_REPEATED"])

    def test_optional_distance_accepts_missing_values_and_scientific_finite_numbers(self):
        selected=shape_spec(); columns=(*COLUMNS,"shape_dist_traveled")
        rows=[fixture(selected,shape_pt_sequence=seq,shape_pt_lat=lat,shape_dist_traveled=dist)
              for seq,lat,dist in [("001","4.6e0","0"),("5","4.7"," "),("9","4.8","1e2")]]
        result=self.validate(rows,columns)
        self.assertTrue(result.summary["ready_for_publication"])
        output=result.frames["candidates"].orderBy("shape_pt_sequence").collect()
        self.assertEqual([r.shape_pt_sequence for r in output],[1,5,9])
        self.assertEqual([r.shape_dist_traveled for r in output],[0.0,None,100.0])
        self.assertEqual(result.summary["warning_rows"],0)

    def test_required_values_ranges_and_provenance_fail_without_hiding_rows(self):
        selected=shape_spec()
        changes=[dict(shape_id=None),dict(shape_id=" A"),dict(shape_id="A\n"),dict(shape_pt_sequence=None),
                 dict(shape_pt_sequence="-1"),dict(shape_pt_sequence="1.0"),dict(shape_pt_sequence="2147483648"),
                 dict(shape_pt_lat=None),dict(shape_pt_lat="91"),dict(shape_pt_lat="NaN"),dict(shape_pt_lat="Infinity"),
                 dict(shape_pt_lon="181"),dict(source_feed_version="2026-09-29"),dict(source_file_path="/wrong/shapes.txt"),
                 dict(bronze_loaded_at_utc=None)]
        rows=[]
        for i,change in enumerate(changes):
            row=fixture(selected,shape_id=f"bad{i}");row.update(change);rows.append(row)
        result=self.validate(rows)
        self.assertEqual(result.summary["rejected_rows"],len(rows))
        self.assertEqual(result.summary["candidate_rows"],0)
        self.assertFalse(result.summary["ready_for_publication"])
        rejected=result.frames["rejected"].collect()
        self.assertTrue(all(r.original_row_json and r.error_codes for r in rejected))
        self.assertTrue(any("SOURCE_FEED_VERSION_MISMATCH" in r.error_codes for r in rejected))
        self.assertTrue(any("BRONZE_TIMESTAMP_INVALID" in r.error_codes for r in rejected))
        scoped=self.validate([fixture(selected),fixture(selected,shape_id="other",source_sha256="b"*64)])
        self.assertEqual(scoped.summary["input_rows"],1)

    def test_raw_key_conflicts_and_cast_collisions_reject_all_variants(self):
        selected=shape_spec()
        rows=[fixture(selected),fixture(selected,shape_pt_lat="4.7"),
              fixture(selected,shape_id="B",shape_pt_sequence="01"),fixture(selected,shape_id="B",shape_pt_sequence="1")]
        result=self.validate(rows)
        self.assertEqual(result.summary["rejected_rows"],4)
        self.assertEqual(result.summary["identical_copies_consolidated"],0)
        rejected=result.frames["rejected"].collect()
        self.assertTrue(all("SHAPE_POINT_KEY_CONFLICT" in r.error_codes for r in rejected if r.shape_id=="A"))
        self.assertTrue(all("SHAPE_SEQUENCE_CAST_COLLISION" in r.error_codes for r in rejected if r.shape_id=="B"))

    def test_distance_must_increase_across_missing_values_and_remain_finite(self):
        selected=shape_spec(); columns=(*COLUMNS,"shape_dist_traveled")
        rows=[fixture(selected,shape_pt_sequence=str(seq),shape_pt_lat=str(lat),shape_dist_traveled=dist)
              for seq,lat,dist in [(1,4.6,"10"),(3,4.7,None),(8,4.8,"5")]]
        rows += [fixture(selected,shape_id="equal",shape_pt_sequence=str(seq),shape_pt_lat=str(lat),shape_dist_traveled="1")
                 for seq,lat in [(1,4.6),(2,4.7)]]
        rows += [fixture(selected,shape_id=f"bad{i}",shape_dist_traveled=v) for i,v in enumerate(["-1","NaN","Infinity","1e309"])]
        result=self.validate(rows,columns)
        self.assertEqual(result.summary["rejected_rows"],6)
        reasons=[r.error_codes for r in result.frames["rejected"].collect()]
        self.assertEqual(sum("SHAPE_DISTANCE_NOT_INCREASING" in r for r in reasons),2)
        self.assertEqual(sum("SHAPE_DIST_TRAVELED_INVALID" in r for r in reasons),4)

    def test_degenerate_geometry_and_zero_coordinates_warn_without_dropping_points(self):
        selected=shape_spec()
        result=self.validate([fixture(selected,shape_pt_sequence=str(seq),shape_pt_lat="0",shape_pt_lon="0") for seq in [0,5]])
        self.assertEqual(result.summary["candidate_rows"],2)
        self.assertEqual(result.summary["rejected_rows"],0)
        self.assertEqual(result.summary["warning_rows"],2)
        self.assertEqual(result.summary["degenerate_shape_rows"],2)
        self.assertEqual(result.summary["zero_coordinate_pair_rows"],2)
        self.assertTrue(result.summary["ready_for_publication"])

    def test_empty_snapshot_wrong_bronze_types_and_timezone_are_actionable(self):
        from pyspark.sql import functions as F
        selected=shape_spec(); good=shape_frame(self.spark,selected)
        with self.assertRaisesRegex(ValueError,"vacío"):
            read_and_validate(shape_frame(self.spark,selected,[]),COLUMNS,selected)
        with self.assertRaisesRegex(ValueError,"string"):
            read_and_validate(good.withColumn("shape_pt_sequence",F.lit(1)),COLUMNS,selected)
        with self.assertRaisesRegex(ValueError,"Faltan columnas"):
            read_and_validate(good.drop("shape_id"),COLUMNS,selected)
        self.spark.conf.set("spark.sql.session.timeZone","America/Bogota")
        try:
            with self.assertRaisesRegex(ValueError,"UTC"):
                read_and_validate(good,COLUMNS,selected)
        finally:
            self.spark.conf.set("spark.sql.session.timeZone","UTC")


if __name__ == "__main__":
    unittest.main()
