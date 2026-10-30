"""Regresiones de Raw/Bronze con fixtures sintéticos y código real del notebook."""

import csv
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

from notebook_test_support import (
    Frame, Functions, LocalVolume, SparkDouble,
    cell_source, execute_function, spark_type_stubs,
)

RAW = "02_raw_static_gtfs_ingestion.ipynb"
REFERENCES = "04_bronze_static_gtfs_reference_entities.ipynb"
QUALITY = "07_validate_bronze_gtfs_snapshot.ipynb"
ESSENTIALS = {"agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}
VERSION = "2026-09-29"
HASH = "a" * 64


def zip_fixture(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in sorted(files):
            archive.writestr(name, "synthetic_header\nsynthetic_value\n")
    return buffer.getvalue()


class RawContractTests(unittest.TestCase):
    def namespace(self, content):
        return {
            "zip_bytes": content, "run_id": "fixture-run",
            "current_feed": {"feed_version": VERSION, "source_url": "https://example.invalid/fixture.zip"},
            "response": SimpleNamespace(status_code=200),
            "download_metadata": {"sha256": hashlib.sha256(content).hexdigest()},
            "spark": SparkDouble(), "display": lambda frame: None,
        }

    def validate(self, namespace):
        with spark_type_stubs():
            exec(cell_source(RAW, "BLOQUE 3 —"), namespace)

    def test_accepts_each_calendar_combination(self):
        for calendars in ({"calendar.txt"}, {"calendar_dates.txt"}, {"calendar.txt", "calendar_dates.txt"}):
            with self.subTest(calendars=calendars):
                namespace = self.namespace(zip_fixture(ESSENTIALS | calendars))
                self.validate(namespace)
                self.assertTrue(namespace["validation_passed"])

    def test_rejects_missing_essential(self):
        namespace = self.namespace(zip_fixture((ESSENTIALS - {"routes.txt"}) | {"calendar.txt"}))
        with self.assertRaisesRegex(RuntimeError, "routes.txt"):
            self.validate(namespace)

    def test_rejects_missing_calendar_definition(self):
        with self.assertRaisesRegex(RuntimeError, "calendario"):
            self.validate(self.namespace(zip_fixture(ESSENTIALS)))

    def test_rejects_non_zip_response(self):
        with self.assertRaisesRegex(RuntimeError, "ZIP válido"):
            self.validate(self.namespace(b"not a ZIP"))

    def test_persistence_guard_prevents_all_writes(self):
        namespace = {"validation_passed": False, "dbutils": Mock()}
        with patch("builtins.open") as open_mock:
            with self.assertRaisesRegex(RuntimeError, "Raw bloqueado"):
                exec(cell_source(RAW, "BLOQUE 4 —"), namespace)
        open_mock.assert_not_called()
        self.assertEqual(namespace["dbutils"].mock_calls, [])

    def test_retry_reuses_snapshot_and_same_run_manifest(self):
        namespace = self.namespace(zip_fixture(ESSENTIALS | {"calendar_dates.txt"}))
        self.validate(namespace)
        with TemporaryDirectory() as temporary:
            volume = LocalVolume()
            namespace.update(
                raw_volume_path=temporary,
                captured_at_utc=datetime(2026, 10, 29, tzinfo=timezone.utc),
                dbutils=SimpleNamespace(fs=volume, jobs=SimpleNamespace(taskValues=Mock())),
            )
            block = cell_source(RAW, "BLOQUE 4 —")
            with spark_type_stubs(), patch("builtins.print"):
                exec(block, namespace)
                first_manifest = Path(namespace["manifest_path"]).read_bytes()
                # El segundo intento no debe abrir el ZIP en modo escritura.
                with patch("builtins.open", side_effect=AssertionError("No sobrescribir el ZIP")):
                    exec(block, namespace)
            self.assertEqual(Path(namespace["raw_snapshot_path"]).read_bytes(), namespace["zip_bytes"])
            self.assertEqual(Path(namespace["manifest_path"]).read_bytes(), first_manifest)
            self.assertEqual(volume.put_count, 1)
            self.assertTrue(namespace["snapshot_already_exists"])
            self.assertTrue(namespace["manifest_already_exists"])


class ReferenceContractTests(unittest.TestCase):
    def namespace(self, files):
        namespace = {"catalog": "workspace", "schema": "gtfs_bogota"}
        with patch("builtins.print"):
            exec(cell_source(REFERENCES, "BLOQUE 2 —"), namespace)
        loader = Mock(side_effect=lambda entity: (entity["file_name"], "table", 1, False))
        namespace.update(
            staging_snapshot_path="fixture",
            dbutils=SimpleNamespace(fs=SimpleNamespace(ls=lambda path: [SimpleNamespace(name=name) for name in files])),
            load_entity_to_bronze=loader, spark=SparkDouble(), load_result_schema=None,
            display=lambda frame: None,
        )
        return namespace, loader

    def test_loads_only_the_published_calendars(self):
        for calendars in ({"calendar.txt"}, {"calendar_dates.txt"}, {"calendar.txt", "calendar_dates.txt"}):
            with self.subTest(calendars=calendars):
                namespace, loader = self.namespace(ESSENTIALS | calendars)
                with patch("builtins.print"):
                    exec(cell_source(REFERENCES, "BLOQUE 4 —"), namespace)
                loaded = {call.args[0]["file_name"] for call in loader.call_args_list}
                self.assertEqual(loaded & {"calendar.txt", "calendar_dates.txt"}, calendars)

    def test_rejects_missing_calendars_before_any_load(self):
        namespace, loader = self.namespace(ESSENTIALS)
        with self.assertRaisesRegex(RuntimeError, "definición de servicio"):
            exec(cell_source(REFERENCES, "BLOQUE 4 —"), namespace)
        loader.assert_not_called()

    def test_other_required_files_remain_required(self):
        namespace, loader = self.namespace((ESSENTIALS - {"trips.txt"}) | {"calendar.txt"})
        with self.assertRaisesRegex(RuntimeError, "trips.txt"):
            exec(cell_source(REFERENCES, "BLOQUE 4 —"), namespace)
        loader.assert_not_called()

    def test_weekly_calendar_requires_weekday_columns(self):
        namespace, _ = self.namespace(ESSENTIALS | {"calendar.txt"})
        entity = next(item for item in namespace["reference_entities"] if item["file_name"] == "calendar.txt")
        helper_source = cell_source(REFERENCES, "BLOQUE 3 —")
        namespace["csv"] = csv
        execute_function(helper_source, "read_gtfs_header", namespace)
        execute_function(helper_source, "load_entity_to_bronze", namespace)
        with TemporaryDirectory() as temporary:
            namespace["staging_snapshot_path"] = temporary
            Path(temporary, "calendar.txt").write_text("service_id,start_date,end_date\ns,20260101,20261231\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "monday"):
                namespace["load_entity_to_bronze"](entity)


class QualityContractTests(unittest.TestCase):
    def namespace(self, files, tables=None):
        checks = []
        namespace = {
            "catalog": "workspace", "schema": "gtfs_bogota", "feed_version": VERSION,
            "snapshot_sha256": HASH, "staging_snapshot_path": "fixture",
            "dbutils": SimpleNamespace(fs=SimpleNamespace(ls=lambda path: [SimpleNamespace(name=name) for name in files])),
            "spark": SparkDouble(tables), "F": Functions, "add_check": lambda *args: checks.append(args),
            "quality_rows": checks, "quality_audit_schema": None, "display": lambda frame: None,
        }
        exec(cell_source(QUALITY, "BLOQUE 2 —"), namespace)
        return namespace, checks

    def check(self, checks, name, entity=None):
        matches = [row for row in checks if row[0] == name and (entity is None or row[2] == entity)]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_calendar_group_passes_with_one_or_both_files(self):
        for calendars in ({"calendar.txt"}, {"calendar_dates.txt"}, {"calendar.txt", "calendar_dates.txt"}):
            with self.subTest(calendars=calendars):
                namespace, checks = self.namespace(calendars)
                exec(cell_source(QUALITY, "BLOQUE 4 —"), namespace)
                self.assertEqual(self.check(checks, "calendar_definition_present")[4], "PASS")
                absent = {"calendar.txt", "calendar_dates.txt"} - calendars
                for name in absent:
                    self.assertEqual(self.check(checks, "source_file_present", name.removesuffix(".txt"))[4], "NOT_APPLICABLE")

    def test_calendar_group_fails_if_both_files_are_absent(self):
        namespace, checks = self.namespace(set())
        exec(cell_source(QUALITY, "BLOQUE 4 —"), namespace)
        self.assertEqual(self.check(checks, "calendar_definition_present")[3:5], ("BLOCKING", "FAIL"))

    def test_complete_snapshot_has_no_blocking_presence_failures(self):
        namespace, checks = self.namespace(set())
        entities = namespace["gtfs_entities"]
        published = [entity for entity in entities if entity["required"] or entity["name"] == "calendar_dates"]
        files = {entity["file_name"] for entity in published}
        namespace["dbutils"].fs.ls = lambda path: [SimpleNamespace(name=name) for name in files]
        namespace["spark"] = SparkDouble({
            f"workspace.gtfs_bogota.{entity['table_name']}": [
                {"source_sha256": HASH, "source_feed_version": VERSION}
            ] for entity in published
        })
        exec(cell_source(QUALITY, "BLOQUE 4 —"), namespace)
        self.assertFalse([row for row in checks if row[3:5] == ("BLOCKING", "FAIL")])
        self.assertEqual(self.check(checks, "bronze_provenance_version", "routes")[4:6], ("PASS", 0))

    def test_null_and_wrong_versions_are_blocking_and_other_hash_is_ignored(self):
        rows = [
            {"source_sha256": HASH, "source_feed_version": VERSION},
            {"source_sha256": HASH, "source_feed_version": None},
            {"source_sha256": HASH, "source_feed_version": "2025-10-28"},
            {"source_sha256": "b" * 64, "source_feed_version": None},
        ]
        namespace, checks = self.namespace({"routes.txt", "calendar.txt"}, {"workspace.gtfs_bogota.bronze_gtfs_routes": rows})
        exec(cell_source(QUALITY, "BLOQUE 4 —"), namespace)
        check = self.check(checks, "bronze_provenance_version", "routes")
        self.assertEqual(check[3:6], ("BLOCKING", "FAIL", 2))

    def test_rows_without_source_file_are_blocking(self):
        rows = [{"source_sha256": HASH, "source_feed_version": VERSION}]
        namespace, checks = self.namespace({"calendar.txt"}, {"workspace.gtfs_bogota.bronze_gtfs_frequencies": rows})
        exec(cell_source(QUALITY, "BLOQUE 4 —"), namespace)
        self.assertEqual(self.check(checks, "bronze_snapshot_rows", "frequencies")[3:5], ("BLOCKING", "FAIL"))

    def test_services_are_checked_with_each_calendar_combination(self):
        cases = [
            ({"calendar": ["weekly"]}, ["weekly"], "PASS", 0),
            ({"calendar_dates": ["special"]}, ["special"], "PASS", 0),
            ({"calendar": ["weekly"], "calendar_dates": ["special", "weekly"]}, ["weekly", "special"], "PASS", 0),
            ({"calendar_dates": ["special", None, " "]}, ["unknown", "unknown"], "WARN", 1),
            ({}, ["weekly"], "NOT_APPLICABLE", "entidad no disponible"),
        ]
        for calendars, trip_services, status, count in cases:
            with self.subTest(calendars=calendars, status=status):
                namespace, checks = self.namespace(set())
                namespace["snapshot_dfs"] = {
                    name: Frame({"service_id": value} for value in values)
                    for name, values in calendars.items()
                }
                namespace["snapshot_dfs"]["trips"] = Frame({"service_id": value} for value in trip_services)
                execute_function(cell_source(QUALITY, "BLOQUE 3 —"), "is_blank", namespace)
                execute_function(cell_source(QUALITY, "BLOQUE 5 —"), "validate_trip_services", namespace)
                namespace["validate_trip_services"]()
                self.assertEqual(self.check(checks, "trips_service_id_exists")[4:6], (status, count))


if __name__ == "__main__":
    unittest.main()
