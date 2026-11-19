"""Oferta diaria con fixtures sintéticas; sin red ni escrituras sobre Databricks."""
from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'databricks'))
from gtfs_gold.route_service_day import analysis_window, aggregate_days, prepare_route_service_day, run_route_service_day, _load_sources
from gtfs_gold.trip_coverage import AUDIT_DDL, SOURCE_RULES

HAS_SPARK = bool(importlib.util.find_spec('pyspark') and shutil.which('java'))
VERSION, SHA = '2026-09-29', 'a' * 64
START, END = date(2026, 1, 1), date(2026, 1, 3)
STAMP = datetime(2026, 11, 19, tzinfo=timezone.utc)
ARGS = dict(catalog='spark_catalog', schema='fixture', feed_version=VERSION, sha256=SHA,
            window_start=START.isoformat(), window_end=END.isoformat())
COVER_SCHEMA = 'source_feed_version string, source_sha256 string, trip_id string, route_id string, service_id string, frequency_window_count long, coverage_status string, gold_run_id string, gold_rule_version string'
DATE_SCHEMA = 'source_feed_version string, source_sha256 string, service_id string, service_date date, source_temporal_warning boolean, analysis_window_start date, analysis_window_end date, silver_run_id string, silver_rule_version string'
SILVER_AUDIT = 'entity string, source_feed_version string, source_sha256 string, silver_run_id string, status string, silver_committed boolean, silver_rule_version string, target_table string, candidate_rows long, started_at_utc timestamp'


class WindowTests(unittest.TestCase):
    def test_explicit_horizon_and_leap_year(self):
        self.assertEqual(analysis_window('2024-01-01', '2024-12-31')[1], date(2024, 12, 31))
        for first, last in [('', ''), ('2026-02-30', '2026-03-01'), ('2026-01-03', '2026-01-01'),
                            ('2000-01-01', '2099-01-01'), ('20260101', '20260103')]:
            with self.subTest(first=first), self.assertRaises(ValueError):
                analysis_window(first, last)


@unittest.skipUnless(HAS_SPARK, 'Requiere Spark y Java; no descargo dependencias desde los tests.')
class RouteServiceDaySparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master('local[1]').appName('gtfs-route-service-day-tests')
                     .config('spark.ui.enabled', 'false').config('spark.sql.shuffle.partitions', '1').getOrCreate())
        cls.spark.sparkContext.setLogLevel('ERROR')
        cls.spark.conf.set('spark.sql.session.timeZone', 'UTC')

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def setUp(self):
        self.cover_rows = [(VERSION, SHA, t, r, service, windows, status, 'coverage-run', 'trip_coverage_v1')
                           for t, r, service, windows, status in [
                               ('t1', 'r1', 'A', 0, 'sin_visitas'), ('t2', 'r1', 'B', 0, 'una_visita'),
                               ('t3', 'r2', 'B', 3, 'varias_visitas'), ('t4', 'r1', 'A', 0, 'varias_visitas'),
                               ('idle', 'r3', 'I', 0, 'varias_visitas')]]
        self.date_rows = [(VERSION, SHA, service, date(2026, 1, day), warning, START, END, 'dates-run', 'service_dates_v1')
                          for service, day, warning in [('A', 1, False), ('A', 2, False), ('B', 2, True), ('B', 3, True), ('unused', 1, False)]]
        self.cover = self.spark.createDataFrame(self.cover_rows, COVER_SCHEMA)
        self.dates = self.spark.createDataFrame(self.date_rows, DATE_SCHEMA)

    def prepare(self, cover=None, dates=None):
        with patch('gtfs_gold.route_service_day._load_sources', return_value=(
                cover if cover is not None else self.cover, dates if dates is not None else self.dates,
                {'versions': {'trip_coverage': 1, 'service_dates': 2}, 'runs': {'trip_coverage': 'coverage-run', 'service_dates': 'dates-run'}})):
            return prepare_route_service_day(self.spark, **ARGS)

    def test_multiple_services_one_route_and_multiple_windows_do_not_multiply_templates(self):
        output, result, _ = self.prepare()
        self.assertEqual((result['candidate_rows'], result['trip_service_days'], result['inactive_trip_count']), (5, 8, 1))
        rows = {(r.route_id, r.service_date.day): r.asDict() for r in output.collect()}
        both = rows['r1', 2]
        self.assertEqual((both['declared_trip_count'], both['active_service_count']), (3, 2))
        self.assertTrue(both['source_temporal_warning'])
        self.assertEqual((rows['r2', 2]['frequency_template_count'], rows['r2', 2]['frequency_window_count']), (1, 3))
        self.assertEqual(sum(r['frequency_template_count'] for r in rows.values()), 2)
        self.assertEqual(sum(r['frequency_window_count'] for r in rows.values()), 6)
        self.assertNotIn(('r3', 1), rows)
        self.assertEqual(rows['r1', 1]['trips_without_visits_count'], 1)

    def test_duplicate_active_dates_fail_before_join(self):
        with self.assertRaisesRegex(ValueError, 'duplicadas'):
            self.prepare(dates=self.dates.unionByName(self.dates.limit(1)))

    def test_duplicate_trip_identity_fails(self):
        with self.assertRaisesRegex(ValueError, 'claves'):
            self.prepare(cover=self.cover.unionByName(self.cover.limit(1)))

    def test_window_mismatch_is_not_silently_clipped(self):
        from pyspark.sql import functions as F
        with self.assertRaisesRegex(ValueError, 'horizonte'):
            self.prepare(dates=self.dates.withColumn('analysis_window_start', F.lit(date(2025, 12, 31))))

    def test_invalid_category_fails(self):
        from pyspark.sql import functions as F
        with self.assertRaisesRegex(ValueError, 'categorías'):
            self.prepare(cover=self.cover.withColumn('coverage_status', F.lit('desconocida')))

    def test_empty_daily_output_is_not_published(self):
        from pyspark.sql import functions as F
        with self.assertRaisesRegex(ValueError, 'vacía'):
            self.prepare(dates=self.dates.limit(1).withColumn('service_id', F.lit('other-service')))

    def test_snapshot_is_part_of_join_identity(self):
        from pyspark.sql import functions as F
        foreign = self.dates.withColumn('source_sha256', F.lit('b' * 64))
        self.assertEqual(aggregate_days(self.cover, foreign).count(), 0)

    def sources(self, latest_failure=False, abandoned=False, tampered=False):
        prefix = 'spark_catalog.fixture'
        audits = [(entity, VERSION, SHA, entity + '-run', 'SUCCEEDED', True, rule,
                   f'{prefix}.silver_gtfs_{entity}', 5, STAMP) for entity, rule in SOURCE_RULES.items()]
        audits.append(('service_dates', VERSION, SHA, 'dates-run', 'SUCCEEDED', True, 'service_dates_v1',
                       f'{prefix}.silver_gtfs_service_dates', len(self.date_rows), STAMP))
        if latest_failure:
            audits.append(('trips', VERSION, SHA, 'later', 'FAILED', False, 'trips_v1',
                           f'{prefix}.silver_gtfs_trips', 5, STAMP + timedelta(hours=1)))
        lineage = json.dumps({e: e + '-run' for e in SOURCE_RULES})
        events = []
        for event in ['STARTED', 'CLOSED']:
            events.append(('coverage-run', event, 'trip_coverage', VERSION, SHA, 'trip_coverage_v1',
                           'RUNNING' if event == 'STARTED' else 'SUCCEEDED', event == 'CLOSED', STAMP,
                           None if event == 'STARTED' else STAMP, None if event == 'STARTED' else 5, '{}', lineage, None))
        if abandoned:
            events.append(('abandoned', 'STARTED', 'trip_coverage', VERSION, SHA, 'trip_coverage_v1',
                           'RUNNING', False, STAMP + timedelta(hours=1), None, None, '{}', '{}', None))
        coverage = self.cover
        if tampered:
            from pyspark.sql import functions as F
            coverage = coverage.withColumn('gold_run_id', F.lit('modified'))
        frames = {f'{prefix}.audit_gtfs_silver_runs': self.spark.createDataFrame(audits, SILVER_AUDIT),
                  f'{prefix}.audit_gtfs_gold_runs': self.spark.createDataFrame(events, AUDIT_DDL),
                  f'{prefix}.gold_gtfs_trip_coverage': coverage, f'{prefix}.silver_gtfs_service_dates': self.dates}
        with patch.object(self.spark.catalog, 'tableExists', return_value=True), patch(
                'gtfs_gold.route_service_day.pinned_table', side_effect=lambda spark, table: (frames[table], 7)):
            return _load_sources(self.spark, 'spark_catalog', 'fixture', VERSION, SHA)

    def test_audited_sources_are_pinned_and_current(self):
        coverage, dates, refs = self.sources()
        self.assertEqual((coverage.count(), dates.count()), (5, 5))
        self.assertEqual(refs['runs']['trip_coverage'], 'coverage-run')
        self.assertEqual(len(refs['versions']), 4)

    def test_later_failed_silver_attempt_blocks_stale_coverage(self):
        with self.assertRaisesRegex(ValueError, 'desactualizada'):
            self.sources(latest_failure=True)

    def test_later_abandoned_gold_attempt_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError, 'cierre único'):
            self.sources(abandoned=True)

    def test_audited_metadata_drift_blocks_source(self):
        with self.assertRaisesRegex(ValueError, 'auditada'):
            self.sources(tampered=True)

    def test_validate_has_no_writes(self):
        prepared = self.prepare()
        with patch('gtfs_gold.route_service_day.prepare_route_service_day', return_value=prepared), patch(
                'gtfs_gold.route_service_day.immutable_insert') as audit, patch(
                'gtfs_gold.route_service_day._overwrite_scope') as writer:
            result = run_route_service_day(self.spark, **ARGS)
        self.assertEqual(result['status'], 'VALIDATED')
        self.assertFalse(result['persisted'])
        audit.assert_not_called()
        writer.assert_not_called()

    def test_publish_calls_scoped_writer_and_checks_commit(self):
        prepared = self.prepare()
        stored, events = {}, []
        target = 'spark_catalog.fixture.gold_gtfs_route_service_day'
        def write(frame, table, predicate):
            self.assertEqual(table, target)
            self.assertEqual(predicate, f"source_feed_version = '{VERSION}' and source_sha256 = '{SHA}'")
            stored[table] = frame
        def record(spark, frame, table, keys):
            events.append(frame.first().asDict())
        with patch('gtfs_gold.route_service_day.prepare_route_service_day', return_value=prepared), patch(
                'gtfs_gold.route_service_day.immutable_insert', side_effect=record), patch(
                'gtfs_gold.route_service_day._overwrite_scope', side_effect=write), patch.object(
                self.spark.catalog, 'tableExists', side_effect=lambda table: table.replace('`', '') in stored), patch.object(
                self.spark, 'table', side_effect=lambda table: stored[table.replace('`', '')]):
            result = run_route_service_day(self.spark, **ARGS, mode='publish')
        self.assertTrue(result['persisted'])
        self.assertEqual([(e['event_type'], e['status'], e['gold_committed']) for e in events],
                         [('STARTED', 'RUNNING', False), ('CLOSED', 'SUCCEEDED', True)])
        self.assertEqual(stored[target].count(), 5)


    def test_missing_table_is_not_zero(self):
        with patch.object(self.spark.catalog, 'tableExists', return_value=False):
            with self.assertRaisesRegex(ValueError, 'Falta'):
                _load_sources(self.spark, 'spark_catalog', 'fixture', VERSION, SHA)

    def test_window_migration_blocks_writer(self):
        from pyspark.sql import functions as F
        prepared = self.prepare()
        previous = prepared[0].withColumn('analysis_window_start', F.lit(date(2025, 12, 31)))
        events = []
        with patch('gtfs_gold.route_service_day.prepare_route_service_day', return_value=prepared), patch(
                'gtfs_gold.route_service_day.immutable_insert', side_effect=lambda spark, frame, table, keys: events.append(frame.first().asDict())), patch(
                'gtfs_gold.route_service_day._overwrite_scope') as writer, patch.object(
                self.spark.catalog, 'tableExists', return_value=True), patch.object(self.spark, 'table', return_value=previous):
            with self.assertRaisesRegex(ValueError, 'migración'):
                run_route_service_day(self.spark, **ARGS, mode='publish')
        writer.assert_not_called()
        self.assertEqual((events[-1]['status'], events[-1]['gold_committed']), ('FAILED', False))

    def test_failure_after_commit_preserves_committed_flag(self):
        from pyspark.sql import functions as F
        prepared = self.prepare()
        events = []
        wrong = prepared[0].withColumn('gold_run_id', F.lit('unexpected-run'))
        with patch('gtfs_gold.route_service_day.prepare_route_service_day', return_value=prepared), patch(
                'gtfs_gold.route_service_day.immutable_insert', side_effect=lambda spark, frame, table, keys: events.append(frame.first().asDict())), patch(
                'gtfs_gold.route_service_day._overwrite_scope'), patch.object(
                self.spark.catalog, 'tableExists', return_value=False), patch.object(self.spark, 'table', return_value=wrong):
            with self.assertRaisesRegex(RuntimeError, 'No confirmé'):
                run_route_service_day(self.spark, **ARGS, mode='publish')
        self.assertEqual((events[-1]['status'], events[-1]['gold_committed']), ('FAILED', True))


if __name__ == '__main__':
    unittest.main()
