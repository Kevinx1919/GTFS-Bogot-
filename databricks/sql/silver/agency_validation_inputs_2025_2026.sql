-- Evidencia de lectura: consultas ejecutadas con Genie el 6 de noviembre de 2026.
-- Entorno de la revisión: workspace.gtfs_bogota. No es un pipeline genérico.
-- Resultados fuente transitorios; no se guardan filas en Git.

select
  source_feed_version,
  source_sha256,
  source_file_name,
  source_columns_json
from workspace.gtfs_bogota.audit_gtfs_source_schema_observations
where source_file_name = 'agency.txt'
  and (
    (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
    or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
  )
order by source_feed_version;

select
  agency_id,
  agency_name,
  agency_url,
  agency_timezone,
  agency_lang,
  agency_phone,
  agency_fare_url,
  cast(null as string) as agency_email,
  source_feed_version,
  source_sha256,
  source_file_path,
  unix_micros(bronze_loaded_at_utc) as bronze_loaded_at_epoch_us,
  count(*) over(partition by source_feed_version, source_sha256) as snapshot_row_count
from workspace.gtfs_bogota.bronze_gtfs_agency
where (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
   or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
order by source_feed_version, agency_id
limit 20;
