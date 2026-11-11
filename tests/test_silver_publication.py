"""Pruebas del Job y de publicación; Delta nativo solo con JARs locales explícitos."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory, gettempdir
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "databricks"))
from gtfs_silver.agency_validation import BUSINESS_FIELDS, SnapshotSpec, validate_snapshot
from gtfs_silver.job_config import build_job
from gtfs_silver.pipeline import load_registry
from gtfs_silver.publication import (
    PublicationTables, SnapshotRejectedError, _check_result, _overwrite_scope,
    publish_agency, quoted_table, snapshot_predicate,
)

COLUMNS = BUSINESS_FIELDS[:6]
HAS_DELTA = (importlib.util.find_spec("pyspark") is not None
             and bool(os.environ.get("GTFS_DELTA_TEST_JARS"))
             and shutil.which("java") is not None)


def spec(version="2025-10-28", content_hash="a" * 64):
    return SnapshotSpec(version, content_hash, f"/fixture/{version}/{content_hash}/agency.txt")


def data(selected, count=7):
    return [{
        "agency_id": str(index), "agency_name": f"{selected.feed_version} Marca {index}",
        "agency_url": "https://example.org/", "agency_timezone": "America/Bogota",
        "agency_lang": "es", "agency_phone": "+57 601 123",
        "source_feed_version": selected.feed_version, "source_sha256": selected.sha256,
        "source_file_path": selected.source_path,
        "bronze_loaded_at_utc": datetime(2026, 1, 1, tzinfo=timezone.utc),
    } for index in range(1, count + 1)]


class SilverConfigurationTests(unittest.TestCase):
    def test_job_reuses_one_notebook_with_serial_snapshots_and_no_schedule(self):
        job = build_job("/Workspace/Shared/example-project")
        self.assertEqual(job["max_concurrent_runs"], 1)
        self.assertNotIn("schedule", job)
        loop = job["tasks"][0]["for_each_task"]
        self.assertEqual(loop["concurrency"], 1)
        self.assertEqual(loop["inputs"], "{{job.parameters.work_items}}")
        self.assertNotIn("existing_cluster_id", loop["task"])
        self.assertEqual(loop["task"]["environment_key"], "silver")
        parameters = {item["name"]: item["default"] for item in job["parameters"]}
        items = json.loads(parameters["work_items"])
        self.assertEqual([item["feed_version"] for item in items], ["2025-10-28", "2026-09-29"])
        self.assertEqual(loop["task"]["notebook_task"]["base_parameters"]["entity"], "{{input.entity}}")
        self.assertEqual(parameters["mode"], "publish")

    def test_job_dependencies_match_production_requirements_and_exclude_pyspark(self):
        dependencies = build_job("/Workspace/Shared/example-project")["environments"][0]["spec"]["dependencies"]
        expected = [line for line in (ROOT / "databricks/requirements-silver.txt").read_text().splitlines()
                    if line and not line.startswith("#")]
        self.assertEqual(dependencies, expected)
        self.assertFalse(any("pyspark" in item or "delta-spark" in item for item in dependencies))

    def test_rejects_unsafe_workspace_paths_and_identifiers(self):
        for value in ("relative", "/Workspace/../other", "/Workspace/project\nother"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_job(value)
        for value in ("workspace.schema", "bronze;drop", "../x"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PublicationTables(value, "schema")
        with self.assertRaises(ValueError):
            quoted_table("schema.table")

    def test_targets_are_derived_and_cannot_be_bronze(self):
        tables = PublicationTables("workspace", "gtfs_bogota")
        self.assertEqual(tables.name("silver"), "workspace.gtfs_bogota.silver_gtfs_agency")
        self.assertNotEqual(tables.name("quarantine"), tables.name("silver"))
        self.assertIn("source_sha256", snapshot_predicate(spec()))

    def test_only_implemented_entity_is_enabled(self):
        registry = load_registry()
        self.assertEqual(list(registry), ["agency", "routes", "stops"])
        self.assertTrue(registry["agency"]["enabled"])
        self.assertEqual(registry["agency"]["depends_on"], [])
        self.assertEqual(registry["routes"]["depends_on"], ["agency"])
        self.assertEqual(registry["routes"]["validator"], "routes_v1")
        job = build_job("/Workspace/Shared/example-project")
        routes = job["tasks"][1]
        self.assertEqual(routes["depends_on"], [{"task_key": "publish_snapshots"}])
        self.assertEqual(routes["for_each_task"]["concurrency"], 1)
        self.assertEqual(routes["for_each_task"]["inputs"], "{{job.parameters.routes_work_items}}")
        self.assertEqual(registry["stops"]["depends_on"], [])
        self.assertEqual(registry["stops"]["validator"], "stops_v1")
        stops = job["tasks"][2]
        self.assertEqual(stops["depends_on"], [{"task_key": "publish_routes"}])
        self.assertEqual(stops["for_each_task"]["inputs"], "{{job.parameters.stops_work_items}}")
        parameters = {p["name"]: p["default"] for p in job["parameters"]}
        self.assertEqual([i["entity"] for i in json.loads(parameters["stops_work_items"])], ["stops", "stops"])


    def test_false_reconciliation_is_rejected_before_any_write(self):
        result = validate_snapshot(data(spec()), COLUMNS, spec())
        modified = deepcopy(result)
        modified.summary["input_rows"] = 99
        with self.assertRaises(ValueError):
            _check_result(modified)

    def test_preview_is_read_only_without_a_spark_session(self):
        selected = spec()
        result = validate_snapshot(data(selected), COLUMNS, selected)
        output = publish_agency(None, result, selected, PublicationTables("workspace", "test"), mode="validate")
        self.assertFalse(output["persisted"])
        self.assertEqual(output["status"], "VALIDATED")


@unittest.skipUnless(HAS_DELTA, "Delta local requiere Spark, Java y GTFS_DELTA_TEST_JARS preparados fuera de la suite.")
class SilverPublicationDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.temporary = TemporaryDirectory(prefix="gtfs-delta-tests-")
        cls.warehouse = Path(cls.temporary.name).resolve()
        if not cls.warehouse.is_relative_to(Path(gettempdir()).resolve()):
            raise RuntimeError("El warehouse de pruebas debe estar dentro de TEMP.")
        cls.spark = (
            SparkSession.builder.master("local[1]").appName("gtfs-publication-tests")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "1")
            .config("spark.databricks.delta.snapshotPartitions", "1")
            .config("spark.sql.warehouse.dir", cls.warehouse.as_uri())
            .config("spark.jars", os.environ["GTFS_DELTA_TEST_JARS"])
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .getOrCreate()
        )
        cls.spark.conf.set("spark.sql.session.timeZone", "UTC")
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()
        if cls.warehouse.is_relative_to(Path(gettempdir()).resolve()):
            cls.temporary.cleanup()

    def setUp(self):
        self.namespace = "gtfs_test_" + uuid4().hex
        self.spark.sql(f"create database {self.namespace}")
        self.tables = PublicationTables("spark_catalog", self.namespace)

    def tearDown(self):
        if not self.namespace.startswith("gtfs_test_"):
            raise RuntimeError("No eliminar un schema ajeno a las pruebas.")
        self.spark.sql(f"drop database {self.namespace} cascade")

    def publish(self, selected, rows=None, run_id=None):
        result = validate_snapshot(rows or data(selected), COLUMNS, selected)
        return publish_agency(self.spark, result, selected, self.tables, run_id=run_id)

    def test_two_versions_then_retry_preserves_fourteen_rows_and_old_names(self):
        old, new = spec(), spec("2026-09-29", "b" * 64)
        self.publish(old, run_id="old-first")
        before = self.spark.table(self.tables.name("silver")).collect()
        self.publish(new, run_id="new-first")
        self.assertEqual(self.spark.table(self.tables.name("silver")).count(), 14)
        self.publish(new, run_id="new-retry")
        self.publish(new, run_id="new-retry")
        all_rows = self.spark.table(self.tables.name("silver"))
        self.assertEqual(all_rows.count(), 14)
        previous = all_rows.filter(snapshot_predicate(old)).collect()
        self.assertEqual(set(json.dumps(row.asDict(), sort_keys=True, default=str) for row in previous), set(json.dumps(row.asDict(), sort_keys=True, default=str) for row in before))
        names = {row.source_feed_version: row.agency_name
                 for row in all_rows.filter("agency_id = '2'").collect()}
        self.assertEqual(names, {"2025-10-28": "2025-10-28 Marca 2", "2026-09-29": "2026-09-29 Marca 2"})
        self.assertEqual(self.spark.table(self.tables.name("audit")).count(), 3)

    def test_creation_race_fails_without_replacing_an_existing_table(self):
        from pyspark.errors import AnalysisException
        selected = spec()
        self.publish(selected)
        table = self.tables.name("silver")
        existing = self.spark.table(table)
        before = existing.collect()
        # Simulo que otro escritor crea la tabla justo tras comprobar su ausencia.
        with patch.object(type(self.spark.catalog), "tableExists", return_value=False):
            with self.assertRaises(AnalysisException):
                _overwrite_scope(existing.limit(1), table, snapshot_predicate(selected))
        self.assertEqual(self.spark.table(table).collect(), before)

    def test_hash_is_part_of_scope_even_when_publication_date_is_same(self):
        first, corrected = spec(), spec(content_hash="b" * 64)
        self.publish(first, data(first, 1))
        self.publish(corrected, data(corrected, 1))
        self.assertEqual(self.spark.table(self.tables.name("silver")).count(), 2)
        self.publish(corrected, data(corrected, 1))
        self.assertEqual(self.spark.table(self.tables.name("silver")).count(), 2)

    def test_rejected_snapshot_persists_reasons_without_changing_silver(self):
        selected = spec()
        self.publish(selected)
        before = self.spark.table(self.tables.name("silver")).collect()
        bad = data(selected, 1)
        bad[0]["agency_url"] = "/invalid"
        result = validate_snapshot(bad + deepcopy(bad), COLUMNS, selected)
        with self.assertRaises(SnapshotRejectedError):
            publish_agency(self.spark, result, selected, self.tables, run_id="rejected")
        after = self.spark.table(self.tables.name("silver")).collect()
        self.assertEqual(set(json.dumps(row.asDict(), sort_keys=True, default=str) for row in before), set(json.dumps(row.asDict(), sort_keys=True, default=str) for row in after))
        quarantine = self.spark.table(self.tables.name("quarantine")).first()
        self.assertEqual(quarantine.input_copies, 2)
        self.assertIn("AGENCY_URL_FORMAT_INVALID", quarantine.error_codes)
        audit = self.spark.table(self.tables.name("audit")).filter("silver_run_id = 'rejected'").first()
        self.assertEqual(audit.status, "REJECTED")
        self.assertFalse(audit.silver_committed)

    def test_preview_does_not_create_any_table(self):
        selected = spec()
        result = validate_snapshot(data(selected), COLUMNS, selected)
        publish_agency(self.spark, result, selected, self.tables, mode="validate")
        self.assertTrue(all(not self.spark.catalog.tableExists(self.tables.name(kind))
                            for kind in ("silver", "audit", "quarantine")))

    def test_empty_or_cross_snapshot_output_cannot_replace_existing_data(self):
        from pyspark.sql import functions as F
        selected = spec()
        self.publish(selected)
        existing = self.spark.table(self.tables.name("silver"))
        with self.assertRaises(ValueError):
            _overwrite_scope(existing.limit(0), self.tables.name("silver"), snapshot_predicate(selected))
        with self.assertRaises(ValueError):
            _overwrite_scope(existing.withColumn("source_sha256", F.lit("b" * 64)),
                             self.tables.name("silver"), snapshot_predicate(selected))
        self.assertEqual(self.spark.table(self.tables.name("silver")).count(), 7)

    def test_routes_reuses_publication_audit_retry_and_quarantine(self):
        from gtfs_silver.models import SnapshotSpec
        from gtfs_silver.publication import publish_snapshot
        from gtfs_silver.routes_spark import read_and_validate
        from test_routes_validation import COLUMNS as route_columns, fixture as route_fixture
        from pyspark.sql.types import StringType, StructField, StructType, TimestampType
        selected = spec()
        self.publish(selected)
        dependency = self.spark.table(self.tables.name("silver"))
        tables = PublicationTables("spark_catalog", self.namespace, "routes")
        schema = StructType([StructField(c, StringType()) for c in
                             (*route_columns, "source_feed_version", "source_sha256", "source_file_path")]
                            + [StructField("bronze_loaded_at_utc", TimestampType())])
        for version, content_hash in (("2025-10-28", "a" * 64), ("2026-09-29", "b" * 64)):
            agency_spec = spec(version, content_hash)
            if version != selected.feed_version:
                self.publish(agency_spec)
                dependency = self.spark.table(self.tables.name("silver"))
            route_spec = SnapshotSpec(version, content_hash, "/fixture/routes.txt", "routes")
            rows = [route_fixture("same", source_feed_version=version, source_sha256=content_hash,
                                  route_long_name=version)]
            result = read_and_validate(self.spark.createDataFrame(rows, schema), route_columns, route_spec, dependency)
            preview = publish_snapshot(self.spark, result, route_spec, tables, mode="validate")
            self.assertFalse(preview["persisted"])
            self.assertFalse(self.spark.catalog.tableExists(tables.name("silver")) if version == selected.feed_version else False)
            publish_snapshot(self.spark, result, route_spec, tables, run_id=version)
        publish_snapshot(self.spark, result, route_spec, tables, run_id=version)
        self.assertEqual(self.spark.table(tables.name("silver")).count(), 2)
        self.assertEqual(self.spark.table(tables.name("silver")).schema["route_type"].dataType.simpleString(), "int")
        rows[0]["route_type"] = "bad"
        rejected = read_and_validate(self.spark.createDataFrame(rows * 2, schema), route_columns, route_spec, dependency)
        with self.assertRaises(SnapshotRejectedError):
            publish_snapshot(self.spark, rejected, route_spec, tables, run_id="route-rejected")
        self.assertEqual(self.spark.table(tables.name("silver")).count(), 2)
        quarantine = self.spark.table(tables.name("quarantine")).first()
        self.assertEqual(quarantine.route_id, "same")
        self.assertEqual(quarantine.input_copies, 2)
        self.assertIn("ROUTE_TYPE_INVALID", quarantine.error_codes)
        statuses = {row.status for row in self.spark.table(tables.name("audit")).filter("entity = 'routes'").collect()}
        self.assertEqual(statuses, {"SUCCEEDED", "REJECTED"})

    def test_pipeline_reads_bronze_and_agency_with_real_versioned_delta_reader(self):
        from gtfs_silver import pipeline
        from test_routes_validation import COLUMNS as route_columns, fixture as route_fixture
        from pyspark.sql.types import StringType, StructField, StructType, TimestampType
        selected = spec()
        parameters = dict(catalog="spark_catalog", schema=self.namespace, staging_volume="staging",
                          feed_version=selected.feed_version, snapshot_sha256=selected.sha256)
        base = (f"/Volumes/spark_catalog/{self.namespace}/staging/gtfs_static/"
                f"feed_version={selected.feed_version}/sha256={selected.sha256}")
        agency_spec = SnapshotSpec(selected.feed_version, selected.sha256, base + "/agency.txt")
        agency_schema = StructType([
            *[StructField(c, StringType()) for c in (*COLUMNS, "source_feed_version", "source_sha256", "source_file_path")],
            StructField("bronze_loaded_at_utc", TimestampType()),
        ])
        agency_source = self.spark.createDataFrame(data(agency_spec), agency_schema)
        agency_source.writeTo(f"spark_catalog.{self.namespace}.bronze_gtfs_agency").using("delta").create()
        with patch.object(pipeline, "read_source_header", return_value=COLUMNS):
            agency_output = pipeline.run_entity(self.spark, entity="agency", **parameters)
        self.assertEqual(agency_output["status"], "SUCCEEDED")
        self.assertEqual(agency_output["candidate_rows"], 7)
        route_schema = StructType([
            *[StructField(c, StringType()) for c in (*route_columns, "source_feed_version", "source_sha256", "source_file_path")],
            StructField("bronze_loaded_at_utc", TimestampType()),
        ])
        route_source = self.spark.createDataFrame([route_fixture(source_file_path=base + "/routes.txt")], route_schema)
        route_source.writeTo(f"spark_catalog.{self.namespace}.bronze_gtfs_routes").using("delta").create()
        # Solo simulo el encabezado Staging; el pipeline, lector y escritor Delta son reales.
        with patch.object(pipeline.routes_spark, "read_source_header", return_value=route_columns):
            output = pipeline.run_entity(self.spark, entity="routes", **parameters)
            retry = pipeline.run_entity(self.spark, entity="routes", **parameters)
        self.assertEqual(output["status"], "SUCCEEDED")
        self.assertEqual(retry["candidate_rows"], 1)
        self.assertEqual(self.spark.table(f"spark_catalog.{self.namespace}.silver_gtfs_routes").count(), 1)
        self.assertEqual(self.spark.table(self.tables.name("silver")).count(), 7)

    def test_stops_pipeline_publication_retry_history_and_quarantine_with_real_delta(self):
        from gtfs_silver import pipeline
        from test_stops_validation import COLUMNS as stop_columns, fixture as stop_fixture
        from pyspark.sql.types import StringType, StructField, StructType, TimestampType
        tables = PublicationTables("spark_catalog", self.namespace, "stops")
        bronze = f"spark_catalog.{self.namespace}.bronze_gtfs_stops"
        schema = StructType([
            *[StructField(c, StringType()) for c in (*stop_columns, "source_feed_version", "source_sha256", "source_file_path")],
            StructField("bronze_loaded_at_utc", TimestampType()),
        ])
        for index, version in enumerate(("2025-10-28", "2026-09-29")):
            content_hash = ("a" if index == 0 else "b") * 64
            parameters = dict(catalog="spark_catalog", schema=self.namespace, staging_volume="staging",
                              entity="stops", feed_version=version, snapshot_sha256=content_hash)
            path = (f"/Volumes/spark_catalog/{self.namespace}/staging/gtfs_static/"
                    f"feed_version={version}/sha256={content_hash}/stops.txt")
            origin = dict(source_feed_version=version, source_sha256=content_hash, source_file_path=path)
            rows = [stop_fixture("S", location_type="1", stop_name=f" {version} Estación ", **origin),
                    stop_fixture("P", parent_station="S", **origin)]
            source = self.spark.createDataFrame(rows, schema)
            source.write.format("delta").mode("append").saveAsTable(bronze)
            with patch.object(pipeline.stops_spark, "read_source_header", return_value=stop_columns):
                preview = pipeline.run_entity(self.spark, **parameters, mode="validate")
                self.assertFalse(preview["persisted"])
                self.assertEqual(preview["name_trimmed_rows"], 1)
                published = pipeline.run_entity(self.spark, **parameters)
            self.assertEqual(published["status"], "SUCCEEDED")
            self.assertEqual(published["candidate_rows"], 2)
        with patch.object(pipeline.stops_spark, "read_source_header", return_value=stop_columns):
            retry = pipeline.run_entity(self.spark, **parameters)
        output = self.spark.table(tables.name("silver"))
        self.assertEqual(retry["status"], "SUCCEEDED")
        self.assertEqual(output.count(), 4)
        self.assertEqual(output.schema["stop_lat"].dataType.simpleString(), "double")
        self.assertEqual(output.schema["location_type"].dataType.simpleString(), "int")
        self.assertEqual(len(output.schema.fields), 17)
        old = output.filter("source_feed_version = '2025-10-28' and stop_id = 'S'").first()
        self.assertEqual(old.stop_name, "2025-10-28 Estación")
        bad_rows = [stop_fixture("bad", stop_lat="bad", **origin)] * 2
        self.spark.createDataFrame(bad_rows, schema).write.format("delta").mode("append").saveAsTable(bronze)
        with patch.object(pipeline.stops_spark, "read_source_header", return_value=stop_columns):
            rejected = pipeline.run_entity(self.spark, **parameters, mode="validate")
            self.assertEqual(rejected["status"], "REJECTED")
            with self.assertRaises(SnapshotRejectedError):
                pipeline.run_entity(self.spark, **parameters)
        self.assertEqual(self.spark.table(tables.name("silver")).count(), 4)
        quarantine = self.spark.table(tables.name("quarantine")).first()
        self.assertEqual(quarantine.stop_id, "bad")
        self.assertEqual(quarantine.input_copies, 2)
        self.assertIn("STOP_LAT_INVALID", quarantine.error_codes)
        statuses = {r.status for r in self.spark.table(tables.name("audit")).filter("entity = 'stops'").collect()}
        self.assertEqual(statuses, {"SUCCEEDED", "REJECTED"})

    def test_failure_after_commit_is_explicit_in_audit_and_requires_review(self):
        selected = spec()
        with patch("gtfs_silver.publication._same_rows", return_value=False), self.assertRaises(RuntimeError):
            self.publish(selected, run_id="verification-failed")
        self.assertEqual(self.spark.table(self.tables.name("silver")).count(), 7)
        audit = self.spark.table(self.tables.name("audit")).first()
        self.assertEqual(audit.status, "FAILED")
        self.assertTrue(audit.silver_committed)


if __name__ == "__main__":
    unittest.main()
