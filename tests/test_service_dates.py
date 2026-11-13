"""Fechas derivadas: ventanas, excepciones y procedencia con fixtures pequeños."""
from datetime import date
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver import pipeline
from gtfs_silver.job_config import build_job
from gtfs_silver.models import DerivedSnapshotSpec
from gtfs_silver.service_dates_spark import check_existing_window, derive_service_dates
from gtfs_silver.calendars_spark import WEEKDAYS

SPEC=DerivedSnapshotSpec("2026-09-29","a"*64,"2026-01-01","2026-01-07")
REFS={"calendar_table":"spark_catalog.fixture.silver_gtfs_calendar","calendar_delta_version":"0",
      "calendar_dates_table":"spark_catalog.fixture.silver_gtfs_calendar_dates","calendar_dates_delta_version":"0"}
HAS_SPARK=importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


def calendar_frame(spark):
    fields="service_id string,"+",".join(d+" int" for d in WEEKDAYS)+",start_date date,end_date date,source_feed_version string,source_sha256 string,silver_rule_version string"
    return spark.createDataFrame([("001",1,1,1,1,1,0,0,date(2026,1,1),date(2026,1,7),SPEC.feed_version,SPEC.sha256,"calendar_v1")],fields)


def exceptions_frame(spark):
    rows=[("001",date(2026,1,day),kind,SPEC.feed_version,SPEC.sha256,"calendar_dates_v1")
          for day,kind in [(2,2),(3,1),(4,2),(5,1),(8,1)]]
    return spark.createDataFrame(rows,"service_id string,date date,exception_type int,source_feed_version string,source_sha256 string,silver_rule_version string")


class ServiceDatesContractTests(unittest.TestCase):
    def test_window_spec_is_explicit_bounded_and_has_no_fictitious_source_file(self):
        self.assertEqual(SPEC.entity,"service_dates")
        self.assertFalse(hasattr(SPEC,"source_path"))
        DerivedSnapshotSpec(SPEC.feed_version,SPEC.sha256,"2024-01-01","2024-12-31")
        for start,end in [("",""),("2026-01-02","2026-01-01"),("2000-01-01","2099-01-01"),("2026-02-30","2026-03-01")]:
            with self.subTest(start=start),self.assertRaises(ValueError):
                DerivedSnapshotSpec(SPEC.feed_version,SPEC.sha256,start,end)
        with self.assertRaises(ValueError):DerivedSnapshotSpec(SPEC.feed_version,"bad",SPEC.window_start,SPEC.window_end)
        with self.assertRaises(ValueError):DerivedSnapshotSpec(SPEC.feed_version,SPEC.sha256,SPEC.window_start,SPEC.window_end,"calendar")

    def test_pipeline_dispatches_derived_spec_without_reading_a_txt(self):
        spark=MagicMock()
        with patch.object(pipeline,"_run_service_dates",return_value={"persisted":False}) as derive:
            pipeline.run_entity(spark,catalog="workspace",schema="fixture",staging_volume="unused",entity="service_dates",
                                feed_version=SPEC.feed_version,snapshot_sha256=SPEC.sha256,window_start=SPEC.window_start,window_end=SPEC.window_end,mode="validate")
        self.assertEqual(derive.call_args.args[3],SPEC)
        spark.catalog.tableExists.assert_not_called()

    def test_template_selects_only_2026_and_does_not_add_window_refs_to_source_tasks(self):
        job=build_job("/Workspace/Shared/example-project")
        self.assertEqual(len(job["tasks"]),10)
        task=next(t for t in job["tasks"] if t["task_key"]=="publish_service_dates")
        self.assertEqual(task["task_key"],"publish_service_dates")
        self.assertEqual(task["depends_on"],[{"task_key":"publish_calendar_dates"}])
        p={p["name"]:p["default"] for p in job["parameters"]}
        work=json.loads(p["service_dates_work_items"])
        self.assertEqual(len(work),1)
        self.assertEqual((work[0]["feed_version"],work[0]["window_start"],work[0]["window_end"]),("2026-09-29","2026-01-01","2026-12-31"))
        self.assertNotIn("window_start",job["tasks"][0]["for_each_task"]["task"]["notebook_task"]["base_parameters"])


@unittest.skipUnless(HAS_SPARK,"Requiere Spark y Java.")
class ServiceDatesSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark=(SparkSession.builder.master("local[1]").appName("service-dates-rules")
                   .config("spark.ui.enabled","false").config("spark.sql.shuffle.partitions","1").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone","UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):cls.spark.stop()

    def derive(self,c=None,e=None):return derive_service_dates(self.spark,SPEC,c,e,REFS)

    def test_weekly_union_additions_minus_removals_reconciles_effective_changes(self):
        result=self.derive(calendar_frame(self.spark),exceptions_frame(self.spark))
        rows={r.service_date:r for r in result.frames["candidates"].collect()}
        self.assertEqual(set(rows),{date(2026,1,d) for d in [1,3,5,6,7]})
        self.assertFalse(rows[date(2026,1,3)].weekly_pattern_active)
        self.assertTrue(rows[date(2026,1,5)].weekly_pattern_active)
        self.assertEqual(rows[date(2026,1,5)].activation_source,"calendar_date_addition")
        self.assertEqual((result.summary["weekly_service_days"],result.summary["added_new_days"],result.summary["removed_active_days"]),(5,1,1))
        self.assertEqual(result.summary["exception_rules_in_window"],4)
        self.assertEqual(result.summary["exception_rules_outside_window"],1)
        self.assertEqual(result.summary["input_rows"],5)
        self.assertEqual(result.summary["source_calendar_dates_rows"],5)
        self.assertEqual(json.loads(rows[date(2026,1,1)].input_versions_json),REFS)
        self.assertEqual(result.frames["rejected"].columns[:2],["service_id","service_date"])
        self.assertEqual(result.frames["candidates"].schema["service_date"].dataType.simpleString(),"date")

    def test_single_source_modes_work_and_source_temporal_warnings_are_preserved(self):
        from pyspark.sql import functions as F
        calendar=calendar_frame(self.spark).withColumn("start_date",F.lit("2000-01-01").cast("date")).withColumn("end_date",F.lit("2099-01-01").cast("date"))
        weekly=self.derive(calendar,None)
        self.assertEqual(weekly.summary["candidate_rows"],5)
        self.assertEqual(weekly.summary["warning_rows"],5)
        dates=self.derive(None,exceptions_frame(self.spark))
        self.assertEqual(dates.summary["candidate_rows"],2)
        self.assertEqual(dates.summary["source_calendar_rows"],0)

    def test_invalid_source_schemas_rules_scope_and_duplicate_keys_block(self):
        from pyspark.sql import functions as F
        c=calendar_frame(self.spark);e=exceptions_frame(self.spark)
        for bad in [c.unionByName(c),c.withColumn("silver_rule_version",F.lit("wrong")),c.withColumn("source_sha256",F.lit("b"*64)),c.withColumn("monday",F.lit(2)),c.withColumn("start_date",F.col("start_date").cast("string"))]:
            with self.assertRaises(ValueError):self.derive(bad,e)
        with self.assertRaises(ValueError):self.derive(c,e.unionByName(e))
        with self.assertRaises(ValueError):derive_service_dates(self.spark,SPEC,c,e,{})
        with self.assertRaises(ValueError):self.derive(None,None)
        missing=e.withColumn("service_id",F.lit("missing"))
        with self.assertRaises(ValueError):self.derive(c,missing)

    def test_empty_window_guard_and_horizon_stability_protect_published_data(self):
        from pyspark.sql import functions as F
        c=calendar_frame(self.spark)
        for day in WEEKDAYS:c=c.withColumn(day,F.lit(0))
        with self.assertRaisesRegex(ValueError,"no produce días activos"):self.derive(c,None)
        output=self.derive(calendar_frame(self.spark),exceptions_frame(self.spark)).frames["candidates"]
        check_existing_window(output,SPEC)
        other=DerivedSnapshotSpec(SPEC.feed_version,SPEC.sha256,"2026-01-02","2026-01-08")
        with self.assertRaisesRegex(ValueError,"otro horizonte"):check_existing_window(output,other)
        check_existing_window(output,DerivedSnapshotSpec(SPEC.feed_version,"b"*64,"2026-01-02","2026-01-08"))


if __name__=="__main__":unittest.main()
