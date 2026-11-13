"""Decisiones del plan y lecturas Spark, con fixtures pequeños y sin red."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "databricks"))
from gtfs_bronze.contracts import ENTITY_NAMES, RULE_VERSION
from gtfs_bronze.runtime import CLOSURE_DDL
from gtfs_silver.planner import ENTITY_ORDER, bronze_snapshots, build_plan
from gtfs_silver.planner_runtime import assert_bronze_ready, create_plan, emit_plan
from gtfs_silver.pipeline import load_registry, run_entity
from gtfs_silver.job_config import build_job

STAMP = datetime(2026, 11, 13, tzinfo=timezone.utc)
VERSION = "2026-09-29"
HASH = "a" * 64
POLICY = {"feed_version_from": "2026-01-01", "feed_version_to": "2026-12-31",
          "window_start": "2026-01-01", "window_end": "2026-12-31"}
HAS_DELTA = bool(importlib.util.find_spec("pyspark") and os.environ.get("GTFS_DELTA_TEST_JARS") and shutil.which("java"))


def events(version=VERSION, sha=HASH, *, schema="fixture"):
    inventory = {entity: {"source_present": True, "source_row_count": 1, "snapshot_count": 1,
                         "table_exists": True, "table_name": f"spark_catalog.{schema}.bronze_gtfs_{entity}",
                         "delta_version": 2, "bronze_columns": ["fixture"]} for entity in ENTITY_NAMES}
    common = {"quality_run_id": "quality-" + sha, "source_feed_version": version, "source_sha256": sha,
              "rule_version": RULE_VERSION, "started_at_utc": STAMP, "warning_policy": "silver_contracts_v1",
              "coordinator_run_id": "", "result_sha256": "c" * 64}
    return [{**common, "event_type": "STARTED", "completed_at_utc": None, "status": "RUNNING",
             "total_checks": 0, "blocking_failures": 0, "warning_count": 0, "validation_completed": False,
             "ready_for_silver": False, "entity_inventory_json": "{}"},
            {**common, "event_type": "CLOSED", "completed_at_utc": STAMP + timedelta(seconds=1), "status": "PASSED",
             "total_checks": 60, "blocking_failures": 0, "warning_count": 0, "validation_completed": True,
             "ready_for_silver": True, "entity_inventory_json": json.dumps(inventory)}]


def completed(version=VERSION, sha=HASH, *, schema="fixture", names=ENTITY_ORDER):
    audits, targets = [], {}
    for index, name in enumerate(names):
        start = STAMP + timedelta(minutes=index + 2)
        audit = {"entity": name, "source_feed_version": version, "source_sha256": sha,
                 "silver_run_id": name + "-run", "status": "SUCCEEDED", "silver_rule_version": name + "_v1",
                 "target_table": f"spark_catalog.{schema}.silver_gtfs_{name}", "candidate_rows": 1,
                 "input_rows": 1, "rejected_rows": 0, "silver_committed": True,
                 "started_at_utc": start, "finished_at_utc": start + timedelta(seconds=1)}
        audits.append(audit)
        targets[(name, version, sha)] = {"exists": True, "rows": 1, "run_ids": [name + "-run"],
                                       "rules": [name + "_v1"], "invalid_technical_rows": 0}
        if name == "service_dates": targets[(name, version, sha)]["windows"] = [[POLICY["window_start"], POLICY["window_end"]]]
    return audits, targets


def plan(ev=None, audits=None, targets=None, **options):
    return build_plan(events() if ev is None else ev, audits or [], targets or {}, load_registry(), POLICY,
                      catalog="spark_catalog", schema="fixture", **options)


class SilverPlannerTests(unittest.TestCase):
    def test_new_snapshot_schedules_dependencies_in_same_plan_and_shape_mapping(self):
        result = plan(targets={})
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["counts"]["PENDING"], 10)
        self.assertEqual(list(result["work_items"]), list(ENTITY_ORDER))
        self.assertEqual(result["work_items"]["shape_points"][0]["expected_rule_version"], "shape_points_v1")
        self.assertEqual(result["work_items"]["service_dates"][0]["window_start"], "2026-01-01")

    def test_complete_snapshot_and_no_snapshots_return_no_work(self):
        audits, targets = completed()
        result = plan(audits=audits, targets=targets)
        self.assertEqual((result["status"], result["counts"]["COMPLETE"]), ("NO_WORK", 10))
        self.assertTrue(all(not values for values in result["work_items"].values()))
        self.assertEqual(plan(ev=[], targets={})["status"], "NO_WORK")

    def test_latest_incomplete_or_failed_bronze_does_not_reuse_old_success(self):
        old = events()
        new = {**old[0], "quality_run_id": "new", "started_at_utc": STAMP + timedelta(hours=1)}
        result = plan(ev=old + [new], targets={})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["decisions"][0]["reason"], "INCOMPLETE_BRONZE_ATTEMPT")
        bad = deepcopy(old); bad[1].update(status="FAILED", blocking_failures=1, ready_for_silver=False)
        self.assertEqual(plan(ev=bad, targets={})["status"], "BLOCKED")

    def test_ambiguous_attempt_and_invalid_inventory_block(self):
        ev = events()
        self.assertEqual(plan(ev=ev + [{**ev[0], "quality_run_id": "tie"}], targets={})["status"], "BLOCKED")
        ev[1]["entity_inventory_json"] = "{}"
        self.assertEqual(plan(ev=ev, targets={})["status"], "BLOCKED")

    def test_schema_warnings_keep_silver_validation_required(self):
        ev=events(); ev[1].update(status="WARNING", warning_count=5)
        self.assertEqual(plan(ev=ev, targets={})["status"], "READY")

    def test_latest_failed_silver_blocks_instead_of_falling_back(self):
        audits, targets = completed()
        failed = {**audits[0], "silver_run_id": "new-failure", "status": "FAILED", "silver_committed": False,
                  "started_at_utc": STAMP + timedelta(days=1)}
        result = plan(audits=audits + [failed], targets=targets)
        states = {row["entity"]: row["status"] for row in result["decisions"]}
        self.assertEqual(states["agency"], "BLOCKED")
        self.assertEqual(states["routes"], "BLOCKED")
        dbutils = SimpleNamespace(jobs=SimpleNamespace(taskValues=Mock()))
        with self.assertRaisesRegex(RuntimeError, "bloqueos"): emit_plan(dbutils, result)
        dbutils.jobs.taskValues.set.assert_not_called()

    def test_missing_or_inconsistent_destination_requires_recovery(self):
        audits, original = completed()
        key=("agency", VERSION, HASH)
        for state in ({"exists": False, "rows": 0}, {**original[key], "rows": 2},
                      {**original[key], "run_ids": ["different"]}):
            with self.subTest(state=state):
                result=plan(audits=audits, targets={**original,key:state})
                self.assertEqual(result["decisions"][0]["status"], "BLOCKED")
        self.assertEqual(plan(targets={key:original[key]})["decisions"][0]["reason"], "DESTINATION_WITHOUT_AUDIT")

    def test_rule_change_and_republished_dependency_schedule_dependents(self):
        audits, targets = completed()
        audits[0]["silver_rule_version"]="agency_v0";targets[("agency",VERSION,HASH)]["rules"]=["agency_v0"]
        result=plan(audits=audits,targets=targets)
        states={r["entity"]:r["status"] for r in result["decisions"]}
        self.assertEqual([states[n] for n in ("agency","routes","trips","frequencies","stop_times")], ["PENDING"]*5)
        audits,targets=completed();audits[0]["started_at_utc"]=STAMP+timedelta(days=1);audits[0]["finished_at_utc"]=STAMP+timedelta(days=1,seconds=1)
        result=plan(audits=audits,targets=targets)
        self.assertEqual(next(r for r in result["decisions"] if r["entity"]=="routes")["reason"],"DEPENDENCY_REPUBLISHED")

    def test_optional_files_and_2025_horizon_are_not_manufactured(self):
        ev=events("2025-10-28");inventory=json.loads(ev[1]["entity_inventory_json"])
        for entity in ("calendar","frequencies","feed_info"):
            inventory[entity].update(source_present=False,source_row_count=None,snapshot_count=0)
        ev[1]["entity_inventory_json"]=json.dumps(inventory)
        result=plan(ev=ev,targets={})
        states={r["entity"]:r["status"] for r in result["decisions"]}
        self.assertEqual(states["calendar"],"NOT_APPLICABLE")
        self.assertEqual(states["calendar_dates"],"PENDING")
        self.assertEqual(states["stop_times"],"PENDING")
        self.assertEqual(states["service_dates"],"OUT_OF_SCOPE")

    def test_window_changes_need_explicit_migration(self):
        audits,targets=completed();targets[("service_dates",VERSION,HASH)]["windows"]=[["2026-02-01","2026-12-31"]]
        result=plan(audits=audits,targets=targets)
        self.assertEqual(next(r for r in result["decisions"] if r["entity"]=="service_dates")["status"],"BLOCKED")

    def test_batch_leaves_work_visible_and_completed_snapshots_do_not_starve_new_ones(self):
        first=events("2025-10-28","b"*64);second=events();third=events("2027-01-01","d"*64)
        audits,targets=completed("2025-10-28","b"*64)
        result=plan(ev=first+second+third,audits=audits,targets=targets,max_snapshots=1)
        self.assertEqual(result["counts"]["PENDING"],10)
        self.assertEqual(result["counts"]["DEFERRED"],9)
        self.assertEqual(result["work_items"]["agency"][0]["feed_version"],VERSION)

    def test_auto_job_preserves_manual_default_and_replaces_all_fixed_lists(self):
        manual=build_job("/Workspace/REPO_ROOT");auto=build_job("/Workspace/REPO_ROOT",selection_mode="auto")
        self.assertEqual(len(manual["tasks"]),10);self.assertEqual(len(auto["tasks"]),11)
        self.assertEqual(auto["tasks"][0]["task_key"],"plan_silver")
        self.assertFalse(any(p["name"].endswith("work_items") for p in auto["parameters"]))
        self.assertNotIn("07ba2ba9",json.dumps(auto))
        for task in auto["tasks"][1:]:
            self.assertIn("tasks.plan_silver.values",task["for_each_task"]["inputs"])
            self.assertEqual(task["for_each_task"]["task"]["notebook_task"]["base_parameters"]["expected_rule_version"],"{{input.expected_rule_version}}")

    def test_budget_and_dependency_cycles_fail_without_silent_truncation(self):
        ev=[]
        for index in range(5):ev+=events(VERSION,format(index+1,"064x"))
        with self.assertRaisesRegex(ValueError,"excede"):
            plan(ev=ev,targets={},max_task_value_bytes=1000)
        registry=load_registry();registry["agency"]["depends_on"]=["routes"]
        with self.assertRaisesRegex(ValueError,"ciclo"):
            build_plan(events(),[],{},registry,POLICY,catalog="spark_catalog",schema="fixture")

    def test_bronze_read_uses_pinned_version_and_skips_latest_history_lookup(self):
        from gtfs_silver.pipeline import _read_bronze
        spark=MagicMock()
        _read_bronze(spark,"spark_catalog.fixture.bronze_gtfs_agency","7")
        spark.read.option.assert_called_once_with("versionAsOf",7)
        spark.sql.assert_not_called()

    def test_recovery_apply_requires_stopped_executions_before_io(self):
        from gtfs_silver.planner_recovery import resolve_attempt
        spark=MagicMock()
        with self.assertRaisesRegex(ValueError,"terminado"):
            resolve_attempt(spark,catalog="spark_catalog",schema="fixture",layer="silver",entity="agency",
                            feed_version=VERSION,sha256=HASH,attempt_run_id="fixture",reason="Fixture sin cierre",
                            mode="apply",executions_stopped=False)
        spark.sql.assert_not_called()

    def test_empty_plan_emits_empty_lists_and_stale_rule_stops_before_reads(self):
        result=plan(ev=[],targets={});dbutils=SimpleNamespace(jobs=SimpleNamespace(taskValues=Mock()))
        emit_plan(dbutils,result)
        values={call.kwargs["key"]:call.kwargs["value"] for call in dbutils.jobs.taskValues.set.call_args_list}
        self.assertEqual(values["work_items"],[]);self.assertEqual(values["plan_status"],"NO_WORK")
        spark=MagicMock()
        with self.assertRaisesRegex(ValueError,"regla cambió"):
            run_entity(spark,catalog="spark_catalog",schema="fixture",staging_volume="staging",entity="agency",
                       feed_version=VERSION,snapshot_sha256=HASH,expected_rule_version="agency_v0")
        spark.sql.assert_not_called()


@unittest.skipUnless(HAS_DELTA,"Requiere Spark y JARs Delta preparados.")
class SilverPlannerDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.temporary=TemporaryDirectory(prefix="gtfs-planner-")
        cls.spark=(SparkSession.builder.master("local[1]").appName("silver-planner-tests")
                   .config("spark.ui.enabled","false").config("spark.sql.shuffle.partitions","1")
                   .config("spark.databricks.delta.snapshotPartitions","1")
                   .config("spark.sql.warehouse.dir",Path(cls.temporary.name).as_uri())
                   .config("spark.jars",os.environ["GTFS_DELTA_TEST_JARS"])
                   .config("spark.sql.extensions","io.delta.sql.DeltaSparkSessionExtension")
                   .config("spark.sql.catalog.spark_catalog","org.apache.spark.sql.delta.catalog.DeltaCatalog").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone","UTC");cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls): cls.spark.stop();cls.temporary.cleanup()

    def setUp(self):
        self.schema="planner_"+uuid4().hex;self.spark.sql(f"create database {self.schema}")
        self.registry={name:cfg for name,cfg in load_registry().items() if name in {"agency","routes"}}
        self.ev=events(schema=self.schema)
        self.closure=f"spark_catalog.{self.schema}.audit_gtfs_bronze_snapshot_runs"
        self.spark.createDataFrame(self.ev,CLOSURE_DDL).write.format("delta").saveAsTable(self.closure)

    def tearDown(self):self.spark.sql(f"drop database {self.schema} cascade")

    def publish_fixture(self,entity="agency",*,mixed_runs=False):
        audits,_=completed(schema=self.schema,names=[entity])
        for audit in audits:
            audit.update(reference_versions_json="{}", identical_copies_consolidated=0, warning_rows=0, error_message=None)
        schema="entity string, source_feed_version string, source_sha256 string, silver_run_id string, status string, silver_rule_version string, target_table string, reference_versions_json string, input_rows long, candidate_rows long, rejected_rows long, identical_copies_consolidated long, warning_rows long, started_at_utc timestamp, finished_at_utc timestamp, silver_committed boolean, error_message string"
        if mixed_runs:audits[0].update(candidate_rows=2,input_rows=2)
        self.spark.createDataFrame(audits,schema).write.format("delta").mode("append").saveAsTable(f"spark_catalog.{self.schema}.audit_gtfs_silver_runs")
        rows=[(VERSION,HASH,entity+"-run",entity+"_v1")]
        if mixed_runs:rows.append((VERSION,HASH,"other-run",entity+"_v1"))
        self.spark.createDataFrame(rows,"source_feed_version string, source_sha256 string, silver_run_id string, silver_rule_version string").write.format("delta").saveAsTable(f"spark_catalog.{self.schema}.silver_gtfs_{entity}")

    def test_reads_metadata_and_target_then_rechecks_latest_bronze(self):
        self.publish_fixture()
        result=create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)
        self.assertEqual(result["counts"]["COMPLETE"],1);self.assertEqual(result["counts"]["PENDING"],1)
        item=result["work_items"]["routes"][0]
        # Ejecuto el notebook completo en vista previa; no tiene efectos de escritura.
        nb=json.loads((ROOT/"databricks/notebooks/silver/11_plan_silver.ipynb").read_text(encoding="utf-8"))
        values={"repo_root":str(ROOT),"catalog":"spark_catalog","schema":self.schema}
        class Widgets:
            def text(self,key,default,*args):values.setdefault(key,default)
            def get(self,key):return values[key]
        dbutils=SimpleNamespace(widgets=Widgets(),jobs=SimpleNamespace(taskValues=Mock()))
        namespace={"spark":self.spark,"dbutils":dbutils,"display":lambda frame:None}
        for cell in nb["cells"]:
            if cell["cell_type"]=="code":exec("".join(cell["source"]),namespace)
        self.assertEqual(namespace["plan"]["status"],"READY")
        dbutils.jobs.taskValues.set.assert_not_called()
        assert_bronze_ready(self.spark,catalog="spark_catalog",schema=self.schema,feed_version=VERSION,sha256=HASH,
                            quality_run_id=item["bronze_quality_run_id"],result_sha256=item["bronze_result_sha256"])
        with self.assertRaisesRegex(RuntimeError,"versión Delta"):
            assert_bronze_ready(self.spark,catalog="spark_catalog",schema=self.schema,feed_version=VERSION,sha256=HASH,
                                quality_run_id=item["bronze_quality_run_id"],result_sha256=item["bronze_result_sha256"],
                                entity="routes",bronze_delta_version="999")
        newer={**self.ev[0],"quality_run_id":"new-attempt","started_at_utc":STAMP+timedelta(days=1)}
        self.spark.createDataFrame([newer],CLOSURE_DDL).write.format("delta").mode("append").saveAsTable(self.closure)
        with self.assertRaisesRegex(RuntimeError,"cierre Bronze cambió"):
            assert_bronze_ready(self.spark,catalog="spark_catalog",schema=self.schema,feed_version=VERSION,sha256=HASH,
                                quality_run_id=item["bronze_quality_run_id"],result_sha256=item["bronze_result_sha256"])
        self.assertEqual(create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)["status"],"BLOCKED")

    def test_mixed_destination_runs_block_and_planning_does_not_write(self):
        self.publish_fixture(mixed_runs=True)
        before=self.spark.sql(f"describe history {self.closure} limit 1").first()["version"]
        result=create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(result["decisions"][0]["reason"],"DESTINATION_DOES_NOT_MATCH_AUDIT")
        self.assertEqual(self.spark.sql(f"describe history {self.closure} limit 1").first()["version"],before)

    def test_preparation_failure_is_audited_and_cannot_hide_behind_previous_success(self):
        self.publish_fixture()
        from gtfs_silver import pipeline
        with patch.object(pipeline,"_run_entity",side_effect=ValueError("fixture preparation failed")):
            with self.assertRaisesRegex(ValueError,"fixture preparation failed"):
                pipeline.run_entity(self.spark,catalog="spark_catalog",schema=self.schema,staging_volume="staging",
                                    entity="agency",feed_version=VERSION,snapshot_sha256=HASH,
                                    expected_rule_version="agency_v1",bronze_quality_run_id=self.ev[1]["quality_run_id"],
                                    bronze_result_sha256=self.ev[1]["result_sha256"],bronze_delta_version="2")
        result=create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)
        self.assertEqual(result["decisions"][0]["reason"],"LATEST_SILVER_ATTEMPT_NOT_SUCCESSFUL")

    def test_frozen_bronze_read_excludes_later_append(self):
        from gtfs_silver.pipeline import _read_bronze
        table=f"spark_catalog.{self.schema}.bronze_gtfs_agency"
        frame=self.spark.createDataFrame([("A",)],"agency_id string")
        frame.write.format("delta").saveAsTable(table)
        version=str(self.spark.sql(f"describe history {table} limit 1").first()["version"])
        frame.write.format("delta").mode("append").saveAsTable(table)
        self.assertEqual(_read_bronze(self.spark,table,version).count(),1)
        self.assertEqual(self.spark.table(table).count(),2)

    def test_invalid_bronze_pair_resolution_keeps_evidence_and_expires_on_close(self):
        from gtfs_silver.planner_recovery import resolve_attempt
        first=events("2025-10-28",HASH,schema=self.schema)
        second=events(VERSION,"b"*64,schema=self.schema)
        wrong={**first[0],"quality_run_id":"invalid-version-pair","source_feed_version":VERSION,
               "started_at_utc":STAMP+timedelta(hours=1)}
        self.spark.createDataFrame(first+second+[wrong],CLOSURE_DDL).write.format("delta").mode("overwrite").saveAsTable(self.closure)
        args=dict(catalog="spark_catalog",schema=self.schema,layer="bronze",entity="*",feed_version=VERSION,
                  sha256=HASH,attempt_run_id=wrong["quality_run_id"],reason="Identidad incorrecta; sin ejecución activa.")
        resolution_table=f"spark_catalog.{self.schema}.audit_gtfs_attempt_resolutions"
        # Compruebo el notebook manual completo en preview.
        nb=json.loads((ROOT/"databricks/notebooks/silver/18_recover_pipeline_attempts.ipynb").read_text(encoding="utf-8"))
        values={"repo_root":str(ROOT),"catalog":"spark_catalog","schema":self.schema,
                "resolutions_json":json.dumps([{k:v for k,v in args.items() if k not in {"catalog","schema"}}])}
        class Widgets:
            def text(self,key,default,*unused):values.setdefault(key,default)
            def get(self,key):return values[key]
        namespace={"spark":self.spark,"dbutils":SimpleNamespace(widgets=Widgets())}
        for cell in nb["cells"]:
            if cell["cell_type"]=="code":exec("".join(cell["source"]),namespace)
        self.assertFalse(self.spark.catalog.tableExists(resolution_table))
        for _ in range(2):resolve_attempt(self.spark,**args,mode="apply",executions_stopped=True)
        self.assertEqual(self.spark.table(resolution_table).count(),1)
        self.assertEqual(self.spark.table(self.closure).count(),5)
        result=create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)
        self.assertEqual(result["status"],"READY");self.assertEqual(result["counts"]["RESOLVED"],1)
        closed={**wrong,"event_type":"CLOSED","status":"FAILED","blocking_failures":1,"total_checks":1,
                "validation_completed":True,"ready_for_silver":False,"completed_at_utc":STAMP+timedelta(hours=2)}
        self.spark.createDataFrame([closed],CLOSURE_DDL).write.format("delta").mode("append").saveAsTable(self.closure)
        self.assertEqual(create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)["status"],"BLOCKED")

    def test_silver_resolution_preserves_previous_publication_and_expires_on_change(self):
        from gtfs_silver.planner_recovery import resolve_attempt
        self.publish_fixture()
        audit_table=f"spark_catalog.{self.schema}.audit_gtfs_silver_runs"
        old,_=completed(schema=self.schema,names=["agency"])
        running={**old[0],"silver_run_id":"abandoned-agency","status":"RUNNING","silver_committed":False,
                 "started_at_utc":STAMP+timedelta(days=1),"finished_at_utc":None}
        self.spark.createDataFrame([running],self.spark.table(audit_table).schema).write.format("delta").mode("append").saveAsTable(audit_table)
        args=dict(catalog="spark_catalog",schema=self.schema,layer="silver",entity="agency",feed_version=VERSION,
                  sha256=HASH,attempt_run_id="abandoned-agency",reason="Sin ejecución activa; destino anterior verificado.")
        preview=resolve_attempt(self.spark,**args)
        self.assertFalse(preview["persisted"]);self.assertEqual(preview["evidence"]["verified_rows"],1)
        resolve_attempt(self.spark,**args,mode="apply",executions_stopped=True)
        result=create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)
        self.assertEqual(result["decisions"][0]["status"],"COMPLETE")
        self.assertEqual(result["counts"]["RESOLVED"],1)
        rows=self.spark.table(f"spark_catalog.{self.schema}.silver_gtfs_agency").collect()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["silver_run_id"],"agency-run")
        self.assertEqual(self.spark.table(audit_table).filter("silver_run_id='abandoned-agency'").first()["status"],"RUNNING")
        self.spark.sql(f"update {audit_table} set status='FAILED', finished_at_utc=current_timestamp() where silver_run_id='abandoned-agency'")
        result=create_plan(self.spark,catalog="spark_catalog",schema=self.schema,registry=self.registry)
        self.assertEqual(result["status"],"BLOCKED");self.assertEqual(result["counts"]["RESOLVED"],0)
