-- Perfilado de solo lectura ejecutado para agency, snapshot 2025-10-28.
-- Entorno actual: workspace.gtfs_bogota; no es un pipeline genérico.
-- No usar estos campos de duplicados para otra versión sin revisar su encabezado.
-- El hash y la fecha fijan el snapshot; no se fijó una versión Delta.
-- Consulta 1: métricas de texto. agency_fare_url no estuvo publicada en 2025.
with snapshot as (
select agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone, agency_fare_url from workspace.gtfs_bogota.bronze_gtfs_agency where source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
), cells as (
select stack(7, 'agency_id', agency_id, 'agency_name', agency_name, 'agency_url', agency_url, 'agency_timezone', agency_timezone, 'agency_lang', agency_lang, 'agency_phone', agency_phone, 'agency_fare_url', agency_fare_url) as (field_name, field_value)
from snapshot
)
select field_name, count(*) as snapshot_rows,
sum(case when field_value is null then 1 else 0 end) as null_count,
sum(case when field_value = '' then 1 else 0 end) as empty_count,
sum(case when field_value rlike r'^\s+$' then 1 else 0 end) as whitespace_only_count,
sum(case when field_value is not null and not(field_value rlike r'^\s*$') then 1 else 0 end) as non_blank_count,
count(distinct case when field_value is not null and not(field_value rlike r'^\s*$') then field_value end) as distinct_non_blank_count,
sum(case when field_value is not null and not(field_value rlike r'^\s*$') and field_value <> regexp_replace(field_value, r'^\s+|\s+$', '') then 1 else 0 end) as edge_whitespace_count
from cells
group by field_name
order by field_name;

-- Consulta 2: duplicados de negocio con las seis columnas publicadas.
with snapshot as (
select agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone, agency_fare_url from workspace.gtfs_bogota.bronze_gtfs_agency where source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
), key_counts as (
select agency_id, count(*) as row_count,
count(distinct struct(agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone)) as business_variants
from snapshot
where agency_id is not null and not(agency_id rlike r'^\s*$')
group by agency_id
), trim_keys as (
select regexp_replace(agency_id, r'^\s+|\s+$', '') as id_after_trim,
count(distinct agency_id) as original_variants
from snapshot
where agency_id is not null and not(agency_id rlike r'^\s*$')
group by regexp_replace(agency_id, r'^\s+|\s+$', '')
), overall as (
select count(*) as total_rows,
count(*) - count(distinct struct(agency_id, agency_name, agency_url, agency_timezone, agency_lang, agency_phone)) as identical_extra_rows,
sum(case when agency_id is null or agency_id rlike r'^\s*$' then 1 else 0 end) as blank_id_rows
from snapshot
), key_summary as (
select count(*) as distinct_non_blank_ids,
count(case when row_count > 1 then 1 end) as repeated_id_groups,
count(case when business_variants > 1 then 1 end) as conflicting_id_groups
from key_counts
), trim_summary as (
select count(case when original_variants > 1 then 1 end) as potential_trim_collision_groups
from trim_keys
)
select overall.total_rows, overall.identical_extra_rows, overall.blank_id_rows,
key_summary.distinct_non_blank_ids, key_summary.repeated_id_groups, key_summary.conflicting_id_groups,
trim_summary.potential_trim_collision_groups
from overall cross join key_summary cross join trim_summary;
