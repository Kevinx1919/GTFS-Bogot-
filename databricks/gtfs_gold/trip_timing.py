"""Extremos horarios publicados por viaje; no calcula duración observada ni expande frecuencias."""
from __future__ import annotations
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4
import json
from gtfs_bronze.contracts import quoted_table
from gtfs_bronze.runtime import pinned_table, immutable_insert
from gtfs_silver.publication import _overwrite_scope
from .trip_coverage import _identity, AUDIT_DDL
from .route_service_day import _latest_silver

RULE_VERSION = "trip_timing_v1"
KEYS = ["source_feed_version", "source_sha256"]
SOURCE_RULES = {"trips": "trips_v1", "stop_times": "stop_times_v1", "frequencies": "frequencies_v1"}
STATUSES = ["no_visits", "one_visit", "frequency_template", "missing_endpoints", "reversed_endpoints", "eligible"]


def _load_sources(spark: Any, catalog: str, schema: str, version: str, sha: str) -> tuple[dict, dict]:
    from pyspark.sql import functions as F
    prefix = f"{catalog}.{schema}"
    audit_name = f"{prefix}.audit_gtfs_silver_runs"
    if not spark.catalog.tableExists(quoted_table(audit_name)):
        raise ValueError("Falta la auditoría Silver de horarios.")
    audits, audit_version = pinned_table(spark, audit_name)
    scope = (F.col("source_feed_version") == version) & (F.col("source_sha256") == sha)
    audits = audits.filter(scope)
    frames, versions, runs = {}, {"silver_audit": audit_version}, {}
    for entity, rule in SOURCE_RULES.items():
        table = f"{prefix}.silver_gtfs_{entity}"
        row = _latest_silver(audits, entity, table, rule)
        if not spark.catalog.tableExists(quoted_table(table)):
            raise ValueError(f"Falta {table}; no interpreto una fuente perdida como cero.")
        frame, versions[entity] = pinned_table(spark, table)
        frame = frame.filter(scope)
        bad = F.coalesce((F.col("silver_run_id") != row["silver_run_id"]) | (F.col("silver_rule_version") != rule), F.lit(True))
        stats = frame.agg(F.count("*").alias("rows"), F.max(bad.cast("int")).alias("bad")).first()
        if stats["rows"] != row["candidate_rows"] or stats["bad"] != 0:
            raise ValueError(f"{entity} no coincide con su publicación auditada.")
        frames[entity], runs[entity] = frame, row["silver_run_id"]
    return frames, {"versions": versions, "runs": runs}


def build_trip_timing(trips: Any, visits: Any, frequencies: Any) -> Any:
    from pyspark.sql import functions as F
    key = [*KEYS, "trip_id"]
    # El struct selecciona la visita extrema por secuencia, incluso si su hora es null.
    point = F.struct("stop_sequence", "stop_id", "departure_time_seconds", "arrival_time_seconds", "timepoint_effective")
    endpoints = visits.groupBy(*key).agg(F.count("*").alias("visit_count"), F.min(point).alias("_first"), F.max(point).alias("_last"))
    windows = frequencies.groupBy(*key).agg(F.count("*").alias("frequency_window_count"))
    frame = (trips.select(*key, "route_id", "service_id").join(endpoints, key, "left").join(windows, key, "left")
             .fillna(0, subset=["visit_count", "frequency_window_count"])
             .withColumn("first_stop_id", F.col("_first.stop_id")).withColumn("last_stop_id", F.col("_last.stop_id"))
             .withColumn("first_stop_sequence", F.col("_first.stop_sequence")).withColumn("last_stop_sequence", F.col("_last.stop_sequence"))
             .withColumn("first_departure_time_seconds", F.col("_first.departure_time_seconds"))
             .withColumn("last_arrival_time_seconds", F.col("_last.arrival_time_seconds"))
             .withColumn("is_frequency_template", F.col("frequency_window_count") > 0))
    precision = (F.when(F.col("_first.timepoint_effective").isNull() | F.col("_last.timepoint_effective").isNull(), "unknown")
                 .when((F.col("_first.timepoint_effective") == 0) | (F.col("_last.timepoint_effective") == 0), "approximate")
                 .otherwise("exact_as_published"))
    span = F.col("last_arrival_time_seconds") - F.col("first_departure_time_seconds")
    status = (F.when(F.col("visit_count") == 0, "no_visits").when(F.col("visit_count") == 1, "one_visit")
              .when(F.col("is_frequency_template"), "frequency_template")
              .when(span.isNull(), "missing_endpoints").when(span < 0, "reversed_endpoints").otherwise("eligible"))
    frame = (frame.withColumn("endpoint_time_precision", precision).withColumn("timing_status", status)
             .withColumn("published_span_seconds", F.when(F.col("timing_status") == "eligible", span).cast("long")))
    return frame.select(*key, "route_id", "service_id", "visit_count", "first_stop_id", "last_stop_id",
                        "first_stop_sequence", "last_stop_sequence", "first_departure_time_seconds", "last_arrival_time_seconds",
                        "frequency_window_count", "is_frequency_template", "endpoint_time_precision", "timing_status", "published_span_seconds")


def prepare_trip_timing(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str) -> tuple[Any, dict, dict]:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    sources, references = _load_sources(spark, catalog, schema, feed_version, sha256)
    primary = {"trips": ["trip_id"], "stop_times": ["trip_id", "stop_sequence"], "frequencies": ["trip_id", "start_time_seconds"]}
    counts = {}
    for name, frame in sources.items():
        required = primary[name] + (["route_id", "service_id"] if name == "trips" else ["stop_id"] if name == "stop_times" else [])
        bad = F.lit(False)
        for column in required:
            bad = bad | F.col(column).isNull()
            if column.endswith("_id"):
                bad = bad | (F.trim(F.col(column)) == "") | (F.trim(F.col(column)) != F.col(column))
            else:
                bad = bad | (F.col(column) < 0)
        if name == "stop_times":
            bad = bad | (F.col("arrival_time_seconds") < 0) | (F.col("departure_time_seconds") < 0)
            bad = bad | (F.col("timepoint_effective").isNotNull() & ~F.col("timepoint_effective").isin(0, 1))
        # Las horas opcionales null son válidas; no convierto el booleano SQL desconocido en un rechazo.
        stats = frame.agg(F.count("*").alias("rows"), F.countDistinct(*primary[name]).alias("ids"),
                          F.max(F.when(bad, 1).otherwise(0)).alias("bad")).first()
        if not stats["rows"] or stats["rows"] != stats["ids"] or stats["bad"] != 0:
            raise ValueError(f"Claves u horas inválidas en {name}.")
        counts[name] = stats["rows"]
    trips, visits, frequencies = [sources[n] for n in ("trips", "stop_times", "frequencies")]
    for frame in (visits, frequencies):
        if frame.select(*KEYS, "trip_id").distinct().join(trips.select(*KEYS, "trip_id"), [*KEYS, "trip_id"], "left_anti").limit(1).count():
            raise ValueError("Referencia huérfana a trip_id; no descarto registros horarios.")
    output = build_trip_timing(trips, visits, frequencies)
    result = output.agg(F.count("*").alias("candidate_rows"), F.countDistinct("trip_id").alias("distinct_trips"),
                        F.sum("visit_count").alias("published_visits"), F.sum("frequency_window_count").alias("frequency_windows"),
                        *[F.sum(F.when(F.col("timing_status") == status, 1).otherwise(0)).alias(status) for status in STATUSES]).first().asDict()
    if (result["candidate_rows"] != counts["trips"] or result["distinct_trips"] != counts["trips"]
            or result["published_visits"] != counts["stop_times"] or result["frequency_windows"] != counts["frequencies"]
            or sum(result[s] for s in STATUSES) != counts["trips"]):
        raise ValueError("Los extremos horarios no reconcilian con sus fuentes.")
    return output, {**result, "reconciled": True, "rule_version": RULE_VERSION}, references


def run_trip_timing(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str, mode: str = "validate") -> dict:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    target = f"{catalog}.{schema}.gold_gtfs_trip_timing"
    audit = f"{catalog}.{schema}.audit_gtfs_gold_runs"
    run_id, started, committed = str(uuid4()), datetime.now(timezone.utc), False
    result, references = {}, {"versions": {}, "runs": {}}
    def record(event: str, status: str, error: str | None = None) -> None:
        row = {"gold_run_id": run_id, "event_type": event, "entity": "trip_timing", "source_feed_version": feed_version,
               "source_sha256": sha256, "gold_rule_version": RULE_VERSION, "status": status, "gold_committed": committed,
               "started_at_utc": started, "finished_at_utc": None if event == "STARTED" else datetime.now(timezone.utc),
               "candidate_rows": result.get("candidate_rows"), "source_versions_json": json.dumps(references["versions"], sort_keys=True),
               "source_runs_json": json.dumps(references["runs"], sort_keys=True), "error_message": error}
        immutable_insert(spark, spark.createDataFrame([row], AUDIT_DDL), audit, ["gold_run_id", "event_type"])
    if mode == "publish":
        record("STARTED", "RUNNING")
    try:
        frame, result, references = prepare_trip_timing(spark, catalog=catalog, schema=schema, feed_version=feed_version, sha256=sha256)
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
