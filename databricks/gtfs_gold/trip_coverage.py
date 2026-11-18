"""Cobertura por viaje: preserva trips y agrega visitas/ventanas antes de unir."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import re
from typing import Any
from uuid import uuid4

from gtfs_bronze.contracts import quoted_table
from gtfs_bronze.discovery import iso_date
from gtfs_bronze.runtime import immutable_insert, pinned_table
from gtfs_silver.publication import _overwrite_scope

RULE_VERSION = "trip_coverage_v1"
SOURCE_RULES = {"trips": "trips_v1", "stop_times": "stop_times_v1", "frequencies": "frequencies_v1"}
AUDIT_DDL = """gold_run_id string, event_type string, entity string, source_feed_version string,
source_sha256 string, gold_rule_version string, status string, gold_committed boolean,
started_at_utc timestamp, finished_at_utc timestamp, candidate_rows bigint,
source_versions_json string, source_runs_json string, error_message string"""


def _identity(catalog: str, schema: str, feed_version: str, sha256: str) -> None:
    quoted_table(f"{catalog}.{schema}.configuration_check")
    iso_date(feed_version)
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("snapshot_sha256 debe contener 64 caracteres hexadecimales en minúsculas.")


def prepare_coverage(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str) -> tuple[Any, dict, dict]:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    _identity(catalog, schema, feed_version, sha256)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    audit_table = f"{catalog}.{schema}.audit_gtfs_silver_runs"
    if not spark.catalog.tableExists(quoted_table(audit_table)):
        raise ValueError("Falta la auditoría Silver; no puedo comprobar las fuentes Gold.")
    audits, audit_version = pinned_table(spark, audit_table)
    scoped = audits.filter((F.col("source_feed_version") == feed_version) & (F.col("source_sha256") == sha256)
                           & F.col("entity").isin(list(SOURCE_RULES)))
    rank = Window.partitionBy("entity").orderBy(F.col("started_at_utc").desc())
    rows = (scoped.withColumn("_rank", F.dense_rank().over(rank)).filter(F.col("_rank") == 1)
            .select("entity", "silver_run_id", "status", "silver_committed", "silver_rule_version", "target_table", "candidate_rows")
            .limit(4).collect())
    if len(rows) != 3 or {r["entity"] for r in rows} != set(SOURCE_RULES):
        raise ValueError("Necesito una publicación Silver vigente y única por cada fuente de cobertura.")
    sources, versions, runs, expected = {}, {"silver_audit": audit_version}, {}, {}
    for row in rows:
        entity = row["entity"]
        table = f"{catalog}.{schema}.silver_gtfs_{entity}"
        if (row["status"] != "SUCCEEDED" or row["silver_committed"] is not True
                or row["silver_rule_version"] != SOURCE_RULES[entity] or row["target_table"] != table
                or not row["silver_run_id"] or not row["candidate_rows"] or row["candidate_rows"] < 0):
            raise ValueError(f"La última publicación de {entity} no está disponible bajo su contrato; no publico Gold.")
        if not spark.catalog.tableExists(quoted_table(table)):
            raise ValueError(f"Falta {table}; no interpreto una fuente perdida como ausencia de datos.")
        frame, version = pinned_table(spark, table)
        frame = frame.filter((F.col("source_feed_version") == feed_version) & (F.col("source_sha256") == sha256))
        bad = (F.coalesce(F.col("silver_run_id") != F.lit(row["silver_run_id"]), F.lit(True))
               | F.coalesce(F.col("silver_rule_version") != F.lit(SOURCE_RULES[entity]), F.lit(True)))
        sources[entity] = frame.withColumn("_invalid_source", F.when(bad, 1).otherwise(0))
        versions[entity], runs[entity], expected[entity] = version, row["silver_run_id"], row["candidate_rows"]
    # Reconciliación técnica independiente: tampoco oculto visitas huérfanas fuera del left join.
    source_stats = None
    for entity, source in sources.items():
        stats = source.agg(F.count("*").alias("rows"), F.sum("_invalid_source").alias("invalid_rows")).withColumn("entity", F.lit(entity))
        source_stats = stats if source_stats is None else source_stats.unionByName(stats)
    for stats in source_stats.collect():
        if stats["rows"] != expected[stats["entity"]] or stats["invalid_rows"] != 0:
            raise ValueError("Una fuente Silver no coincide con su publicación auditada; no publico Gold.")
    keys = ["source_feed_version", "source_sha256", "trip_id"]
    visits = sources["stop_times"].groupBy(*keys).agg(
        F.count("*").alias("visit_count"),
        F.sum(F.when(F.col("arrival_time_seconds").isNotNull() & F.col("departure_time_seconds").isNotNull(), 1).otherwise(0)).alias("complete_time_pair_count"))
    frequencies = sources["frequencies"].groupBy(*keys).agg(
        F.count("*").alias("frequency_window_count"), F.min("exact_times_effective").alias("_minimum_exact"),
        F.max("exact_times_effective").alias("_maximum_exact"),
        F.sum(F.when(F.col("exact_times_effective").isNull() | ~F.col("exact_times_effective").isin(0, 1), 1).otherwise(0)).alias("_invalid_exact"))
    joined = sources["trips"].select(*keys, "route_id", "service_id").join(visits, keys, "left").join(frequencies, keys, "left")
    context = (F.when(F.col("frequency_window_count").isNull(), "sin_frecuencias")
               .when((F.col("_minimum_exact") == 0) & (F.col("_maximum_exact") == 0), "por_frecuencia")
               .when((F.col("_minimum_exact") == 1) & (F.col("_maximum_exact") == 1), "horario_exacto_por_frecuencia")
               .otherwise("contexto_inconsistente"))
    coverage = (joined.withColumn("scheduling_context", context)
                .fillna(0, subset=["visit_count", "complete_time_pair_count", "frequency_window_count", "_invalid_exact"])
                .withColumn("coverage_status", F.when(F.col("visit_count") == 0, "sin_visitas").when(F.col("visit_count") == 1, "una_visita").otherwise("varias_visitas"))
                .withColumn("visits_without_complete_time_pair", F.col("visit_count") - F.col("complete_time_pair_count")))
    bad = ((F.col("_invalid_exact") > 0)
           | (F.col("scheduling_context") == "contexto_inconsistente") | F.col("trip_id").isNull()
           | (F.trim(F.col("trip_id")) == ""))
    metrics = coverage.agg(F.count("*").alias("candidate_rows"), F.countDistinct("trip_id").alias("distinct_trips"),
                           F.sum("visit_count").alias("published_visits"), F.sum("frequency_window_count").alias("frequency_windows"),
                           F.sum(F.when(bad, 1).otherwise(0)).alias("invalid_rows"),
                           *[F.sum(F.when(F.col("coverage_status") == status, 1).otherwise(0)).alias(status)
                             for status in ("sin_visitas", "una_visita", "varias_visitas")]).first().asDict()
    if (metrics["candidate_rows"] != expected["trips"] or metrics["distinct_trips"] != expected["trips"]
            or metrics["published_visits"] != expected["stop_times"] or metrics["frequency_windows"] != expected["frequencies"]
            or metrics["invalid_rows"] != 0):
        raise ValueError("Cobertura no reconciliada, fuente modificada o contexto incompatible; no publico Gold.")
    columns = [*keys, "route_id", "service_id", "visit_count", "complete_time_pair_count",
               "visits_without_complete_time_pair", "frequency_window_count", "coverage_status", "scheduling_context"]
    return coverage.select(*columns), {**metrics, "reconciled": True, "rule_version": RULE_VERSION}, {"versions": versions, "runs": runs}


def run_coverage(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str, mode: str = "validate") -> dict:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    target = f"{catalog}.{schema}.gold_gtfs_trip_coverage"
    audit = f"{catalog}.{schema}.audit_gtfs_gold_runs"
    run_id, started, committed = str(uuid4()), datetime.now(timezone.utc), False
    result, references = {}, {"versions": {}, "runs": {}}
    def record(event: str, status: str, error: str | None = None) -> None:
        row = {"gold_run_id": run_id, "event_type": event, "entity": "trip_coverage", "source_feed_version": feed_version,
               "source_sha256": sha256, "gold_rule_version": RULE_VERSION, "status": status, "gold_committed": committed,
               "started_at_utc": started, "finished_at_utc": None if event == "STARTED" else datetime.now(timezone.utc),
               "candidate_rows": result.get("candidate_rows"), "source_versions_json": json.dumps(references["versions"], sort_keys=True),
               "source_runs_json": json.dumps(references["runs"], sort_keys=True), "error_message": error}
        immutable_insert(spark, spark.createDataFrame([row], AUDIT_DDL), audit, ["gold_run_id", "event_type"])
    if mode == "publish":
        record("STARTED", "RUNNING")
    try:
        frame, result, references = prepare_coverage(spark, catalog=catalog, schema=schema, feed_version=feed_version, sha256=sha256)
        if mode == "publish":
            output = (frame.withColumn("gold_run_id", F.lit(run_id)).withColumn("gold_rule_version", F.lit(RULE_VERSION))
                      .withColumn("gold_loaded_at_utc", F.lit(started).cast("timestamp")))
            predicate = f"source_feed_version = '{feed_version}' and source_sha256 = '{sha256}'"
            _overwrite_scope(output, target, predicate)
            committed = True
            current = spark.table(quoted_table(target)).where(predicate)
            checked = current.agg(F.count("*").alias("rows"), F.countDistinct("trip_id").alias("ids"),
                                  F.countDistinct("gold_run_id").alias("runs"), F.min("gold_run_id").alias("run_id")).first()
            if (checked["rows"] != result["candidate_rows"] or checked["ids"] != result["candidate_rows"]
                    or checked["runs"] != 1 or checked["run_id"] != run_id):
                raise RuntimeError("No confirmé la publicación Gold; revisa la auditoría antes de continuar.")
            record("CLOSED", "SUCCEEDED")
        return {"status": "SUCCEEDED" if committed else "VALIDATED", "persisted": committed, "gold_run_id": run_id,
                "table": target, **result, "source_references": references}
    except Exception as error:
        if mode == "publish":
            record("CLOSED", "FAILED", str(error)[:2000])
        raise
