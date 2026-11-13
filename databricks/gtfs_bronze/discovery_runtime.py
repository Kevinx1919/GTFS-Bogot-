"""Lecturas Delta de control y procedencia; no escribe tablas analíticas."""
from __future__ import annotations
from typing import Any

from .contracts import ENTITY_NAMES, quoted_table
from .discovery import build_ingestion_plan, validate_selection
from .runtime import pinned_table

CATALOG_FIELDS = ("feed_version", "source_url", "is_direct_zip_url", "portal_modified_at_utc", "portal_item_id")


def create_ingestion_plan(spark: Any, *, catalog: str, schema: str, max_metadata_rows: int = 5000,
                          selection_mode: str = "latest_uningested", explicit_version: str = "",
                          start_date: str = "", end_date: str = "", max_versions: int = 1,
                          reprocess_completed: bool = False) -> dict:
    from pyspark.sql import functions as F
    from gtfs_silver.planner import bronze_snapshots
    from gtfs_silver.planner_runtime import bounded_rows, read_bronze_events
    from gtfs_silver.planner_recovery import load_resolutions
    quoted_table(f"{catalog}.{schema}.configuration_check")
    if type(max_metadata_rows) is not int or not 1 <= max_metadata_rows <= 10000:
        raise ValueError("max_metadata_rows debe estar entre 1 y 10000.")
    options = dict(selection_mode=selection_mode, explicit_version=explicit_version, start_date=start_date,
                   end_date=end_date, max_versions=max_versions, reprocess_completed=reprocess_completed)
    validate_selection(**options)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    control = f"{catalog}.{schema}.control_gtfs_static_catalog"
    if not spark.catalog.tableExists(quoted_table(control)):
        raise ValueError("Falta el catálogo de control; ejecuta los bloques 1 a 4 de notebook 06.")
    frame, control_version = pinned_table(spark, control)
    if explicit_version:
        frame = frame.filter(F.col("feed_version") == explicit_version)
    if start_date:
        frame = frame.filter(F.col("feed_version").between(start_date, end_date))
    rows = bounded_rows(frame.select(*CATALOG_FIELDS), max_metadata_rows, "Catálogo de versiones")
    lower, upper = (explicit_version, explicit_version) if explicit_version else (start_date, end_date)
    resolutions, resolution_version = load_resolutions(spark, catalog, schema, max_metadata_rows)
    applied = []
    closure = f"{catalog}.{schema}.audit_gtfs_bronze_snapshot_runs"
    events, closure_version = [], None
    if spark.catalog.tableExists(quoted_table(closure)):
        events, closure_version = read_bronze_events(spark, closure, limit=max_metadata_rows,
                                                    feed_from=lower, feed_to=upper, resolutions=resolutions,
                                                    applied_resolutions=applied)
    # Busco evidencia huérfana solo para versiones sin intento de cierre vigente.
    # Estas proyecciones técnicas pueden leer archivos grandes; no perfilan columnas de negocio.
    certified_or_attempted = {state["key"][0] for state in bronze_snapshots(events)}
    unknown = {row["feed_version"] for row in rows} - certified_or_attempted
    observed, versions = set(), {}
    names = ["audit_gtfs_source_schema_observations", *["bronze_gtfs_" + entity for entity in sorted(ENTITY_NAMES)]]
    for name in names:
        if not unknown:
            break
        table = f"{catalog}.{schema}.{name}"
        if not spark.catalog.tableExists(quoted_table(table)):
            continue
        evidence, version = pinned_table(spark, table)
        found = bounded_rows(evidence.select("source_feed_version")
                             .filter(F.col("source_feed_version").isin(sorted(unknown))).distinct(),
                             max_metadata_rows, "Procedencia sin cierre")
        observed.update(row["source_feed_version"] for row in found)
        unknown -= observed
        versions[table] = version
    plan = build_ingestion_plan(rows, events, observed_versions=observed, **options)
    plan["resolved_attempts"] = applied
    plan["input_versions"] = {"catalog": control_version, "bronze_closure": closure_version,
                               "resolutions": resolution_version, "provenance": versions}
    return plan


def emit_ingestion_plan(dbutils: Any, plan: dict) -> None:
    if plan["status"] == "BLOCKED":
        raise RuntimeError("El plan Bronze tiene bloqueos; no entregué listas al Job. Revisa las decisiones.")
    for key, value in (("ingestion_work_items", plan["work_items"]), ("ingestion_plan_status", plan["status"]),
                       ("planned_count", len(plan["work_items"])), ("deferred_count", plan["counts"]["DEFERRED"])):
        dbutils.jobs.taskValues.set(key=key, value=value)
