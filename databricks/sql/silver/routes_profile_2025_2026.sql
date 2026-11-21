-- Perfil inicial de routes; consultas de solo lectura ejecutadas con Genie el 2026-11-06.
-- Conservo consultas exitosas. Un intento DISTINCT OVER falló y fue corregido por Genie.
-- Los resultados agregados están en docs/routes_profile_2025_2026.md.

-- Consulta 1
select
  source_feed_version,
  source_sha256,
  source_file_name,
  source_columns_json
from workspace.gtfs_bogota.audit_gtfs_source_schema_observations
where source_file_name = 'routes.txt'
  and (
    (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
    or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
  )
order by source_feed_version;

-- Consulta 2
with routes_2025 as (
  select '2025-10-28' as snapshot, route_id, agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where source_feed_version = '2025-10-28'
    and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
), routes_2026 as (
  select '2026-09-29' as snapshot, route_id, agency_id, route_short_name, route_long_name, cast(null as string) as route_desc, route_type, route_color, route_text_color
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where source_feed_version = '2026-09-29'
    and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097'
), combined as (
  select * from routes_2025
  union all
  select * from routes_2026
), cells as (
  select snapshot,
    stack(8,
      'route_id', route_id,
      'agency_id', agency_id,
      'route_short_name', route_short_name,
      'route_long_name', route_long_name,
      'route_desc', route_desc,
      'route_type', route_type,
      'route_color', route_color,
      'route_text_color', route_text_color
    ) as (field_name, field_value)
  from combined
)
select
  snapshot,
  field_name,
  count(*) as total_rows,
  sum(case when field_value is null then 1 else 0 end) as nulls,
  sum(case when field_value = '' then 1 else 0 end) as empty_exact,
  sum(case when field_value rlike r'^\s+$' then 1 else 0 end) as whitespace_only,
  sum(case when field_value is not null and field_value <> '' and not(field_value rlike r'^\s*$')
           and field_value <> regexp_replace(field_value, r'^\s+|\s+$', '') then 1 else 0 end) as edge_whitespace,
  count(distinct case when field_value is not null and not(field_value rlike r'^\s*$') then field_value end) as cardinality
from cells
group by snapshot, field_name
order by snapshot, field_name;

-- Consulta 3
with routes_combined as (
  select
    source_feed_version as snapshot,
    route_type,
    route_color,
    route_text_color
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
     or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
), route_type_dist as (
  select
    snapshot,
    route_type,
    count(*) as route_count
  from routes_combined
  group by snapshot, route_type
), color_examples as (
  select
    snapshot,
    collect_set(case when route_color is not null and route_color <> '' and not(route_color rlike r'^\s*$') then route_color end) as distinct_route_colors,
    collect_set(case when route_text_color is not null and route_text_color <> '' and not(route_text_color rlike r'^\s*$') then route_text_color end) as distinct_route_text_colors
  from routes_combined
  group by snapshot
)
select
  rtd.snapshot,
  rtd.route_type,
  rtd.route_count,
  ce.distinct_route_colors,
  ce.distinct_route_text_colors
from route_type_dist rtd
join color_examples ce on rtd.snapshot = ce.snapshot
order by rtd.snapshot, rtd.route_type;

-- Consulta 4
select
  source_feed_version as snapshot,
  count(*) as total_silver_agency_rows,
  count(distinct agency_id) as distinct_agency_ids,
  count(distinct silver_rule_version) as distinct_rule_versions,
  collect_set(silver_rule_version) as rule_versions
from workspace.gtfs_bogota.silver_gtfs_agency
where (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
   or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
group by source_feed_version
order by source_feed_version;

-- Consulta 5
with bronze_routes as (
  select
    source_feed_version,
    source_sha256,
    route_id,
    agency_id
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
     or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
), silver_agency as (
  select
    source_feed_version,
    source_sha256,
    agency_id
  from workspace.gtfs_bogota.silver_gtfs_agency
  where (source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
     or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
)
select
  br.source_feed_version as snapshot,
  count(*) as routes_without_silver_agency,
  count(distinct br.agency_id) as distinct_orphan_agency_ids
from bronze_routes br
left join silver_agency sa
  on br.source_feed_version = sa.source_feed_version
  and br.source_sha256 = sa.source_sha256
  and br.agency_id = sa.agency_id
where sa.agency_id is null
  and br.agency_id is not null
  and not(br.agency_id rlike r'^\s*$')
group by br.source_feed_version
order by br.source_feed_version;

-- Consulta 6
with routes_2025 as (
  select route_id, agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where source_feed_version = '2025-10-28'
    and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
), routes_2026 as (
  select route_id, agency_id, route_short_name, route_long_name, route_type, route_color, route_text_color
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where source_feed_version = '2026-09-29'
    and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097'
), metrics_2025 as (
  select
    '2025-10-28' as snapshot,
    count(*) as total_rows,
    sum(case when route_id is null or route_id = '' or route_id rlike r'^\s*$' then 1 else 0 end) as id_null_empty_blank,
    sum(case when route_id is not null and route_id <> '' and not(route_id rlike r'^\s*$')
             and route_id <> regexp_replace(route_id, r'^\s+|\s+$', '') then 1 else 0 end) as id_edge_whitespace,
    count(distinct case when route_id is not null and not(route_id rlike r'^\s*$') then route_id end) as distinct_ids,
    count(*) - count(distinct struct(route_id, agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color)) as duplicate_business_rows,
    (select count(distinct route_id)
     from (
       select route_id
       from routes_2025
       where route_id is not null and not(route_id rlike r'^\s*$')
       group by route_id
       having count(distinct struct(agency_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color)) > 1
     )
    ) as ids_with_different_attributes
  from routes_2025
), metrics_2026 as (
  select
    '2026-09-29' as snapshot,
    count(*) as total_rows,
    sum(case when route_id is null or route_id = '' or route_id rlike r'^\s*$' then 1 else 0 end) as id_null_empty_blank,
    sum(case when route_id is not null and route_id <> '' and not(route_id rlike r'^\s*$')
             and route_id <> regexp_replace(route_id, r'^\s+|\s+$', '') then 1 else 0 end) as id_edge_whitespace,
    count(distinct case when route_id is not null and not(route_id rlike r'^\s*$') then route_id end) as distinct_ids,
    count(*) - count(distinct struct(route_id, agency_id, route_short_name, route_long_name, route_type, route_color, route_text_color)) as duplicate_business_rows,
    (select count(distinct route_id)
     from (
       select route_id
       from routes_2026
       where route_id is not null and not(route_id rlike r'^\s*$')
       group by route_id
       having count(distinct struct(agency_id, route_short_name, route_long_name, route_type, route_color, route_text_color)) > 1
     )
    ) as ids_with_different_attributes
  from routes_2026
)
select * from metrics_2025
union all
select * from metrics_2026
order by snapshot;

-- Consulta 7
select
  route_id,
  route_short_name
from workspace.gtfs_bogota.bronze_gtfs_routes
where source_feed_version = '2025-10-28'
  and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
  and route_long_name is null
limit 5;

-- Consulta 8
with routes_2025 as (
  select
    '2025-10-28' as expected_version,
    '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952' as expected_hash,
    '/Volumes/workspace/gtfs_bogota/staging_gtfs/gtfs_static/feed_version=2025-10-28/sha256=07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952/routes.txt' as expected_path,
    route_id, route_short_name, route_long_name, route_desc, route_type, route_color, route_text_color,
    agency_id, source_feed_version, source_sha256, source_file_path, bronze_loaded_at_utc
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where source_feed_version = '2025-10-28'
    and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
), routes_2026 as (
  select
    '2026-09-29' as expected_version,
    '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097' as expected_hash,
    '/Volumes/workspace/gtfs_bogota/staging_gtfs/gtfs_static/feed_version=2026-09-29/sha256=08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097/routes.txt' as expected_path,
    route_id, route_short_name, route_long_name, cast(null as string) as route_desc, route_type, route_color, route_text_color,
    agency_id, source_feed_version, source_sha256, source_file_path, bronze_loaded_at_utc
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where source_feed_version = '2026-09-29'
    and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097'
), validation_2025 as (
  select
    expected_version as snapshot,
    expected_hash as hash,
    count(*) as total_rows,
    sum(case when (route_short_name is null or route_short_name = '' or route_short_name rlike r'^\s*$')
             and (route_long_name is null or route_long_name = '' or route_long_name rlike r'^\s*$') then 1 else 0 end) as both_names_empty,
    sum(case when route_type is null or route_type = '' or not(route_type rlike r'^\d+$')
             or cast(route_type as int) not in (0,1,2,3,4,5,6,7,11,12) then 1 else 0 end) as invalid_route_type,
    sum(case when (route_color is not null and route_color <> '' and not(route_color rlike r'^\s*$')
                   and not(route_color rlike r'^[0-9A-Fa-f]{6}$'))
             or (route_text_color is not null and route_text_color <> '' and not(route_text_color rlike r'^\s*$')
                   and not(route_text_color rlike r'^[0-9A-Fa-f]{6}$')) then 1 else 0 end) as invalid_colors,
    sum(case when route_id rlike r'[\x00-\x1F\x7F]' or route_short_name rlike r'[\x00-\x1F\x7F]'
             or route_long_name rlike r'[\x00-\x1F\x7F]' or route_desc rlike r'[\x00-\x1F\x7F]'
             or agency_id rlike r'[\x00-\x1F\x7F]' or route_type rlike r'[\x00-\x1F\x7F]'
             or route_color rlike r'[\x00-\x1F\x7F]' or route_text_color rlike r'[\x00-\x1F\x7F]' then 1 else 0 end) as control_chars,
    sum(case when source_feed_version <> expected_version then 1 else 0 end) as wrong_version,
    sum(case when bronze_loaded_at_utc is null then 1 else 0 end) as null_loaded_at,
    sum(case when source_file_path is null or source_file_path <> expected_path then 1 else 0 end) as wrong_file_path,
    sum(case when route_desc is not null and route_desc <> '' and not(route_desc rlike r'^\s*$')
             and (route_desc = route_short_name or route_desc = route_long_name) then 1 else 0 end) as desc_equals_name
  from routes_2025
  group by expected_version, expected_hash
), validation_2026 as (
  select
    expected_version as snapshot,
    expected_hash as hash,
    count(*) as total_rows,
    sum(case when (route_short_name is null or route_short_name = '' or route_short_name rlike r'^\s*$')
             and (route_long_name is null or route_long_name = '' or route_long_name rlike r'^\s*$') then 1 else 0 end) as both_names_empty,
    sum(case when route_type is null or route_type = '' or not(route_type rlike r'^\d+$')
             or cast(route_type as int) not in (0,1,2,3,4,5,6,7,11,12) then 1 else 0 end) as invalid_route_type,
    sum(case when (route_color is not null and route_color <> '' and not(route_color rlike r'^\s*$')
                   and not(route_color rlike r'^[0-9A-Fa-f]{6}$'))
             or (route_text_color is not null and route_text_color <> '' and not(route_text_color rlike r'^\s*$')
                   and not(route_text_color rlike r'^[0-9A-Fa-f]{6}$')) then 1 else 0 end) as invalid_colors,
    sum(case when route_id rlike r'[\x00-\x1F\x7F]' or route_short_name rlike r'[\x00-\x1F\x7F]'
             or route_long_name rlike r'[\x00-\x1F\x7F]' or agency_id rlike r'[\x00-\x1F\x7F]'
             or route_type rlike r'[\x00-\x1F\x7F]' or route_color rlike r'[\x00-\x1F\x7F]'
             or route_text_color rlike r'[\x00-\x1F\x7F]' then 1 else 0 end) as control_chars,
    sum(case when source_feed_version <> expected_version then 1 else 0 end) as wrong_version,
    sum(case when bronze_loaded_at_utc is null then 1 else 0 end) as null_loaded_at,
    sum(case when source_file_path is null or source_file_path <> expected_path then 1 else 0 end) as wrong_file_path,
    0 as desc_equals_name
  from routes_2026
  group by expected_version, expected_hash
)
select * from validation_2025
union all
select * from validation_2026
order by snapshot;

-- Consulta 9
with routes_both_names_empty as (
  select
    source_feed_version as snapshot,
    route_id,
    route_short_name,
    route_long_name,
    agency_id
  from workspace.gtfs_bogota.bronze_gtfs_routes
  where ((source_feed_version = '2025-10-28' and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
      or (source_feed_version = '2026-09-29' and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097'))
    and (route_short_name is null or route_short_name = '' or route_short_name rlike r'^\s*$')
    and (route_long_name is null or route_long_name = '' or route_long_name rlike r'^\s*$')
  limit 5
)
select * from routes_both_names_empty
order by snapshot, route_id;
