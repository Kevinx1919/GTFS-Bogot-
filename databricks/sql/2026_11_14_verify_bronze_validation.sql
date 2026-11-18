-- Verificación de solo lectura de la validación Bronze 2026.
-- Este UUID identifica una corrida de calidad; no es el ID de ejecución del Job.
-- Las tres consultas se ejecutaron mediante Genie el 14 de noviembre de 2026.

-- 1. Contrasto la regla y la identidad registradas en inicio y cierre.
select quality_run_id, event_type, source_feed_version, source_sha256,
       rule_version, started_at_utc, completed_at_utc, status, total_checks,
       blocking_failures, warning_count, validation_completed, ready_for_silver,
       warning_policy, coordinator_run_id
from workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_runs
where quality_run_id = '6bccbeb8-4d57-4042-8ef7-5c81fa700bd3'
order by event_type
limit 10;

-- 2. Reconcilio la cantidad de controles con el resumen del cierre.
select status, severity, count(*) as checks
from workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_quality
where quality_run_id = '6bccbeb8-4d57-4042-8ef7-5c81fa700bd3'
group by status, severity
order by status, severity;

-- 3. Identifico las advertencias y cualquier fallo de esta evaluación.
select check_name, entity_name, status, severity, details
from workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_quality
where quality_run_id = '6bccbeb8-4d57-4042-8ef7-5c81fa700bd3'
  and status in ('FAIL', 'WARN')
order by entity_name
limit 20;
