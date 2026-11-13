"""Compruebo el despacho y los límites de IO sin ejecutar Spark ni leer archivos."""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch, sentinel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "databricks"))
from gtfs_silver import pipeline


class SilverPipelineTests(unittest.TestCase):
    def parameters(self, entity):
        return dict(catalog="workspace", schema="fixture", staging_volume="staging", entity=entity,
                    feed_version="2025-10-28", snapshot_sha256="a" * 64, mode="validate")

    def test_routes_dispatches_with_matching_source_path_and_pinned_dependency(self):
        spark = MagicMock()
        spark.catalog.tableExists.return_value = True
        spark.sql.return_value.first.return_value = {"version": 4}
        spark.read.option.return_value.table.side_effect = [sentinel.bronze, sentinel.agency]
        with patch.object(pipeline.routes_spark, "read_source_header", return_value=("route_id",)), \
             patch.object(pipeline, "_versioned_table", wraps=pipeline._versioned_table) as read, \
             patch.object(pipeline.routes_spark, "read_and_validate", return_value=sentinel.result) as validate, \
             patch.object(pipeline, "publish_snapshot", return_value={"persisted": False}) as publish:
            result = pipeline.run_entity(spark, **self.parameters("routes"))
        self.assertFalse(result["persisted"])
        self.assertEqual(read.call_count, 2)
        self.assertEqual(read.call_args_list[0].args[1], "workspace.fixture.bronze_gtfs_routes")
        self.assertEqual(read.call_args_list[1].args[1], "workspace.fixture.silver_gtfs_agency")
        self.assertEqual(spark.sql.call_args_list[0].args[0],
                         "describe history `workspace`.`fixture`.`bronze_gtfs_routes` limit 1")
        arguments = validate.call_args.args
        self.assertIs(arguments[0], sentinel.bronze)
        self.assertIs(arguments[3], sentinel.agency)
        self.assertEqual(arguments[2].entity, "routes")
        self.assertTrue(arguments[2].source_path.endswith("/routes.txt"))
        self.assertEqual(publish.call_args.kwargs["mode"], "validate")

    def test_agency_keeps_bounded_validator_and_compatible_publication(self):
        spark = MagicMock()
        spark.catalog.tableExists.return_value = True
        spark.sql.return_value.first.return_value = {"version": 4}
        spark.read.option.return_value.table.return_value = sentinel.bronze
        with patch.object(pipeline, "read_source_header", return_value=("agency_id",)), \
             patch.object(pipeline, "_versioned_table", wraps=pipeline._versioned_table), \
             patch.object(pipeline, "read_and_validate", return_value=sentinel.result) as validate, \
             patch.object(pipeline, "publish_agency", return_value={"persisted": False}):
            pipeline.run_entity(spark, **self.parameters("agency"))
        self.assertIs(validate.call_args.args[0], sentinel.bronze)
        self.assertEqual(spark.sql.call_args.args[0],
                         "describe history `workspace`.`fixture`.`bronze_gtfs_agency` limit 1")
        self.assertEqual(validate.call_args.args[3], 1000)
        self.assertEqual(validate.call_args.args[2].entity, "agency")

    def test_stops_dispatches_without_agency_or_routes_and_uses_plain_table_name(self):
        spark = MagicMock()
        spark.catalog.tableExists.return_value = True
        spark.sql.return_value.first.return_value = {"version": 4}
        spark.read.option.return_value.table.return_value = sentinel.stops
        with patch.object(pipeline.stops_spark, "read_source_header", return_value=("stop_id",)), \
             patch.object(pipeline.stops_spark, "read_and_validate", return_value=sentinel.result) as validate, \
             patch.object(pipeline, "publish_snapshot", return_value={"persisted": False}) as publish:
            result = pipeline.run_entity(spark, **self.parameters("stops"))
        self.assertFalse(result["persisted"])
        self.assertEqual(spark.catalog.tableExists.call_count, 1)
        self.assertEqual(spark.sql.call_args.args[0],
                         "describe history `workspace`.`fixture`.`bronze_gtfs_stops` limit 1")
        self.assertEqual(len(validate.call_args.args), 3)
        self.assertEqual(validate.call_args.args[2].entity, "stops")
        self.assertTrue(validate.call_args.args[2].source_path.endswith("/stops.txt"))
        self.assertEqual(publish.call_args.kwargs["mode"], "validate")

    def test_calendars_dispatch_with_conditional_pinned_weekly_dependency(self):
        for entity, weekly in (("calendar", False), ("calendar_dates", True), ("calendar_dates", False)):
            spark = MagicMock()
            spark.catalog.tableExists.side_effect = [True, True] if weekly else [True, False]
            spark.sql.return_value.first.return_value = {"version": 4}
            spark.read.option.return_value.table.side_effect = [sentinel.bronze, sentinel.calendar] if weekly else [sentinel.bronze]
            with patch.object(pipeline.calendars_spark, "read_source_header", return_value=("service_id",)), \
                 patch.object(pipeline.calendars_spark, "calendar_source_present", return_value=weekly), \
                 patch.object(pipeline.calendars_spark, "read_and_validate", return_value=sentinel.result) as validate, \
                 patch.object(pipeline, "publish_snapshot", return_value={"persisted": False}):
                pipeline.run_entity(spark, **self.parameters(entity))
            self.assertEqual(validate.call_args.args[2].entity, entity)
            if entity == "calendar_dates":
                self.assertEqual(validate.call_args.kwargs["calendar_published"], weekly)
            self.assertEqual(len(validate.call_args.args), 4 if weekly else 3)
            if weekly:
                self.assertIs(validate.call_args.args[3], sentinel.calendar)
                self.assertEqual(spark.sql.call_args.args[0], "describe history `workspace`.`fixture`.`silver_gtfs_calendar` limit 1")

    def test_published_weekly_source_requires_silver_calendar(self):
        spark=MagicMock()
        spark.catalog.tableExists.side_effect=[True, False]
        spark.sql.return_value.first.return_value={"version": 1}
        with patch.object(pipeline.calendars_spark,"read_source_header",return_value=("service_id",)), \
             patch.object(pipeline.calendars_spark,"calendar_source_present",return_value=True):
            with self.assertRaisesRegex(ValueError,"Publica calendar"):
                pipeline.run_entity(spark,**self.parameters("calendar_dates"))

    def test_unknown_entity_or_invalid_mode_stops_before_source_access(self):
        for parameters in (self.parameters("unknown_entity"), {**self.parameters("routes"), "mode": "overwrite_all"}):
            spark = MagicMock()
            with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                pipeline.run_entity(spark, **parameters)
            spark.conf.set.assert_not_called()
            spark.catalog.tableExists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
