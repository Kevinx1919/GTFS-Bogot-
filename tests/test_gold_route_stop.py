"""Puente de red con Spark real y fuentes/escritor Delta sustituidos por dobles."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'databricks'))
from gtfs_gold.route_stop import prepare_route_stop, run_route_stop, build_route_stops, _load_sources, SOURCE_RULES

V, H = '2026-09-29', 'a'*64
ARGS = dict(catalog='spark_catalog', schema='fixture', feed_version=V, sha256=H)
HAS_SPARK = bool(importlib.util.find_spec('pyspark') and shutil.which('java'))

@unittest.skipUnless(HAS_SPARK, 'Requiere Spark y Java configurados, sin descargas.')
class RouteStopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pyspark.sql import SparkSession
        cls.spark = (SparkSession.builder.master('local[1]').appName('route-stop-tests')
                     .config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','1').getOrCreate())
        cls.spark.sparkContext.setLogLevel('ERROR')
    @classmethod
    def tearDownClass(cls): cls.spark.stop()
    def setUp(self):
        self.frames = {}
        fixtures = {
            'routes': ([('r1',),('r2',),('r3',)], 'route_id string'),
            'trips': ([('t1','r1'),('t2','r1'),('t3','r2'),('no-visits','r3')], 'trip_id string, route_id string'),
            'stop_times': ([('t1',1,'s1'),('t1',2,'s1'),('t2',1,'s1'),('t2',2,'s2'),('t3',1,'s1')], 'trip_id string, stop_sequence long, stop_id string'),
            'stops': ([('s1',0,4.6,-74.1),('s2',None,4.7,-74.2),('parent',1,4.6,-74.1)], 'stop_id string, location_type int, stop_lat double, stop_lon double')}
        from pyspark.sql import functions as F
        for name,(rows,schema) in fixtures.items():
            self.frames[name] = (self.spark.createDataFrame(rows,schema).withColumn('source_feed_version',F.lit(V))
                                 .withColumn('source_sha256',F.lit(H)).withColumn('silver_run_id',F.lit(name+'-run'))
                                 .withColumn('silver_rule_version',F.lit(SOURCE_RULES[name])))
    def prepare(self):
        with patch('gtfs_gold.route_stop._load_sources',return_value=(self.frames,{'versions':{},'runs':{}})):
            return prepare_route_stop(self.spark,**ARGS)
    def test_repeated_visits_and_shared_stop_preserve_grain_and_totals(self):
        frame,result,_ = self.prepare();rows={(r.route_id,r.stop_id):r for r in frame.collect()}
        self.assertEqual(set(rows),{('r1','s1'),('r1','s2'),('r2','s1')})
        self.assertEqual((rows['r1','s1'].published_visit_count,rows['r1','s1'].declared_trip_count),(3,2))
        self.assertEqual((result['published_visits'],result['related_stops'],result['routes_without_visits']),(5,2,1))
        self.assertNotIn('stop_lat',frame.columns)
    def test_duplicate_trip_key_fails(self):
        self.frames['trips']=self.frames['trips'].unionByName(self.frames['trips'].limit(1))
        with self.assertRaisesRegex(ValueError,'duplicadas'):self.prepare()
    def test_duplicate_visit_sequence_fails(self):
        self.frames['stop_times']=self.frames['stop_times'].unionByName(self.frames['stop_times'].limit(1))
        with self.assertRaisesRegex(ValueError,'duplicadas'):self.prepare()
    def test_duplicate_stop_key_fails(self):
        self.frames['stops']=self.frames['stops'].unionByName(self.frames['stops'].limit(1))
        with self.assertRaisesRegex(ValueError,'duplicadas'):self.prepare()
    def test_orphan_trip_is_not_dropped(self):
        from pyspark.sql import functions as F
        self.frames['stop_times']=self.frames['stop_times'].withColumn('trip_id',F.when(F.col('trip_id')=='t3',F.lit('missing')).otherwise(F.col('trip_id')))
        with self.assertRaisesRegex(ValueError,'huérfana trip_id'):self.prepare()
    def test_orphan_stop_is_not_dropped(self):
        from pyspark.sql import functions as F
        self.frames['stop_times']=self.frames['stop_times'].withColumn('stop_id',F.lit('missing'))
        with self.assertRaisesRegex(ValueError,'huérfana stop_id'):self.prepare()
    def test_orphan_route_fails(self):
        from pyspark.sql import functions as F
        self.frames['trips']=self.frames['trips'].withColumn('route_id',F.lit('missing'))
        with self.assertRaisesRegex(ValueError,'huérfana route_id'):self.prepare()
    def test_parent_station_cannot_replace_platform(self):
        from pyspark.sql import functions as F
        self.frames['stop_times']=self.frames['stop_times'].withColumn('stop_id',F.lit('parent'))
        with self.assertRaisesRegex(ValueError,'parada/plataforma'):self.prepare()
    def test_missing_coordinates_are_reported_without_inventing_points(self):
        from pyspark.sql import functions as F
        self.frames['stops']=self.frames['stops'].withColumn('stop_lat',F.lit(None).cast('double'))
        _,result,_=self.prepare();self.assertEqual(result['related_stops_without_coordinates'],2)
    def test_foreign_snapshot_cannot_join(self):
        from pyspark.sql import functions as F
        visits=self.frames['stop_times'].withColumn('source_sha256',F.lit('b'*64))
        self.assertEqual(build_route_stops(self.frames['trips'],visits).count(),0)
    def test_validate_does_not_write(self):
        prepared=self.prepare()
        with patch('gtfs_gold.route_stop.prepare_route_stop',return_value=prepared),patch('gtfs_gold.route_stop.immutable_insert') as audit,patch('gtfs_gold.route_stop._overwrite_scope') as writer:
            result=run_route_stop(self.spark,**ARGS)
        self.assertFalse(result['persisted']);audit.assert_not_called();writer.assert_not_called()
    def test_publication_checks_unique_pair_and_records_commit(self):
        prepared=self.prepare();stored={};events=[];target='spark_catalog.fixture.gold_gtfs_route_stop'
        def write(frame,table,predicate):
            self.assertEqual(predicate,f"source_feed_version = '{V}' and source_sha256 = '{H}'");stored[table]=frame
        with patch('gtfs_gold.route_stop.prepare_route_stop',return_value=prepared),patch('gtfs_gold.route_stop.immutable_insert',side_effect=lambda spark,frame,table,keys:events.append(frame.first().asDict())),patch('gtfs_gold.route_stop._overwrite_scope',side_effect=write),patch.object(self.spark,'table',side_effect=lambda name:stored[name.replace('`','')]):
            result=run_route_stop(self.spark,**ARGS,mode='publish')
        self.assertTrue(result['persisted']);self.assertEqual(result['candidate_rows'],3)
        self.assertEqual([(e['event_type'],e['gold_committed'])for e in events],[('STARTED',False),('CLOSED',True)])
    def test_source_metadata_drift_is_rejected(self):
        from pyspark.sql import functions as F
        self.frames['trips']=self.frames['trips'].withColumn('silver_run_id',F.lit('tampered'))
        self.check_loader(raises=True)
    def test_audited_sources_are_pinned(self):
        frames,refs=self.check_loader();self.assertEqual(set(frames),set(SOURCE_RULES));self.assertEqual(len(refs['versions']),5)
    def check_loader(self,raises=False):
        prefix='spark_catalog.fixture';tables={f'{prefix}.silver_gtfs_{n}':f for n,f in self.frames.items()}
        tables[prefix+'.audit_gtfs_silver_runs']=self.frames['routes']
        def latest(audits,entity,table,rule):return {'silver_run_id':entity+'-run','candidate_rows':{'routes':3,'trips':4,'stop_times':5,'stops':3}[entity]}
        with patch.object(self.spark.catalog,'tableExists',return_value=True),patch('gtfs_gold.route_stop.pinned_table',side_effect=lambda spark,table:(tables[table],2)),patch('gtfs_gold.route_stop._latest_silver',side_effect=latest):
            if raises:
                with self.assertRaisesRegex(ValueError,'auditada'):_load_sources(self.spark,'spark_catalog','fixture',V,H)
            else:return _load_sources(self.spark,'spark_catalog','fixture',V,H)
    def test_missing_table_is_not_empty_network(self):
        with patch.object(self.spark.catalog,'tableExists',return_value=False):
            with self.assertRaisesRegex(ValueError,'Falta'):_load_sources(self.spark,'spark_catalog','fixture',V,H)


    def test_later_failed_publication_is_not_bypassed(self):
        with patch.object(self.spark.catalog,'tableExists',return_value=True),patch('gtfs_gold.route_stop.pinned_table',return_value=(self.frames['routes'],1)),patch('gtfs_gold.route_stop._latest_silver',side_effect=ValueError('última publicación fallida')):
            with self.assertRaisesRegex(ValueError,'última publicación'):_load_sources(self.spark,'spark_catalog','fixture',V,H)
    def test_failure_after_commit_retains_commit_evidence(self):
        from pyspark.sql import functions as F
        prepared=self.prepare();events=[]
        wrong=prepared[0].withColumn('gold_run_id',F.lit('unexpected'))
        with patch('gtfs_gold.route_stop.prepare_route_stop',return_value=prepared),patch('gtfs_gold.route_stop.immutable_insert',side_effect=lambda spark,frame,table,keys:events.append(frame.first().asDict())),patch('gtfs_gold.route_stop._overwrite_scope'),patch.object(self.spark,'table',return_value=wrong):
            with self.assertRaisesRegex(RuntimeError,'No confirmé'):run_route_stop(self.spark,**ARGS,mode='publish')
        self.assertEqual((events[-1]['status'],events[-1]['gold_committed']),('FAILED',True))

if __name__=='__main__':unittest.main()
