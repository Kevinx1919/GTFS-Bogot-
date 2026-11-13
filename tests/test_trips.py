"""Trips: referencias únicas, metadata de alcance y datos originales."""
from datetime import date, datetime, timezone
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
from gtfs_silver.job_config import build_job
from gtfs_silver.models import SnapshotSpec, TECHNICAL_FIELDS
from gtfs_silver.trips_spark import read_and_validate, read_source_header, validate_header, validate_scope_headers

COLUMNS = ("route_id", "service_id", "trip_id", "shape_id")
HAS_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def trip_spec(version="2025-10-28", content_hash="a"*64, path=None):
    return SnapshotSpec(version,content_hash,path or f"/fixture/{version}/{content_hash}/trips.txt","trips")


def fixture(selected, **changes):
    row=dict(trip_id="0001",route_id="R01",service_id="SERVICE",shape_id="SHAPE",trip_headsign=None,
             source_feed_version=selected.feed_version,source_sha256=selected.sha256,source_file_path=selected.source_path,
             bronze_loaded_at_utc=datetime(2026,1,1,tzinfo=timezone.utc))
    row.update(changes)
    return row


def trip_frame(spark, selected, rows=None, columns=COLUMNS):
    from pyspark.sql.types import StringType, StructField, StructType, TimestampType
    names=(*columns,*TECHNICAL_FIELDS)
    schema=StructType([StructField(n,TimestampType() if n=="bronze_loaded_at_utc" else StringType()) for n in names])
    return spark.createDataFrame([{n:r[n] for n in names} for r in (rows if rows is not None else [fixture(selected)])],schema)


def dependency_frames(spark, selected):
    suffix=(selected.feed_version,selected.sha256)
    base="source_feed_version string,source_sha256 string,silver_rule_version string"
    return dict(
        routes_df=spark.createDataFrame([("R01",*suffix,"routes_v1")],"route_id string,"+base),
        calendar_df=spark.createDataFrame([("SERVICE",*suffix,"calendar_v1")],"service_id string,"+base),
        calendar_dates_df=spark.createDataFrame([("SERVICE",date(2023,1,d),*suffix,"calendar_dates_v1") for d in [1,2]],"service_id string,date date,"+base),
        shape_points_df=spark.createDataFrame([("SHAPE",seq,*suffix,"shape_points_v1") for seq in [1,3,7]],"shape_id string,shape_pt_sequence int,"+base),
    )


def observations(calendar_files=("calendar.txt","calendar_dates.txt"), shapes=True):
    result=[("routes.txt",json.dumps(["route_id","route_type"])),("stop_times.txt",json.dumps(["trip_id","stop_id","stop_sequence"]))]
    result += [(name,json.dumps(["service_id"])) for name in calendar_files]
    if shapes:result.append(("shapes.txt",json.dumps(["shape_id","shape_pt_sequence"])))
    return result


class TripsContractTests(unittest.TestCase):
    def test_header_accepts_required_and_optional_fields_and_reads_bom(self):
        self.assertEqual(validate_header(COLUMNS[:3]),COLUMNS[:3])
        self.assertEqual(validate_header((*COLUMNS,"trip_headsign")),(*COLUMNS,"trip_headsign"))
        for columns in [(),COLUMNS[1:],(*COLUMNS,"direction_id"),(*COLUMNS,"trip_id"),(None,)]:
            with self.subTest(columns=columns),self.assertRaises(ValueError):validate_header(columns)
        with TemporaryDirectory(prefix="gtfs-trips-header-") as folder:
            path=Path(folder)/"trips.txt";path.write_text(",".join(COLUMNS)+"\n",encoding="utf-8-sig")
            self.assertEqual(read_source_header(str(path)),COLUMNS)

    def test_scope_accepts_declared_calendar_modes_and_optional_shapes(self):
        for calendars in [("calendar.txt",),("calendar_dates.txt",),("calendar.txt","calendar_dates.txt")]:
            for shapes in [False,True]:
                result=validate_scope_headers(observations(calendars,shapes))
                self.assertEqual("shapes.txt" in result,shapes)
                self.assertTrue(set(calendars)<=result)

    def test_scope_rejects_continuous_behavior_before_publication(self):
        for filename in ["routes.txt","stop_times.txt"]:
            for field in ["continuous_pickup","continuous_drop_off"]:
                obs=[(name,json.dumps(["route_id",field])) if name==filename else (name,value) for name,value in observations()]
                with self.subTest(filename=filename,field=field),self.assertRaisesRegex(ValueError,"continuo"):
                    validate_scope_headers(obs)

    def test_scope_rejects_missing_ambiguous_or_corrupt_metadata(self):
        for obs in [[],observations(())[2:],observations((),False),observations()+[observations()[0]],
                    [("routes.txt","bad")],[("routes.txt","{}")],[("routes.txt",'["x","x"]')],[("unexpected.txt",'["x"]')]]:
            with self.subTest(obs=obs),self.assertRaises(ValueError):validate_scope_headers(obs)

    def test_dispatch_preserves_dependency_versions_and_reads_only_trips_bronze(self):
        spark=MagicMock();spark.catalog.tableExists.return_value=True
        result=SimpleNamespace(reference_versions={})
        inputs=dict(routes_df=sentinel.routes,calendar_df=sentinel.calendar,calendar_dates_df=None,shape_points_df=None)
        with patch.object(pipeline.trips_spark,"read_source_header",return_value=COLUMNS) as header, \
             patch.object(pipeline,"_versioned_table",return_value=(sentinel.bronze,4)) as reader, \
             patch.object(pipeline,"_trips_dependencies",return_value=(inputs,{"routes_delta_version":"2"})) as deps, \
             patch.object(pipeline.trips_spark,"read_and_validate",return_value=result) as validator, \
             patch.object(pipeline,"publish_snapshot",return_value={"persisted":False}) as publish:
            pipeline.run_entity(spark,catalog="workspace",schema="fixture",staging_volume="staging",entity="trips",
                                feed_version="2025-10-28",snapshot_sha256="a"*64,mode="validate")
        self.assertTrue(header.call_args.args[0].endswith("/trips.txt"))
        self.assertEqual(reader.call_args.args[1],"workspace.fixture.bronze_gtfs_trips")
        self.assertTrue(reader.call_args.kwargs["with_version"])
        self.assertEqual(validator.call_args.kwargs,inputs)
        self.assertEqual(result.reference_versions["bronze_delta_version"],"4")
        self.assertEqual(result.reference_versions["routes_delta_version"],"2")
        self.assertEqual(publish.call_args.args[3].entity,"trips")
        self.assertEqual(deps.call_args.args[3].entity,"trips")

    def test_job_appends_trips_for_two_snapshots_without_date_horizon(self):
        job=build_job("/Workspace/Shared/example-project")
        self.assertEqual(len(job["tasks"]),10)
        task=job["tasks"][7]
        self.assertEqual(task["task_key"],"publish_trips")
        self.assertEqual(task["depends_on"],[{"task_key":"publish_shape_points"}])
        self.assertEqual(task["for_each_task"]["inputs"],"{{job.parameters.trips_work_items}}")
        p={x["name"]:x["default"] for x in job["parameters"]};items=json.loads(p["trips_work_items"])
        self.assertEqual([i["entity"] for i in items],["trips","trips"])
        self.assertEqual([i["feed_version"] for i in items],["2025-10-28","2026-09-29"])
        self.assertNotIn("window_start",task["for_each_task"]["task"]["notebook_task"]["base_parameters"])


@unittest.skipUnless(HAS_SPARK,"Requiere Spark y Java.")
class TripsSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark=(SparkSession.builder.master("local[1]").appName("trips-rules")
                   .config("spark.ui.enabled","false").config("spark.sql.shuffle.partitions","1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone","UTC");cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):cls.spark.stop()

    def validate(self,rows,columns=COLUMNS,dependencies=None):
        selected=trip_spec()
        return read_and_validate(trip_frame(self.spark,selected,rows,columns),columns,selected,
                                 **(dependency_frames(self.spark,selected) if dependencies is None else dependencies))

    def test_shared_patterns_remain_distinct_and_dependency_grains_do_not_multiply(self):
        from pyspark.sql import functions as F
        selected=trip_spec();rows=[fixture(selected),fixture(selected),fixture(selected,trip_id="0002")]
        source=trip_frame(self.spark,selected,rows).withColumn("trip_headsign",F.lit("Historical value"))
        result=read_and_validate(source,COLUMNS,selected,**dependency_frames(self.spark,selected))
        self.assertEqual((result.summary["input_rows"],result.summary["candidate_rows"],result.summary["identical_copies_consolidated"]),(3,2,1))
        self.assertEqual(result.summary["warning_rows"],0)
        output=result.frames["candidates"].collect()
        self.assertEqual({r.trip_id for r in output},{"0001","0002"})
        self.assertTrue(all(r.trip_headsign is None for r in output))
        self.assertTrue(all(r.source_columns==list(COLUMNS) for r in output))
        self.assertTrue(all(result.frames["candidates"].schema[n].dataType.simpleString()=="string" for n in ["trip_id","route_id","service_id","shape_id","trip_headsign"]))

    def test_optional_shape_and_headsign_remain_null_without_inventing_values(self):
        selected=trip_spec();deps=dependency_frames(self.spark,selected);deps["shape_points_df"]=None
        result=self.validate([fixture(selected)],COLUMNS[:3],deps)
        self.assertTrue(result.summary["ready_for_publication"])
        self.assertIsNone(result.frames["candidates"].first().shape_id)
        columns=(*COLUMNS,"trip_headsign")
        rows=[fixture(selected,shape_id=" ",trip_headsign=" "),fixture(selected,trip_id="0002",shape_id=None,trip_headsign=" Destino ")]
        result=self.validate(rows,columns,deps)
        output=result.frames["candidates"].orderBy("trip_id").collect()
        self.assertIsNone(output[0].trip_headsign)
        self.assertEqual(output[1].trip_headsign," Destino ")
        self.assertEqual(result.summary["warning_rows"],0)

    def test_calendar_modes_accept_ids_without_service_dates_or_active_year_filter(self):
        selected=trip_spec()
        for omitted in ["calendar_df","calendar_dates_df"]:
            deps=dependency_frames(self.spark,selected);deps[omitted]=None
            result=self.validate([fixture(selected)],dependencies=deps)
            self.assertTrue(result.summary["ready_for_publication"])
        deps["calendar_df"]=deps["calendar_dates_df"]=None
        with self.assertRaisesRegex(ValueError,"calendario"):
            self.validate([fixture(selected)],dependencies=deps)

    def test_bad_keys_foreign_keys_and_provenance_keep_original_rejections(self):
        selected=trip_spec();changes=[dict(trip_id=None),dict(trip_id=" bad"),dict(route_id="missing"),dict(service_id="missing"),
              dict(shape_id="missing"),dict(route_id=None),dict(service_id=" "),dict(shape_id=" bad"),dict(trip_headsign="bad\n"),
              dict(source_feed_version="2026-09-29"),dict(source_file_path="/wrong/trips.txt"),dict(bronze_loaded_at_utc=None)]
        rows=[]
        for i,change in enumerate(changes):
            row=fixture(selected,trip_id=f"bad{i}");row.update(change);rows.append(row)
        result=self.validate(rows,(*COLUMNS,"trip_headsign"))
        self.assertEqual(result.summary["rejected_rows"],len(changes))
        self.assertFalse(result.summary["ready_for_publication"])
        rejected=result.frames["rejected"].collect()
        self.assertTrue(all(r.original_row_json and r.error_codes for r in rejected))
        codes={c for r in rejected for c in r.error_codes}
        self.assertTrue({"ROUTE_ID_NOT_FOUND","SERVICE_ID_NOT_FOUND","SHAPE_ID_NOT_FOUND","SOURCE_FEED_VERSION_MISMATCH"}<=codes)
        scoped=self.validate([fixture(selected),fixture(selected,trip_id="other",source_sha256="b"*64)])
        self.assertEqual(scoped.summary["input_rows"],1)

    def test_raw_conflicts_reject_all_copies_before_optional_normalization(self):
        selected=trip_spec();columns=(*COLUMNS,"trip_headsign")
        rows=[fixture(selected,trip_headsign="Destino"),fixture(selected,trip_headsign="Destino"),fixture(selected,trip_headsign=" Destino ")]
        result=self.validate(rows,columns)
        self.assertEqual(result.summary["rejected_rows"],3)
        self.assertEqual(result.summary["identical_copies_consolidated"],0)
        self.assertTrue(all("TRIP_ID_CONFLICT" in r.error_codes for r in result.frames["rejected"].collect()))

    def test_invalid_dependency_scope_keys_markers_and_types_block_preparation(self):
        from pyspark.sql import functions as F
        selected=trip_spec();base=dependency_frames(self.spark,selected)
        for name in ["routes_df","calendar_df","calendar_dates_df","shape_points_df"]:
            deps=dict(base);deps[name]=base[name].unionByName(base[name])
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,"Publica primero"):
                self.validate([fixture(selected)],dependencies=deps)
        for column,value in [("source_sha256","b"*64),("silver_rule_version","wrong")]:
            deps=dict(base);deps["routes_df"]=base["routes_df"].withColumn(column,F.lit(value))
            with self.assertRaisesRegex(ValueError,"Publica primero"):
                self.validate([fixture(selected)],dependencies=deps)
        deps=dict(base);deps["shape_points_df"]=base["shape_points_df"].withColumn("shape_pt_sequence",F.col("shape_pt_sequence").cast("string"))
        with self.assertRaisesRegex(ValueError,"tipo de clave"):
            self.validate([fixture(selected)],dependencies=deps)

    def test_empty_input_bronze_types_and_timezone_fail_explicitly(self):
        from pyspark.sql import functions as F
        selected=trip_spec();source=trip_frame(self.spark,selected)
        with self.assertRaisesRegex(ValueError,"vacío"):
            self.validate([])
        with self.assertRaisesRegex(ValueError,"string"):
            read_and_validate(source.withColumn("trip_id",F.lit(1)),COLUMNS,selected,**dependency_frames(self.spark,selected))
        self.spark.conf.set("spark.sql.session.timeZone","America/Bogota")
        try:
            with self.assertRaisesRegex(ValueError,"UTC"):
                self.validate([fixture(selected)])
        finally:self.spark.conf.set("spark.sql.session.timeZone","UTC")


if __name__=="__main__":unittest.main()
