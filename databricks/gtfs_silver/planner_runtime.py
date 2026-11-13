"""Lecturas acotadas del planificador; solo publica task values si se solicita."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .planner import ENTITY_ORDER, bronze_snapshots, build_plan
from .publication import _versioned_table, quoted_table, simple_identifier

PLANNER_CONFIG = Path(__file__).resolve().parents[1] / "config/silver_planner.json"
BRONZE_FIELDS = (
    "quality_run_id", "event_type", "source_feed_version", "source_sha256", "rule_version",
    "started_at_utc", "completed_at_utc", "status", "total_checks", "blocking_failures", "warning_count",
    "validation_completed", "ready_for_silver", "warning_policy", "entity_inventory_json", "result_sha256",
)
AUDIT_FIELDS = (
    "entity", "source_feed_version", "source_sha256", "silver_run_id", "status", "silver_rule_version",
    "target_table", "candidate_rows", "input_rows", "rejected_rows", "silver_committed", "started_at_utc", "finished_at_utc",
)


def bounded_rows(frame: Any, limit: int, label: str) -> list[dict]:
    rows = frame.limit(limit + 1).collect()
    if len(rows) > limit:
        raise ValueError(f"{label} supera {limit} registros de metadata. Acota el rango de versiones; no se truncó el plan.")
    return [row.asDict(recursive=True) for row in rows]


def read_bronze_events(spark: Any, table: str, *, limit: int, feed_from: str = "", feed_to: str = "", hash_filter: str = "") -> tuple[list[dict], int]:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    if not spark.catalog.tableExists(quoted_table(table)):
        raise ValueError("Falta el cierre Bronze. Ejecuta notebook 07 completo antes de planificar.")
    frame, version = _versioned_table(spark, table, with_version=True)
    starts = frame.filter(F.col("event_type") == "STARTED")
    if hash_filter: starts = starts.filter(F.col("source_sha256") == hash_filter)
    if feed_from: starts = starts.filter(F.col("source_feed_version") >= feed_from)
    if feed_to: starts = starts.filter(F.col("source_feed_version") <= feed_to)
    window = Window.partitionBy("source_feed_version", "source_sha256").orderBy(F.col("started_at_utc").desc())
    latest = starts.withColumn("_rank", F.dense_rank().over(window)).filter(F.col("_rank") == 1)
    rows = bounded_rows(latest.select(*BRONZE_FIELDS), limit, "Intentos Bronze")
    if not rows: return [], version
    ids = [row["quality_run_id"] for row in rows]
    closed = frame.filter((F.col("event_type") == "CLOSED") & F.col("quality_run_id").isin(ids))
    return rows + bounded_rows(closed.select(*BRONZE_FIELDS), limit, "Cierres Bronze"), version


def _read_audits(spark: Any, table: str, scopes: Any, limit: int) -> tuple[list[dict], int | None]:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    if not spark.catalog.tableExists(quoted_table(table)): return [], None
    frame, version = _versioned_table(spark, table, with_version=True)
    scoped = frame.join(scopes, ["source_feed_version", "source_sha256"], "inner")
    window = Window.partitionBy("entity", "source_feed_version", "source_sha256").orderBy(F.col("started_at_utc").desc())
    latest = scoped.withColumn("_rank", F.dense_rank().over(window)).filter(F.col("_rank") == 1)
    return bounded_rows(latest.select(*AUDIT_FIELDS), limit, "Últimos intentos Silver"), version


def _target_states(spark: Any, scopes: Any, registry: dict, catalog: str, schema: str, limit: int) -> tuple[dict, dict]:
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType, DateType
    targets, versions = {}, {}
    scope_keys = [(row["source_feed_version"], row["source_sha256"]) for row in bounded_rows(scopes, limit, "Snapshots")]
    for entity, config in registry.items():
        if config.get("enabled") is not True: continue
        table = f"{catalog}.{schema}.silver_gtfs_{entity}"
        if not spark.catalog.tableExists(quoted_table(table)): continue
        try:
            frame, version = _versioned_table(spark, table, with_version=True)
            fields = {field.name: field.dataType for field in frame.schema.fields}
            technical = ("source_feed_version", "source_sha256", "silver_run_id", "silver_rule_version")
            if any(not isinstance(fields.get(name), StringType) for name in technical):
                raise ValueError("TARGET_TECHNICAL_SCHEMA_MISMATCH")
            selected = frame.join(scopes, ["source_feed_version", "source_sha256"], "inner")
            bad = F.lit(False)
            for name in technical:
                bad = bad | F.col(name).isNull() | (F.trim(F.col(name)) == "")
            metrics = [F.count("*").alias("rows"), F.sum(F.when(bad, 1).otherwise(0)).alias("invalid_technical_rows")]
            for column, label in (("silver_run_id", "run"), ("silver_rule_version", "rule")):
                metrics += [F.countDistinct(column).alias(label + "_count"), F.min(column).alias(label + "_min"), F.max(column).alias(label + "_max")]
            if entity == "service_dates":
                for column in ("analysis_window_start", "analysis_window_end"):
                    if not isinstance(fields.get(column), DateType): raise ValueError("SERVICE_DATES_WINDOW_COLUMNS_MISSING_OR_INVALID")
                    metrics += [F.min(column).alias(column + "_min"), F.max(column).alias(column + "_max"),
                                F.count(column).alias(column + "_count")]
            observed = bounded_rows(selected.groupBy("source_feed_version", "source_sha256").agg(*metrics), limit, f"Destinos {entity}")
            versions[table] = version
            for key in scope_keys: targets[(entity, *key)] = {"exists": True, "rows": 0, "run_ids": [], "rules": []}
            for row in observed:
                state = {"exists": True, "rows": row["rows"], "invalid_technical_rows": row["invalid_technical_rows"]}
                for label, output in (("run", "run_ids"), ("rule", "rules")):
                    state[output] = [row[label + "_min"]] if row[label + "_count"] == 1 else [row[label + "_min"], row[label + "_max"]]
                if entity == "service_dates":
                    values = []
                    for column in ("analysis_window_start", "analysis_window_end"):
                        low, high = row[column + "_min"], row[column + "_max"]
                        if low != high or low is None or row[column + "_count"] != row["rows"]: break
                        values.append(str(low))
                    state["windows"] = [values] if len(values) == 2 else []
                targets[(entity, row["source_feed_version"], row["source_sha256"])] = state
        except ValueError as error:
            for key in scope_keys: targets[(entity, *key)] = {"exists": True, "rows": 0, "error": str(error)}
    return targets, versions


def create_plan(spark: Any, *, catalog: str, schema: str, registry: dict, service_dates: dict | None = None,
                max_snapshots: int = 20, max_metadata_rows: int = 5000,
                feed_version_from: str = "", feed_version_to: str = "") -> dict:
    from datetime import date
    from pyspark.sql.types import StructType, StructField, StringType
    for value in (catalog, schema): simple_identifier(value)
    if type(max_metadata_rows) is not int or not 1 <= max_metadata_rows <= 10000:
        raise ValueError("max_metadata_rows debe estar entre 1 y 10000.")
    for value in (feed_version_from, feed_version_to):
        if value: date.fromisoformat(value)
    if feed_version_from and feed_version_to and feed_version_from > feed_version_to:
        raise ValueError("El rango de feed_version está invertido.")
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    policy = service_dates if service_dates is not None else json.loads(PLANNER_CONFIG.read_text(encoding="utf-8"))["service_dates"]
    bronze_table = f"{catalog}.{schema}.audit_gtfs_bronze_snapshot_runs"
    events, bronze_version = read_bronze_events(spark, bronze_table, limit=max_metadata_rows,
                                               feed_from=feed_version_from, feed_to=feed_version_to)
    ready = [entry for entry in bronze_snapshots(events) if not entry["reason"]]
    audits, targets, versions, audit_version = [], {}, {}, None
    if ready:
        scope_schema = StructType([StructField(name, StringType(), False) for name in ("source_feed_version", "source_sha256")])
        scopes = spark.createDataFrame([entry["key"] for entry in ready], scope_schema)
        audits, audit_version = _read_audits(spark, f"{catalog}.{schema}.audit_gtfs_silver_runs", scopes, max_metadata_rows)
        targets, versions = _target_states(spark, scopes, registry, catalog, schema, max_metadata_rows)
    plan = build_plan(events, audits, targets, registry, policy, catalog=catalog, schema=schema, max_snapshots=max_snapshots)
    plan["input_versions"] = {"bronze_closure": bronze_version, "silver_audit": audit_version, "targets": versions}
    return plan


def emit_plan(dbutils: Any, plan: dict) -> None:
    if plan["status"] == "BLOCKED":
        raise RuntimeError("El plan tiene bloqueos; revisa sus decisiones. No se entregaron listas al Job.")
    for entity in ENTITY_ORDER:
        key = "work_items" if entity == "agency" else entity + "_work_items"
        dbutils.jobs.taskValues.set(key=key, value=plan["work_items"].get(entity, []))
    dbutils.jobs.taskValues.set(key="plan_status", value=plan["status"])
    dbutils.jobs.taskValues.set(key="planned_count", value=plan["counts"]["PENDING"])
    dbutils.jobs.taskValues.set(key="deferred_count", value=plan["counts"]["DEFERRED"])


def assert_bronze_ready(spark: Any, *, catalog: str, schema: str, feed_version: str,
                        sha256: str, quality_run_id: str, result_sha256: str, entity: str = "",
                        bronze_delta_version: str = "") -> None:
    events, _ = read_bronze_events(spark, f"{catalog}.{schema}.audit_gtfs_bronze_snapshot_runs",
                                  limit=10, feed_from=feed_version, feed_to=feed_version, hash_filter=sha256)
    selected = [entry for entry in bronze_snapshots(events) if entry["key"] == (feed_version, sha256)]
    if (len(selected) != 1 or selected[0]["reason"] or selected[0]["start"]["quality_run_id"] != quality_run_id
            or selected[0]["closure"]["result_sha256"] != result_sha256):
        raise RuntimeError("El cierre Bronze cambió desde la planificación. Genera un plan nuevo.")
    if entity and entity != "service_dates":
        from .models import SOURCE_ENTITY_NAMES
        source = SOURCE_ENTITY_NAMES.get(entity, entity)
        recorded = selected[0]["inventory"][source]["delta_version"]
        if bronze_delta_version != str(recorded):
            raise RuntimeError("La versión Delta de la fuente no coincide con el cierre Bronze.")
