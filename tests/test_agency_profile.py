"""Pruebas del perfilado agency: sin red ni escrituras de datos del proyecto.

Las pruebas de métricas usan Spark real solo si están disponibles PySpark y Java.
Las pruebas de parámetros y encabezados no requieren esas dependencias.
"""

import ast
import csv
from datetime import date
import importlib.util
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
import unittest

from notebook_test_support import cell_source, execute_function

NOTEBOOK = "silver/08_profile_gtfs_reference_entities.ipynb"
HAS_LOCAL_SPARK = importlib.util.find_spec("pyspark") is not None and shutil.which("java") is not None


class AgencyProfileInputTests(unittest.TestCase):
    def setUp(self):
        self.namespace = {"date": date, "re": re, "csv": csv}
        execute_function(cell_source(NOTEBOOK, "BLOQUE 1 —"), "validate_profile_parameters", self.namespace)
        execute_function(cell_source(NOTEBOOK, "BLOQUE 2 —"), "read_agency_header", self.namespace)

    def validate(self, version="2025-10-28", content_hash="a" * 64, catalog="workspace"):
        self.namespace["validate_profile_parameters"](catalog, "gtfs_bogota", "staging_gtfs", version, content_hash)

    def test_accepts_explicit_snapshot_parameters(self):
        self.validate()
        self.validate(version="2026-09-29")

    def test_rejects_invalid_dates(self):
        for version in ("2025-02-30", "20251028", "2025-13-01"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.validate(version=version)

    def test_rejects_invalid_hashes(self):
        for content_hash in ("", "a" * 63, "g" * 64):
            with self.subTest(content_hash=content_hash), self.assertRaises(ValueError):
                self.validate(content_hash=content_hash)

    def test_rejects_unsafe_identifiers(self):
        for catalog in ("workspace.other", "workspace`", "../workspace"):
            with self.subTest(catalog=catalog), self.assertRaises(ValueError):
                self.validate(catalog=catalog)

    def test_header_preserves_published_fields_and_supports_bom(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary, "agency.txt")
            path.write_text("agency_id,agency_name\n001,Example Agency\n", encoding="utf-8-sig")
            self.assertEqual(self.namespace["read_agency_header"](str(path)), ["agency_id", "agency_name"])

    def test_rejects_empty_or_ambiguous_headers(self):
        for content in ("", "agency_id,agency_id\n", "agency_id, \n"):
            with self.subTest(content=content), TemporaryDirectory() as temporary:
                path = Path(temporary, "agency.txt")
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    self.namespace["read_agency_header"](str(path))


@unittest.skipUnless(HAS_LOCAL_SPARK, "Requiere PySpark y Java locales; validar métricas reales en Databricks.")
class AgencyProfileSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (
            SparkSession.builder.master("local[1]").appName("gtfs-agency-profile-tests")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate()
        )

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def setUp(self):
        from pyspark.sql import DataFrame, functions as F
        from pyspark.sql.types import BooleanType, LongType, StringType, StructField, StructType
        self.namespace = {
            "DataFrame": DataFrame, "F": F, "BooleanType": BooleanType,
            "LongType": LongType, "StringType": StringType,
            "StructField": StructField, "StructType": StructType,
            "technical_columns": {"source_feed_version", "source_sha256", "source_file_path", "bronze_loaded_at_utc"},
        }
        source = cell_source(NOTEBOOK, "BLOQUE 3 —")
        assignment = next(
            node for node in ast.parse(source).body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "agency_field_contract" for target in node.targets)
        )
        self.namespace["agency_field_contract"] = ast.literal_eval(assignment.value)
        execute_function(source, "profile_agency_fields", self.namespace)
        execute_function(cell_source(NOTEBOOK, "BLOQUE 4 —"), "duplicate_agency_ids", self.namespace)

    def frame(self, columns, rows):
        schema = self.namespace["StructType"]([
            self.namespace["StructField"](name, self.namespace["StringType"](), True)
            for name in columns
        ])
        return self.spark.createDataFrame(rows, schema=schema)

    def test_profile_distinguishes_null_empty_whitespace_and_absent_column(self):
        df = self.frame(
            ["agency_id", "agency_name", "agency_fare_url"],
            [("001", None, None), ("002", "", None), ("003", " \t", None), ("004", "  Agency ", None)],
        )
        original = df.collect()
        profile = self.namespace["profile_agency_fields"](df, ["agency_id", "agency_name"])
        rows = {row.field_name: row.asDict() for row in profile.collect()}
        name = rows["agency_name"]
        self.assertEqual([name[key] for key in ("null_count", "empty_count", "whitespace_only_count", "non_blank_count")], [1, 1, 1, 1])
        self.assertEqual(name["distinct_non_blank_count"], 1)
        self.assertEqual(name["edge_whitespace_count"], 1)
        self.assertFalse(rows["agency_fare_url"]["source_column_present"])
        self.assertEqual(rows["agency_fare_url"]["null_count"], 4)
        self.assertIsNone(rows["agency_email"]["null_count"])
        self.assertEqual(df.collect(), original)

    def test_duplicate_ids_distinguishes_identical_copies_from_conflicting_attributes(self):
        columns = ["agency_id", "agency_name"]
        df = self.frame(columns, [("001", "A"), ("001", "A"), ("002", "B"), ("002", "C"), (None, "D"), ("", "E")])
        result = self.namespace["duplicate_agency_ids"](df, columns)
        rows = {row.agency_id: row.asDict() for row in result.collect()}
        self.assertEqual(set(rows), {"001", "002"})
        self.assertEqual(rows["001"]["business_variants"], 1)
        self.assertEqual(rows["001"]["observation"], "copias_identicas")
        self.assertEqual(rows["002"]["business_variants"], 2)
        self.assertEqual(rows["002"]["observation"], "conflicto_de_clave")

    def test_unrecognized_field_keeps_type_decision_pending(self):
        df = self.frame(["agency_id", "new_field"], [("001", "123")])
        result = self.namespace["profile_agency_fields"](df, ["agency_id", "new_field"])
        row = next(row for row in result.collect() if row.field_name == "new_field")
        self.assertTrue(row.source_column_present)
        self.assertIsNone(row.proposed_silver_type)
        self.assertEqual(row.requiredness, "pendiente")


if __name__ == "__main__":
    unittest.main()
