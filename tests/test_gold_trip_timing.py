"""Extremos publicados: casos sintéticos con Spark real y IO Delta sustituido."""
from pathlib import Path
import importlib.util
import shutil
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'databricks'))
from gtfs_gold.trip_timing import prepare_trip_timing, run_trip_timing, build_trip_timing, _load_sources, SOURCE_RULES
V,H='2026-09-29','a'*64
ARGS=dict(catalog='spark_catalog',schema='fixture',feed_version=V,sha256=H)
HAS_SPARK=bool(importlib.util.find_spec('pyspark') and shutil.which('java'))

@unittest.skipUnless(HAS_SPARK,'Requiere Spark y Java configurados; sin descargas.')
class TripTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark=(SparkSession.builder.master('local[1]').appName('trip-timing-tests').config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','1').getOrCreate());cls.spark.sparkContext.setLogLevel('ERROR')
    @classmethod
    def tearDownClass(cls):cls.spark.stop()
    def setUp(self):
        from pyspark.sql import functions as F
        trips=[(t,'r','svc')for t in ['zero','one','late','approx','missing','reverse','frequency','unknown']]
        visits=[('one',1,'s1',100,100,1),('late',20,'s1',90000,89990,1),('late',25,'s2',None,None,0),('late',30,'s3',94000,93900,1),
                ('approx',1,'s1',100,90,0),('approx',2,'s2',310,300,1),('missing',1,'s1',None,100,0),('missing',2,'s2',250,240,1),
                ('reverse',1,'s1',500,490,1),('reverse',2,'s2',300,290,1),('frequency',1,'s1',0,0,1),('frequency',2,'s2',620,600,1),
                ('unknown',1,'s1',100,100,None),('unknown',2,'s2',300,280,1)]
        fixtures={'trips':(trips,'trip_id string, route_id string, service_id string'),
                  'stop_times':(visits,'trip_id string, stop_sequence long, stop_id string, departure_time_seconds long, arrival_time_seconds long, timepoint_effective int'),
                  'frequencies':([('frequency',0),('frequency',1000)],'trip_id string, start_time_seconds long')}
        self.frames={}
        for name,(rows,schema) in fixtures.items():
            self.frames[name]=(self.spark.createDataFrame(rows,schema).withColumn('source_feed_version',F.lit(V)).withColumn('source_sha256',F.lit(H)).withColumn('silver_run_id',F.lit(name+'-run')).withColumn('silver_rule_version',F.lit(SOURCE_RULES[name])))
    def prepare(self):
        with patch('gtfs_gold.trip_timing._load_sources',return_value=(self.frames,{'versions':{},'runs':{}})):
            return prepare_trip_timing(self.spark,**ARGS)
    def rows(self):return {r.trip_id:r for r in build_trip_timing(self.frames['trips'],self.frames['stop_times'],self.frames['frequencies']).collect()}
    def test_categories_preserve_all_trips_and_reconcile_visits(self):
        frame,result,_=self.prepare();self.assertEqual(result['candidate_rows'],8);self.assertEqual(result['published_visits'],14);self.assertEqual(result['frequency_windows'],2)
        self.assertEqual([result[s]for s in ['no_visits','one_visit','frequency_template','missing_endpoints','reversed_endpoints','eligible']],[1,1,1,1,1,3])
    def test_actual_endpoint_sequence_and_hours_over_24(self):
        r=self.rows()['late'];self.assertEqual((r.first_stop_sequence,r.last_stop_sequence),(20,30));self.assertEqual((r.first_departure_time_seconds,r.last_arrival_time_seconds,r.published_span_seconds),(90000,93900,3900))
        self.assertEqual(r.endpoint_time_precision,'exact_as_published')
    def test_missing_first_departure_is_not_replaced_by_next_non_null(self):
        r=self.rows()['missing'];self.assertIsNone(r.first_departure_time_seconds);self.assertIsNone(r.published_span_seconds);self.assertEqual(r.timing_status,'missing_endpoints')
    def test_one_and_zero_visits_are_not_durations(self):
        rows=self.rows()
        for t,status in [('zero','no_visits'),('one','one_visit')]:self.assertEqual(rows[t].timing_status,status);self.assertIsNone(rows[t].published_span_seconds)
    def test_two_windows_do_not_duplicate_frequency_template(self):
        r=self.rows()['frequency'];self.assertEqual(r.frequency_window_count,2);self.assertTrue(r.is_frequency_template);self.assertIsNone(r.published_span_seconds)
    def test_unknown_and_approximate_precision_are_preserved(self):
        rows=self.rows();self.assertEqual(rows['unknown'].endpoint_time_precision,'unknown');self.assertEqual(rows['approx'].endpoint_time_precision,'approximate');self.assertEqual(rows['unknown'].published_span_seconds,180)
    def test_reversed_endpoint_is_diagnosed_not_corrected(self):
        r=self.rows()['reverse'];self.assertEqual(r.timing_status,'reversed_endpoints');self.assertIsNone(r.published_span_seconds)
    def test_duplicate_sequence_fails(self):
        self.frames['stop_times']=self.frames['stop_times'].unionByName(self.frames['stop_times'].limit(1))
        with self.assertRaisesRegex(ValueError,'inválidas'):self.prepare()
    def test_orphan_frequency_is_not_ignored(self):
        from pyspark.sql import functions as F
        self.frames['frequencies']=self.frames['frequencies'].withColumn('trip_id',F.lit('missing-trip'))
        with self.assertRaisesRegex(ValueError,'huérfana'):self.prepare()
    def test_null_hour_does_not_hide_negative_other_hour(self):
        from pyspark.sql import functions as F
        self.frames['stop_times']=self.frames['stop_times'].withColumn('arrival_time_seconds',F.lit(None).cast('long')).withColumn('departure_time_seconds',F.lit(-1))
        with self.assertRaisesRegex(ValueError,'inválidas'):self.prepare()
    def test_foreign_source_cannot_join(self):
        from pyspark.sql import functions as F
        other=self.frames['stop_times'].withColumn('source_sha256',F.lit('b'*64));rows=build_trip_timing(self.frames['trips'],other,self.frames['frequencies']).collect();self.assertTrue(all(r.visit_count==0 for r in rows))
    def test_validate_does_not_write(self):
        prepared=self.prepare()
        with patch('gtfs_gold.trip_timing.prepare_trip_timing',return_value=prepared),patch('gtfs_gold.trip_timing.immutable_insert')as audit,patch('gtfs_gold.trip_timing._overwrite_scope')as writer:
            r=run_trip_timing(self.spark,**ARGS)
        self.assertFalse(r['persisted']);audit.assert_not_called();writer.assert_not_called()
    def test_scoped_publication_and_commit_check(self):
        prepared=self.prepare();stored={};events=[]
        def write(frame,table,predicate):
            self.assertEqual(predicate,f"source_feed_version = '{V}' and source_sha256 = '{H}'");stored[table]=frame
        with patch('gtfs_gold.trip_timing.prepare_trip_timing',return_value=prepared),patch('gtfs_gold.trip_timing.immutable_insert',side_effect=lambda spark,frame,table,keys:events.append(frame.first().asDict())),patch('gtfs_gold.trip_timing._overwrite_scope',side_effect=write),patch.object(self.spark,'table',side_effect=lambda name:stored[name.replace('`','')]):
            r=run_trip_timing(self.spark,**ARGS,mode='publish')
        self.assertTrue(r['persisted']);self.assertEqual(events[-1]['status'],'SUCCEEDED');self.assertTrue(events[-1]['gold_committed'])
    def test_missing_source_does_not_become_no_frequency(self):
        with patch.object(self.spark.catalog,'tableExists',return_value=False):
            with self.assertRaisesRegex(ValueError,'Falta'):_load_sources(self.spark,'spark_catalog','fixture',V,H)
    def test_latest_failed_source_is_not_bypassed(self):
        with patch.object(self.spark.catalog,'tableExists',return_value=True),patch('gtfs_gold.trip_timing.pinned_table',return_value=(self.frames['trips'],1)),patch('gtfs_gold.trip_timing._latest_silver',side_effect=ValueError('última publicación fallida')):
            with self.assertRaisesRegex(ValueError,'última publicación'):_load_sources(self.spark,'spark_catalog','fixture',V,H)


    def test_pinned_source_metadata_matches_audit(self):
        frames,refs=self.loader();self.assertEqual(set(frames),set(SOURCE_RULES));self.assertEqual(len(refs['versions']),4)
    def test_source_metadata_drift_is_rejected(self):
        from pyspark.sql import functions as F
        self.frames['stop_times']=self.frames['stop_times'].withColumn('silver_run_id',F.lit('modified'))
        with self.assertRaisesRegex(ValueError,'auditada'):self.loader()
    def loader(self):
        prefix='spark_catalog.fixture';tables={f'{prefix}.silver_gtfs_{n}':f for n,f in self.frames.items()};tables[prefix+'.audit_gtfs_silver_runs']=self.frames['trips']
        def latest(audits,entity,table,rule):return {'silver_run_id':entity+'-run','candidate_rows':{'trips':8,'stop_times':14,'frequencies':2}[entity]}
        with patch.object(self.spark.catalog,'tableExists',return_value=True),patch('gtfs_gold.trip_timing.pinned_table',side_effect=lambda spark,table:(tables[table],4)),patch('gtfs_gold.trip_timing._latest_silver',side_effect=latest):
            return _load_sources(self.spark,'spark_catalog','fixture',V,H)

if __name__=='__main__':unittest.main()
