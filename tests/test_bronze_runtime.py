"""Casos de recuperación y cierre Bronze con archivos pequeños y Spark opcional."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "databricks"))
from gtfs_bronze.contracts import (
    CHECK_FIELDS, ENTITY_NAMES, RULE_VERSION, build_closure, expected_check_keys, load_decision,
)
from gtfs_bronze.runtime import (
    download_response, extract_verified, load_frame, persist_closure, preserve_raw,
    publish_task_values, read_gtfs_header, source_frame, start_validation,
)
from notebook_test_support import LocalVolume, SparkDouble, cell_source, spark_type_stubs

STAMP = datetime(2026, 11, 12, tzinfo=timezone.utc)
VERSION = "2026-09-29"
HASH = "a" * 64
HAS_DELTA = bool(importlib.util.find_spec("pyspark") and os.environ.get("GTFS_DELTA_TEST_JARS") and shutil.which("java"))


def evaluation():
    entities = {name: {
        "source_present": True, "snapshot_count": 1, "source_row_count": 1,
        "table_exists": True, "table_name": f"spark_catalog.fixture.bronze_{name}",
        "delta_version": 3, "bronze_columns": ["fixture"], "schema_check_severity": "INFO",
    } for name in ENTITY_NAMES}
    keys = expected_check_keys(entities, {})
    checks = [("run", STAMP, VERSION, HASH, name, "fixture", entity, severity, "PASS", "1", "1", "fixture")
              for name, entity, severity in sorted(keys)]
    return checks, entities


def close(rows, entities, **kwargs):
    return build_closure(rows, entities, {}, {"presence", "identifiers", "schema"},
                         run_id="run", feed_version=VERSION, sha256=HASH, started_at=STAMP, **kwargs)


class BronzeClosureTests(unittest.TestCase):
    def test_complete_evaluation_consolidates_identical_checks_and_keeps_stable_fingerprint(self):
        rows, entities = evaluation()
        checks, result = close(rows + rows[:1], entities)
        self.assertEqual(len(checks), len(rows))
        self.assertTrue(result["ready_for_silver"])
        self.assertEqual(result["event_type"], "CLOSED")
        self.assertEqual(result["result_sha256"], close(list(reversed(rows)), entities)[1]["result_sha256"])

    def test_missing_block_missing_check_and_wrong_identity_cannot_close(self):
        rows, entities = evaluation()
        with self.assertRaisesRegex(RuntimeError, "incompletos"):
            close(rows[:-1], entities)
        with self.assertRaisesRegex(RuntimeError, "incompleta"):
            build_closure(rows, entities, {}, {"presence"}, run_id="run", feed_version=VERSION, sha256=HASH, started_at=STAMP)
        bad = list(rows[0]); bad[3] = "b" * 64
        with self.assertRaisesRegex(ValueError, "otra corrida"):
            close([tuple(bad)] + rows[1:], entities)
        entities["routes"]["delta_version"] = None
        with self.assertRaisesRegex(RuntimeError, "Delta"):
            close(rows, entities)

    def test_conflicting_checks_are_rejected(self):
        rows, entities = evaluation()
        bad = list(rows[0]); bad[9] = "different"
        with self.assertRaisesRegex(ValueError, "contradictorio"):
            close(rows + [tuple(bad)], entities)

    def test_warning_is_recorded_and_blocking_failure_prevents_silver(self):
        rows, entities = evaluation()
        warning = list(next(row for row in rows if row[7] == "WARNING")); warning[8] = "WARN"
        rows = [tuple(warning) if r[4] == warning[4] else r for r in rows]
        _, summary = close(rows, entities)
        self.assertEqual((summary["status"], summary["warning_count"], summary["warning_policy"]), ("WARNING", 1, "silver_contracts_v1"))
        self.assertTrue(summary["ready_for_silver"])
        bad = list(next(row for row in rows if row[7] == "BLOCKING")); bad[8] = "FAIL"
        rows = [tuple(bad) if r[4:8] == tuple(bad[4:8]) else r for r in rows]
        _, summary = close(rows, entities)
        self.assertEqual(summary["status"], "FAILED")
        self.assertFalse(summary["ready_for_silver"])

    def test_partial_load_wrong_identity_and_empty_source_never_append(self):
        self.assertFalse(load_decision(2, 0, 0))
        self.assertTrue(load_decision(2, 2, 0))
        for source, loaded, wrong in [(2, 1, 0), (2, 3, 0), (2, 2, 1), (0, 0, 0)]:
            with self.subTest(source=source, loaded=loaded, wrong=wrong), self.assertRaises(RuntimeError):
                load_decision(source, loaded, wrong)

    def test_required_task_values_failure_is_not_silenced(self):
        dbutils = SimpleNamespace(jobs=SimpleNamespace(taskValues=Mock()))
        dbutils.jobs.taskValues.set.side_effect = RuntimeError("fixture")
        with self.assertRaisesRegex(RuntimeError, "task values"):
            publish_task_values(dbutils, {"feed_version": VERSION}, required=True)


class BronzeFileTests(unittest.TestCase):
    def test_optional_routes_diagnostic_accepts_history_without_route_desc(self):
        spark = SparkDouble({"spark_catalog.fixture.bronze_routes": [{"route_id": "R"}]})
        namespace = {"spark": spark, "show_diagnostics": True, "display": lambda frame: None,
                     "bronze_routes_table": "spark_catalog.fixture.bronze_routes",
                     "routes_source_df": spark.table("spark_catalog.fixture.bronze_routes")}
        with spark_type_stubs():
            exec(cell_source("03_bronze_static_gtfs.ipynb", "BLOQUE 4A —"), namespace)

    def test_raw_retry_checks_content_and_never_overwrites_corruption(self):
        content = b"fixture bytes"; digest = hashlib.sha256(content).hexdigest()
        with TemporaryDirectory() as temporary:
            path = Path(temporary, "gtfs.zip")
            self.assertFalse(preserve_raw(str(path), content, digest))
            self.assertTrue(preserve_raw(str(path), content, digest))
            path.write_bytes(b"interrupted")
            with self.assertRaisesRegex(RuntimeError, "no coincide"):
                preserve_raw(str(path), content, digest)
            self.assertEqual(path.read_bytes(), b"interrupted")

    def test_staging_retry_detects_same_size_content_change(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("nested/stops.txt", b"stop_id\nA\n")
        with TemporaryDirectory() as temporary, zipfile.ZipFile(buffer) as archive:
            member = archive.infolist()[0]; path = Path(temporary, "stops.txt")
            self.assertFalse(extract_verified(archive, member, str(path)))
            self.assertTrue(extract_verified(archive, member, str(path)))
            path.write_bytes(b"stop_id\nB\n")
            with self.assertRaisesRegex(RuntimeError, "Staging inconsistente"):
                extract_verified(archive, member, str(path))
            self.assertEqual(path.read_bytes(), b"stop_id\nB\n")

    def test_header_cannot_override_technical_provenance(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary, "routes.txt")
            path.write_text("route_id,source_sha256\na,evil\n")
            with self.assertRaisesRegex(RuntimeError, "reservados"):
                read_gtfs_header(str(path))

    def test_download_retries_temporary_http_and_network_but_not_404(self):
        response = Mock(status_code=200)
        transient = Mock(status_code=503)
        getter = Mock(side_effect=[TimeoutError(), transient, response]); sleep = Mock()
        self.assertIs(download_response("https://example.invalid/fixture", getter, sleep=sleep), response)
        self.assertEqual(getter.call_count, 3)
        transient.close.assert_called_once()
        missing = Mock(status_code=404); missing.raise_for_status.side_effect = RuntimeError("404")
        getter = Mock(return_value=missing)
        with self.assertRaisesRegex(RuntimeError, "404"):
            download_response("https://example.invalid/fixture", getter, sleep=sleep)
        self.assertEqual(getter.call_count, 1)


@unittest.skipUnless(HAS_DELTA, "Requiere Spark, Java y JARs Delta locales.")
class BronzeDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.temporary = TemporaryDirectory(prefix="gtfs-bronze-")
        cls.spark = (SparkSession.builder.master("local[1]").appName("bronze-recovery-tests")
                     .config("spark.ui.enabled", "false").config("spark.sql.shuffle.partitions", "1")
                     .config("spark.databricks.delta.snapshotPartitions", "1")
                     .config("spark.sql.warehouse.dir", Path(cls.temporary.name).as_uri())
                     .config("spark.jars", os.environ["GTFS_DELTA_TEST_JARS"])
                     .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                     .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
                     .getOrCreate())
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop(); cls.temporary.cleanup()

    def setUp(self):
        self.schema = "bronze_" + uuid4().hex
        self.spark.sql(f"create database {self.schema}")

    def tearDown(self):
        self.spark.sql(f"drop database {self.schema} cascade")

    def test_loader_preserves_history_and_blocks_alias_and_partial_append(self):
        table = f"spark_catalog.{self.schema}.bronze_routes"
        source = self.spark.createDataFrame([("r",)], "route_id string")
        args = dict(table=table, source_path="/fixture/routes.txt", feed_version="2025-10-28", sha256=HASH)
        self.assertEqual(load_frame(self.spark, source, **args), (1, False))
        self.assertEqual(load_frame(self.spark, source, **args), (1, True))
        with self.assertRaisesRegex(RuntimeError, "otra versión"):
            load_frame(self.spark, source, **{**args, "feed_version": VERSION})
        self.assertEqual(load_frame(self.spark, source, **{**args, "feed_version": VERSION, "sha256": "b" * 64}), (1, False))
        self.assertEqual(self.spark.table(table).count(), 2)
        with self.assertRaisesRegex(RuntimeError, "inconsistente"):
            load_frame(self.spark, source.unionByName(source), **args)
        self.assertEqual(self.spark.table(table).count(), 2)

    def test_terminal_audit_retry_and_conflict(self):
        rows, entities = evaluation(); rows, summary = close(rows, entities)
        quality = f"spark_catalog.{self.schema}.quality"; closure = f"spark_catalog.{self.schema}.runs"
        start_validation(self.spark, closure_table=closure, run_id="run", feed_version=VERSION, sha256=HASH, started_at=STAMP)
        for _ in range(2):
            persist_closure(self.spark, rows, summary, quality_table=quality, closure_table=closure)
        self.assertEqual(self.spark.table(quality).count(), len(rows))
        self.assertEqual(self.spark.table(closure).count(), 2)
        bad = list(rows[0]); bad[-1] = "changed"
        with self.assertRaisesRegex(RuntimeError, "otro resultado"):
            persist_closure(self.spark, [tuple(bad)] + rows[1:], summary, quality_table=quality, closure_table=closure)
        self.assertEqual(self.spark.table(closure).count(), 2)

    def test_notebook07_complete_then_partial_execution_cannot_close(self):
        files = {
            "agency.txt": "agency_id\nA\n", "routes.txt": "route_id\nR\n",
            "stops.txt": "stop_id\nS\n", "trips.txt": "trip_id,route_id,service_id\nT,R,W\n",
            "calendar_dates.txt": "service_id,date,exception_type\nW,20260101,1\n",
            "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nG,4.6,-74,1\n",
            "stop_times.txt": "trip_id,stop_id,stop_sequence\nT,S,1\n",
        }
        with TemporaryDirectory() as temporary:
            staging = Path(temporary, "gtfs_static", f"feed_version={VERSION}", f"sha256={HASH}")
            staging.mkdir(parents=True)
            for name, text in files.items():
                path = staging / name; path.write_text(text, encoding="utf-8")
                load_frame(self.spark, source_frame(self.spark, str(path), read_gtfs_header(str(path))),
                           table=f"spark_catalog.{self.schema}.bronze_gtfs_{name[:-4]}",
                           source_path=str(path), feed_version=VERSION, sha256=HASH)
            widgets = {"catalog": "spark_catalog", "schema": self.schema, "repo_root": str(ROOT), "feed_version": VERSION, "snapshot_sha256": HASH}
            class Widgets:
                def text(self, key, default, *args): widgets.setdefault(key, default)
                def get(self, key): return widgets[key]
            dbutils = SimpleNamespace(widgets=Widgets(), fs=LocalVolume(), jobs=SimpleNamespace(taskValues=Mock()))
            ns = {"spark": self.spark, "dbutils": dbutils, "display": lambda frame: None}
            notebook = "07_validate_bronze_gtfs_snapshot.ipynb"
            blocks = [cell_source(notebook, f"BLOQUE {i} —") for i in range(1, 8)]
            exec(blocks[0], ns)
            ns["staging_snapshot_path"] = str(staging)
            for source in blocks[1:]: exec(source, ns)
            self.assertTrue(ns["closure"]["ready_for_silver"])
            self.assertEqual(ns["closure"]["status"], "PASSED")
            count = self.spark.table(ns["quality_audit_table"]).count()
            exec(blocks[6], ns)
            self.assertEqual(self.spark.table(ns["quality_audit_table"]).count(), count)
            exec(blocks[4], ns)
            with self.assertRaisesRegex(RuntimeError, "incompleta"):
                exec(blocks[6], ns)
            self.assertEqual(self.spark.table(ns["closure_audit_table"]).count(), 2)
