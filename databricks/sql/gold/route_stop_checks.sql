-- Lectura posterior a publish. Parámetros catalog, schema, feed_version y snapshot_sha256.
select count(*) as rows,
       count(distinct struct(route_id, stop_id)) as distinct_pairs,
       count(distinct route_id) as routes_with_visits,
       count(distinct stop_id) as related_stops,
       sum(published_visit_count) as published_visits,
       count(distinct gold_run_id) as publication_runs
from identifier(:catalog || '.' || :schema || '.gold_gtfs_route_stop')
where source_feed_version = :feed_version and source_sha256 = :snapshot_sha256;

-- Detalle acotado de una ruta; LIMIT solo protege la inspección, no define los totales.
select b.route_id, b.stop_id, s.stop_name, s.stop_lat, s.stop_lon, s.location_type,
       b.declared_trip_count, b.published_visit_count
from identifier(:catalog || '.' || :schema || '.gold_gtfs_route_stop') b
join identifier(:catalog || '.' || :schema || '.silver_gtfs_stops') s
  on b.source_feed_version = s.source_feed_version and b.source_sha256 = s.source_sha256
 and b.stop_id = s.stop_id
where b.source_feed_version = :feed_version and b.source_sha256 = :snapshot_sha256
  and b.route_id = :route_id
order by b.stop_id
limit 500;
