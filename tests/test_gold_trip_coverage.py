"""Gold con fixtures pequeñas; sin red ni escrituras sobre el Workspace."""
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'databricks'))
from gtfs_gold.trip_coverage import _identity, prepare_coverage, run_coverage

HAS_DELTA=bool(importlib.util.find_spec("pyspark") and os.environ.get("GTFS_DELTA_TEST_JARS") and shutil.which("java"))
VERSION="2026-09-29"; HASH="a"*64
STAMP=datetime(2026,11,17,tzinfo=timezone.utc)
AUDIT_SCHEMA="entity string, source_feed_version string, source_sha256 string, silver_run_id string, status string, silver_committed boolean, silver_rule_version string, target_table string, candidate_rows long, started_at_utc timestamp"


class GoldIdentityTests(unittest.TestCase):
    def test_identity_preserves_valid_snapshot_and_rejects_unsafe_parameters(self):
        _identity("workspace","fixture",VERSION,HASH)
        for catalog,schema,version,sha in (("bad.catalog","fixture",VERSION,HASH),("workspace","fixture", "2026-02-30",HASH),
                                         ("workspace","fixture","20260929",HASH),("workspace","fixture",VERSION,"bad")):
            with self.subTest(version=version,sha=sha),self.assertRaises(ValueError):
                _identity(catalog,schema,version,sha)


@unittest.skipUnless(HAS_DELTA,"Requiere Spark/Delta offline configurados.")
class GoldCoverageDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.temporary=TemporaryDirectory(prefix="gtfs-gold-")
        cls.spark=(SparkSession.builder.master("local[1]").appName("gold-coverage-tests")
                   .config("spark.ui.enabled","false").config("spark.sql.shuffle.partitions","1")
                   .config("spark.databricks.delta.snapshotPartitions","1")
                   .config("spark.sql.warehouse.dir",Path(cls.temporary.name).as_uri())
                   .config("spark.jars",os.environ["GTFS_DELTA_TEST_JARS"])
                   .config("spark.sql.extensions","io.delta.sql.DeltaSparkSessionExtension")
                   .config("spark.sql.catalog.spark_catalog","org.apache.spark.sql.delta.catalog.DeltaCatalog").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone","UTC");cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):cls.spark.stop();cls.temporary.cleanup()

    def setUp(self):
        self.schema="gold_"+uuid4().hex; self.spark.sql(f"create database {self.schema}")
        self.args=dict(catalog="spark_catalog",schema=self.schema,feed_version=VERSION,sha256=HASH)
        self.target=f"spark_catalog.{self.schema}.gold_gtfs_trip_coverage"
        self.audit=f"spark_catalog.{self.schema}.audit_gtfs_silver_runs"
        self.gold_audit=f"spark_catalog.{self.schema}.audit_gtfs_gold_runs"

    def tearDown(self):self.spark.sql(f"drop database {self.schema} cascade")

    def seed(self,version=VERSION,sha=HASH):
        frames={
            "trips": ([(version,sha,t,"route","service","trips-run","trips_v1") for t in ("zero","one","many","frequency")],
                      "source_feed_version string, source_sha256 string, trip_id string, route_id string, service_id string, silver_run_id string, silver_rule_version string"),
            "stop_times": ([(version,sha,t,a,d,"visits-run","stop_times_v1") for t,a,d in
                            [("one",100,100),("many",100,110),("many",None,None),("many",200,210),("frequency",0,0),("frequency",100,100)]],
                           "source_feed_version string, source_sha256 string, trip_id string, arrival_time_seconds long, departure_time_seconds long, silver_run_id string, silver_rule_version string"),
            "frequencies": ([(version,sha,"frequency",0,"frequency-run","frequencies_v1")]*2,
                            "source_feed_version string, source_sha256 string, trip_id string, exact_times_effective int, silver_run_id string, silver_rule_version string"),
        }
        audits=[]
        for entity,(rows,schema) in frames.items():
            table=f"spark_catalog.{self.schema}.silver_gtfs_{entity}"
            self.spark.createDataFrame(rows,schema).write.format("delta").mode("append").saveAsTable(table)
            run=rows[0][-2]
            audits.append((entity,version,sha,run,"SUCCEEDED",True,entity+"_v1",table,len(rows),STAMP))
        self.spark.createDataFrame(audits,AUDIT_SCHEMA).write.format("delta").mode("append").saveAsTable(self.audit)

    def test_validate_publish_retry_and_preserve_history(self):
        self.seed()
        result=run_coverage(self.spark,**self.args)
        self.assertEqual((result["candidate_rows"],result["sin_visitas"],result["una_visita"],result["varias_visitas"]),(4,1,1,2))
        self.assertEqual((result["published_visits"],result["frequency_windows"]),(6,2))
        self.assertFalse(self.spark.catalog.tableExists(self.target));self.assertFalse(self.spark.catalog.tableExists(self.gold_audit))
        run_coverage(self.spark,mode="publish",**self.args)
        frame=self.spark.table(self.target)
        frequency=frame.filter("trip_id='frequency'").first()
        self.assertEqual((frequency["visit_count"],frequency["frequency_window_count"]),(2,2))
        self.assertEqual(frame.filter("trip_id='many'").first()["visits_without_complete_time_pair"],1)
        self.seed("2025-10-28","b"*64)
        run_coverage(self.spark,mode="publish",**{**self.args,"feed_version":"2025-10-28","sha256":"b"*64})
        original=[tuple(r) for r in self.spark.table(self.target).filter("source_feed_version='2025-10-28'").orderBy("trip_id").collect()]
        run_coverage(self.spark,mode="publish",**self.args)
        self.assertEqual(self.spark.table(self.target).count(),8)
        self.assertEqual(original,[tuple(r) for r in self.spark.table(self.target).filter("source_feed_version='2025-10-28'").orderBy("trip_id").collect()])

    def test_source_drift_and_latest_failure_block_publication(self):
        self.seed()
        self.spark.sql(f"update spark_catalog.{self.schema}.silver_gtfs_stop_times set silver_run_id='changed' where trip_id='one'")
        with self.assertRaisesRegex(ValueError,"no coincide"):
            run_coverage(self.spark,**self.args)
        self.spark.sql(f"update spark_catalog.{self.schema}.silver_gtfs_stop_times set silver_run_id='visits-run' where trip_id='one'")
        later=("trips",VERSION,HASH,"later","FAILED",False,"trips_v1",f"spark_catalog.{self.schema}.silver_gtfs_trips",4,STAMP+timedelta(days=1))
        self.spark.createDataFrame([later],AUDIT_SCHEMA).write.format("delta").mode("append").saveAsTable(self.audit)
        with self.assertRaisesRegex(ValueError,"última publicación"):
            run_coverage(self.spark,mode="publish",**self.args)
        self.assertFalse(self.spark.catalog.tableExists(self.target))
        closed=self.spark.table(self.gold_audit).filter("event_type='CLOSED'").first()
        self.assertEqual((closed["status"],closed["gold_committed"]),("FAILED",False))
