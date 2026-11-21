-- Comprobación posterior a publish, con parámetros catalog, schema, feed_version y snapshot_sha256.
select timing_status, endpoint_time_precision,
       count(*) as declared_trips,
       sum(visit_count) as published_visits,
       sum(frequency_window_count) as frequency_windows
from identifier(:catalog || '.' || :schema || '.gold_gtfs_trip_timing')
where source_feed_version = :feed_version and source_sha256 = :snapshot_sha256
group by timing_status, endpoint_time_precision
order by timing_status, endpoint_time_precision;

-- Casos concretos: segundos de servicio sin aplicar módulo 24.
select trip_id, route_id, first_stop_id, last_stop_id, first_stop_sequence, last_stop_sequence,
       first_departure_time_seconds, last_arrival_time_seconds, timing_status,
       published_span_seconds, endpoint_time_precision
from identifier(:catalog || '.' || :schema || '.gold_gtfs_trip_timing')
where source_feed_version = :feed_version and source_sha256 = :snapshot_sha256
  and trip_id = :trip_id
limit 10;
