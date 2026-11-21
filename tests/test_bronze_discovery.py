"""Catálogo, selección y recuperación con fixtures; sin consultas reales al proveedor."""
from copy import deepcopy
from datetime import timedelta
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "databricks"))
from gtfs_bronze.discovery import build_ingestion_plan, fetch_catalog, normalize_catalog, validate_selection
from gtfs_bronze.discovery_runtime import create_ingestion_plan, emit_ingestion_plan
from gtfs_bronze.runtime import CLOSURE_DDL
from test_silver_planner import events, STAMP, VERSION, HASH

HAS_DELTA = bool(importlib.util.find_spec("pyspark") and os.environ.get("GTFS_DELTA_TEST_JARS") and shutil.which("java"))


def catalog_row(version=VERSION, **updates):
    return {"feed_version": version, "portal_item_id": "item-" + version,
            "source_url": "https://example.invalid/" + version + ".zip", "is_direct_zip_url": True,
            "portal_modified_at_utc": STAMP - timedelta(days=1), **updates}


class DiscoveryTests(unittest.TestCase):
    def test_complete_and_warning_are_no_work(self):
        for status in ("PASSED", "WARNING"):
            ev = events(); ev[-1]["status"] = status
            result = build_ingestion_plan([catalog_row()], ev)
            self.assertEqual(result["status"], "NO_WORK")
            self.assertEqual(result["work_items"], [])

    def test_range_is_bounded_oldest_first_and_bootstrap_needs_no_tables(self):
        rows = [catalog_row("2026-09-29"), catalog_row("2026-05-01"), catalog_row("2025-01-01")]
        result = build_ingestion_plan(rows, [], selection_mode="backfill_range", start_date="2026-01-01",
                                      end_date="2026-12-31", max_versions=1)
        self.assertEqual(result["work_items"], [{"feed_version": "2026-05-01"}])
        self.assertEqual(result["counts"]["DEFERRED"], 1)
        self.assertEqual(len(result["decisions"]), 2)

    def test_latest_is_one_newest_pending(self):
        result = build_ingestion_plan([catalog_row("2026-05-01"), catalog_row()], [], max_versions=20)
        self.assertEqual(result["work_items"], [{"feed_version": VERSION}])
        self.assertEqual(result["counts"]["DEFERRED"], 1)

    def test_completed_versions_do_not_consume_pending_budget(self):
        result = build_ingestion_plan([catalog_row(), catalog_row("2026-10-01")], events())
        self.assertEqual(result["work_items"], [{"feed_version": "2026-10-01"}])

    def test_latest_attempt_blocks_even_after_previous_success(self):
        ev = events()
        ev.append({**ev[0], "quality_run_id": "later", "started_at_utc": STAMP + timedelta(days=1)})
        result = build_ingestion_plan([catalog_row()], ev)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["decisions"][0]["reason"], "INCOMPLETE_BRONZE_ATTEMPT")

    def test_failed_or_invalid_inventory_blocks(self):
        for change in ({"status": "FAILED", "ready_for_silver": False}, {"entity_inventory_json": "{}"}):
            ev = events(); ev[-1].update(change)
            self.assertEqual(build_ingestion_plan([catalog_row()], ev)["status"], "BLOCKED")

    def test_orphan_provenance_never_counts_as_ready_or_fresh(self):
        result = build_ingestion_plan([catalog_row()], [], observed_versions={VERSION})
        self.assertEqual(result["decisions"][0]["reason"], "BRONZE_EVIDENCE_WITHOUT_VALID_CLOSURE")
        self.assertEqual(result["work_items"], [])

    def test_explicit_complete_requires_reprocess_option_and_keeps_guards(self):
        args = dict(selection_mode="explicit_version", explicit_version=VERSION)
        self.assertEqual(build_ingestion_plan([catalog_row()], events(), **args)["status"], "NO_WORK")
        result = build_ingestion_plan([catalog_row()], events(), reprocess_completed=True, **args)
        self.assertEqual(result["work_items"], [{"feed_version": VERSION}])
        self.assertEqual(result["decisions"][0]["reason"], "EXPLICIT_REPROCESS")
        self.assertEqual(build_ingestion_plan([catalog_row()], events()[:1], reprocess_completed=True, **args)["status"], "BLOCKED")

    def test_newer_portal_metadata_requests_hash_recheck(self):
        result = build_ingestion_plan([catalog_row(portal_modified_at_utc=STAMP + timedelta(days=1))], events())
        self.assertEqual(result["decisions"][0]["reason"], "PORTAL_METADATA_NEWER_THAN_CLOSURE")
        self.assertEqual(result["status"], "READY")

    def test_ambiguous_or_unresolved_url_blocks_and_hash_is_absent(self):
        result = build_ingestion_plan([catalog_row(), catalog_row(source_url="https://example.invalid/other.zip")], [])
        self.assertEqual(result["decisions"][0]["reason"], "AMBIGUOUS_SOURCE_URL")
        self.assertEqual(build_ingestion_plan([catalog_row(is_direct_zip_url=False)], [])["status"], "BLOCKED")
        self.assertNotIn("snapshot_sha256", build_ingestion_plan([catalog_row()], [])["work_items"][0])

    def test_invalid_inputs_fail_and_explicit_missing_is_not_no_work(self):
        cases = [{"selection_mode": "unknown"}, {"max_versions": 0}, {"max_versions": True},
                 {"selection_mode": "backfill_range"}, {"start_date": "2026-01-01"},
                 {"start_date": "2026-02-30", "end_date": "2026-03-01"},
                 {"selection_mode": "explicit_version", "explicit_version": "2026-9-29"},
                 {"start_date": "2026-02-01", "end_date": "2026-01-01"}, {"reprocess_completed": True}]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                validate_selection(**{"selection_mode": "latest_uningested", **kwargs})
        with self.assertRaisesRegex(ValueError, "no existe"):
            build_ingestion_plan([], [], selection_mode="explicit_version", explicit_version=VERSION)

    def test_emit_no_work_and_blocked_without_publishing_lists(self):
        values = Mock(); utils = SimpleNamespace(jobs=SimpleNamespace(taskValues=values))
        emit_ingestion_plan(utils, build_ingestion_plan([catalog_row()], events()))
        self.assertIn(unittest.mock.call(key="ingestion_work_items", value=[]), values.set.call_args_list)
        values.reset_mock()
        with self.assertRaises(RuntimeError):
            emit_ingestion_plan(utils, build_ingestion_plan([catalog_row()], events()[:1]))
        values.set.assert_not_called()

    def response(self, results, next_start=-1, status=200):
        response = Mock(status_code=status)
        response.json.return_value = {"results": results, "nextStart": next_start}
        return response

    def test_pagination_and_transient_retry_preserve_page(self):
        get = Mock(side_effect=[self.response([], status=503), self.response([{"id": "a"}], 101),
                                self.response([{"id": "b"}])])
        sleep = Mock()
        self.assertEqual(len(fetch_catalog("https://example.invalid", get, sleep=sleep)), 2)
        self.assertEqual([c.kwargs["params"]["start"] for c in get.call_args_list], [1, 1, 101])
        sleep.assert_called_once_with(1)

    def test_bad_pagination_errors_limits_and_empty_catalog_fail(self):
        cases = [self.response([], 1), self.response([], True), self.response([], None), self.response([]),
                 self.response([{}, {}])]
        for response in cases:
            with self.subTest(response=response), self.assertRaises((ValueError, RuntimeError)):
                fetch_catalog("https://example.invalid", Mock(return_value=response), max_items=1)
        with self.assertRaisesRegex(RuntimeError, "max_pages"):
            fetch_catalog("https://example.invalid", Mock(return_value=self.response([{}], 101)), max_pages=1)
        response = self.response([]); response.json.return_value = {"error": {"message": "denied"}}
        with self.assertRaises(RuntimeError):
            fetch_catalog("https://example.invalid", Mock(return_value=response))

    def test_normalization_consolidates_duplicates_and_rejects_conflicts(self):
        item = {"id": "fixture", "title": "GTFS Estáticos " + VERSION,
                "url": "https://example.invalid/feed.ZIP?download=1", "modified": 1000}
        args = dict(group_id="fixture", run_id="fixture", discovered_at=STAMP)
        rows = normalize_catalog([item, deepcopy(item), {"title": "otro"}], **args)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["is_direct_zip_url"])
        with self.assertRaisesRegex(ValueError, "contradictoria"):
            normalize_catalog([item, {**item, "url": "https://example.invalid/other.zip"}], **args)
        with self.assertRaises(ValueError):
            normalize_catalog([{**item, "title": "GTFS Estaticos 2026-02-30"}], **args)
        for url in ("ftp://example.invalid/f.zip", "https://user:secret@example.invalid/f.zip", "https://example.invalid/page"):
            self.assertFalse(normalize_catalog([{**item, "url": url}], **args)[0]["is_direct_zip_url"])


@unittest.skipUnless(HAS_DELTA, "Requiere Spark/Delta offline configurados.")
class DiscoveryDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.temporary = TemporaryDirectory(prefix="gtfs-discovery-")
        cls.spark = (SparkSession.builder.master("local[1]").appName("discovery-tests")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1")
                     .config("spark.databricks.delta.snapshotPartitions", "1")
                     .config("spark.sql.warehouse.dir", Path(cls.temporary.name).as_uri())
                     .config("spark.jars", os.environ["GTFS_DELTA_TEST_JARS"])
                     .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                     .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog").getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop(); cls.temporary.cleanup()

    def setUp(self):
        self.schema = "discovery_" + uuid4().hex
        self.spark.sql(f"create database {self.schema}")
        self.control = f"spark_catalog.{self.schema}.control_gtfs_static_catalog"
        self.spark.createDataFrame([catalog_row()]).write.format("delta").saveAsTable(self.control)
        self.args = dict(catalog="spark_catalog", schema=self.schema)

    def tearDown(self):
        self.spark.sql(f"drop database {self.schema} cascade")

    def test_bootstrap_and_orphan_outside_routes(self):
        self.assertEqual(create_ingestion_plan(self.spark, **self.args)["status"], "READY")
        self.spark.createDataFrame([(VERSION,)], "source_feed_version string").write.format("delta").saveAsTable(
            f"spark_catalog.{self.schema}.bronze_gtfs_stops")
        result = create_ingestion_plan(self.spark, **self.args)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["decisions"][0]["reason"], "BRONZE_EVIDENCE_WITHOUT_VALID_CLOSURE")

    def test_complete_then_incomplete_and_metadata_cap(self):
        table = f"spark_catalog.{self.schema}.audit_gtfs_bronze_snapshot_runs"
        ev = events(schema=self.schema)
        self.spark.createDataFrame(ev, CLOSURE_DDL).write.format("delta").saveAsTable(table)
        self.assertEqual(create_ingestion_plan(self.spark, **self.args)["status"], "NO_WORK")
        self.spark.createDataFrame([{**ev[0], "quality_run_id": "later", "started_at_utc": STAMP + timedelta(days=1)}], CLOSURE_DDL).write.format("delta").mode("append").saveAsTable(table)
        self.assertEqual(create_ingestion_plan(self.spark, **self.args)["status"], "BLOCKED")
        self.spark.createDataFrame([catalog_row("2026-10-01")]).write.format("delta").mode("append").saveAsTable(self.control)
        with self.assertRaisesRegex(ValueError, "no se truncó"):
            create_ingestion_plan(self.spark, max_metadata_rows=1, **self.args)

    def test_notebook_runs_all_blocks_with_fake_http_and_no_task_values(self):
        from notebook_test_support import cell_source
        from unittest.mock import patch
        item = {"id": "fixture", "title": "GTFS Estáticos " + VERSION,
                "url": "https://example.invalid/feed.zip", "modified": 1000}
        values = {"repo_root": str(ROOT), **self.args}
        widgets = SimpleNamespace(text=lambda k,d,*a: values.setdefault(k,d),
                                  dropdown=lambda k,d,*a: values.setdefault(k,d), get=lambda k: values[k])
        task_values = Mock()
        namespace = {"spark": self.spark, "display": lambda f: None,
                     "dbutils": SimpleNamespace(widgets=widgets, jobs=SimpleNamespace(taskValues=task_values))}
        notebook = "06_discover_static_gtfs_catalog.ipynb"
        # Uso un catálogo nuevo para conservar su esquema histórico completo.
        self.spark.sql(f"drop table {self.control}")
        http = SimpleNamespace(get=Mock(return_value=self.response_for_item(item)), ConnectionError=ConnectionError, Timeout=TimeoutError)
        with patch.dict(sys.modules, {"requests": http}):
            for number in range(1, 7):
                exec(cell_source(notebook, f"BLOQUE {number} —"), namespace)
        self.assertEqual(namespace["plan"]["status"], "READY")
        task_values.set.assert_not_called()
        self.assertEqual(self.spark.table(self.control).count(), 1)
        self.assertEqual(self.spark.table(f"spark_catalog.{self.schema}.audit_gtfs_static_catalog_observations").count(), 1)
        values["emit_task_values"] = "true"
        with patch.dict(sys.modules, {"requests": http}):
            for number in range(1, 7):
                exec(cell_source(notebook, f"BLOQUE {number} —"), namespace)
        self.assertEqual(self.spark.table(self.control).count(), 1)
        self.assertEqual(self.spark.table(f"spark_catalog.{self.schema}.audit_gtfs_static_catalog_observations").count(), 2)
        self.assertIn(unittest.mock.call(key="ingestion_work_items", value=[{"feed_version": VERSION}]), task_values.set.call_args_list)

    def response_for_item(self, item):
        response = Mock(status_code=200)
        response.json.return_value = {"results": [item], "nextStart": -1}
        return response
