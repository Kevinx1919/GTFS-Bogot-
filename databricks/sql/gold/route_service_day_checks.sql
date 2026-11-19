-- Consultas de lectura tras publicar Gold. Parámetros de consulta de Databricks:
-- catalog=workspace, schema=gtfs_bogota, feed_version=2026-09-29,
-- snapshot_sha256=08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097.
-- IDENTIFIER mantiene el nombre de tabla fuera de la interpolación SQL.

-- Una fila diaria resume las rutas y los dos tipos de programación declarada.
select service_date,
       count(distinct route_id) as routes_with_programming,
       sum(trips_without_frequency_count) as trips_without_frequency,
       sum(frequency_template_count) as frequency_templates
from identifier(:catalog || '.' || :schema || '.gold_gtfs_route_service_day')
where source_feed_version = :feed_version
  and source_sha256 = :snapshot_sha256
  and service_date in (date '2026-11-19', date '2026-11-21', date '2026-11-22')
group by service_date
order by service_date;

-- La clave debe ser única y las dos particiones deben conciliar.
select count(*) as rows,
       count(distinct struct(route_id, service_date)) as distinct_route_dates,
       sum(case when declared_trip_count <> trips_without_frequency_count + frequency_template_count
                     or declared_trip_count <> trips_without_visits_count + trips_with_one_visit_count + trips_with_multiple_visits_count
                then 1 else 0 end) as unreconciled_rows,
       min(service_date) as first_active_date,
       max(service_date) as last_active_date
from identifier(:catalog || '.' || :schema || '.gold_gtfs_route_service_day')
where source_feed_version = :feed_version and source_sha256 = :snapshot_sha256;
