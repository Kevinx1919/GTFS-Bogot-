"""Puente de catálogo ruta–ubicación; conserva visitas repetidas como diagnóstico."""
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

RULE_VERSION = "route_stop_v1"
KEYS = ["source_feed_version", "source_sha256"]
SOURCE_RULES = {"routes": "routes_v1", "trips": "trips_v1", "stop_times": "stop_times_v1", "stops": "stops_v1"}
PRIMARY_KEYS = {"routes": ["route_id"], "trips": ["trip_id"], "stops": ["stop_id"], "stop_times": ["trip_id", "stop_sequence"]}


def _load_sources(spark: Any, catalog: str, schema: str, version: str, sha: str) -> tuple[dict, dict]:
    from pyspark.sql import functions as F
    prefix = f"{catalog}.{schema}"
    audit_name = f"{prefix}.audit_gtfs_silver_runs"
    if not spark.catalog.tableExists(quoted_table(audit_name)):
        raise ValueError("Falta la auditoría Silver para validar la red publicada.")
    audits, audit_version = pinned_table(spark, audit_name)
    scope = (F.col("source_feed_version") == version) & (F.col("source_sha256") == sha)
    audits = audits.filter(scope)
    sources, versions, runs = {}, {"silver_audit": audit_version}, {}
    for entity, rule in SOURCE_RULES.items():
        table = f"{prefix}.silver_gtfs_{entity}"
        row = _latest_silver(audits, entity, table, rule)
        if not spark.catalog.tableExists(quoted_table(table)):
            raise ValueError(f"Falta {table}; no publico una red incompleta.")
        frame, versions[entity] = pinned_table(spark, table)
        frame = frame.filter(scope)
        bad = F.coalesce((F.col("silver_run_id") != row["silver_run_id"]) | (F.col("silver_rule_version") != rule), F.lit(True))
        stats = frame.agg(F.count("*").alias("rows"), F.max(bad.cast("int")).alias("bad")).first()
        if stats["rows"] != row["candidate_rows"] or stats["bad"] != 0:
            raise ValueError(f"{entity} no coincide con su publicación auditada.")
        sources[entity], runs[entity] = frame, row["silver_run_id"]
    return sources, {"versions": versions, "runs": runs}


def build_route_stops(trips: Any, visits: Any) -> Any:
    """Reduce visitas a viaje–ubicación antes de unir con el catálogo de viajes."""
    from pyspark.sql import functions as F
    trip_stops = visits.groupBy(*KEYS, "trip_id", "stop_id").agg(F.count("*").alias("_visits"))
    linked = trip_stops.join(trips.select(*KEYS, "trip_id", "route_id"), [*KEYS, "trip_id"], "inner")
    return linked.groupBy(*KEYS, "route_id", "stop_id").agg(
        F.sum("_visits").cast("long").alias("published_visit_count"),
        F.count("*").alias("declared_trip_count"))


def prepare_route_stop(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str) -> tuple[Any, dict, dict]:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    sources, references = _load_sources(spark, catalog, schema, feed_version, sha256)
    counts = {}
    # Compruebo claves antes de unir: ningún duplicado puede multiplicar relaciones.
    for entity, frame in sources.items():
        primary = PRIMARY_KEYS[entity]
        bad = F.lit(False)
        required = primary + (["route_id"] if entity == "trips" else ["stop_id"] if entity == "stop_times" else [])
        for column in required:
            bad = bad | F.col(column).isNull()
            if column != "stop_sequence":
                bad = bad | (F.trim(F.col(column)) == "") | (F.trim(F.col(column)) != F.col(column))
        if entity == "stop_times":
            bad = bad | (F.col("stop_sequence") < 0)
        stats = frame.agg(F.count("*").alias("rows"), F.countDistinct(*primary).alias("ids"),
                          F.max(bad.cast("int")).alias("bad")).first()
        if not stats["rows"] or stats["rows"] != stats["ids"] or stats["bad"] != 0:
            raise ValueError(f"Claves inválidas o duplicadas en {entity}; no publico Gold.")
        counts[entity] = stats["rows"]
    trips, visits, stops, routes = [sources[name] for name in ("trips", "stop_times", "stops", "routes")]
    for child, parent, key in [(trips.select(*KEYS, "route_id").distinct(), routes, "route_id"),
                                (visits.select(*KEYS, "trip_id").distinct(), trips, "trip_id"),
                                (visits.select(*KEYS, "stop_id").distinct(), stops, "stop_id")]:
        if child.join(parent.select(*KEYS, key), [*KEYS, key], "left_anti").limit(1).count():
            raise ValueError(f"Referencia huérfana {key}; no descarto visitas ni rutas silenciosamente.")
    linked_stops = visits.select(*KEYS, "stop_id").distinct().join(stops, [*KEYS, "stop_id"], "inner")
    if linked_stops.filter(F.coalesce(F.col("location_type"), F.lit(0)) != 0).limit(1).count():
        raise ValueError("Una visita apunta a otra clase de ubicación; el contrato requiere parada/plataforma.")
    output = build_route_stops(trips, visits)
    result = output.agg(F.count("*").alias("candidate_rows"), F.countDistinct("route_id", "stop_id").alias("distinct_pairs"),
                        F.countDistinct("route_id").alias("routes_with_visits"), F.countDistinct("stop_id").alias("related_stops"),
                        F.sum("published_visit_count").alias("published_visits"),
                        F.max(F.when((F.col("declared_trip_count") < 1) | (F.col("published_visit_count") < F.col("declared_trip_count")), 1).otherwise(0)).alias("invalid_rows")).first().asDict()
    if (not result["candidate_rows"] or result["candidate_rows"] != result["distinct_pairs"]
            or result["published_visits"] != counts["stop_times"] or result["invalid_rows"] != 0):
        raise ValueError("La relación ruta–ubicación no reconcilia; no publico Gold.")
    missing_coordinates = linked_stops.filter(F.col("stop_lat").isNull() | F.col("stop_lon").isNull()).count()
    return output, {**result, "catalog_routes": counts["routes"],
                    "routes_without_visits": counts["routes"] - result["routes_with_visits"],
                    "related_stops_without_coordinates": missing_coordinates,
                    "reconciled": True, "rule_version": RULE_VERSION}, references


def run_route_stop(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str, mode: str = "validate") -> dict:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    target = f"{catalog}.{schema}.gold_gtfs_route_stop"
    audit = f"{catalog}.{schema}.audit_gtfs_gold_runs"
    run_id, started, committed = str(uuid4()), datetime.now(timezone.utc), False
    result, references = {}, {"versions": {}, "runs": {}}
    def record(event: str, status: str, error: str | None = None) -> None:
        row = {"gold_run_id": run_id, "event_type": event, "entity": "route_stop", "source_feed_version": feed_version,
               "source_sha256": sha256, "gold_rule_version": RULE_VERSION, "status": status, "gold_committed": committed,
               "started_at_utc": started, "finished_at_utc": None if event == "STARTED" else datetime.now(timezone.utc),
               "candidate_rows": result.get("candidate_rows"), "source_versions_json": json.dumps(references["versions"], sort_keys=True),
               "source_runs_json": json.dumps(references["runs"], sort_keys=True), "error_message": error}
        immutable_insert(spark, spark.createDataFrame([row], AUDIT_DDL), audit, ["gold_run_id", "event_type"])
    if mode == "publish":
        record("STARTED", "RUNNING")
    try:
        frame, result, references = prepare_route_stop(spark, catalog=catalog, schema=schema, feed_version=feed_version, sha256=sha256)
        if mode == "publish":
            output = (frame.withColumn("gold_run_id", F.lit(run_id)).withColumn("gold_rule_version", F.lit(RULE_VERSION))
                      .withColumn("gold_loaded_at_utc", F.lit(started).cast("timestamp")))
            predicate = f"source_feed_version = '{feed_version}' and source_sha256 = '{sha256}'"
            _overwrite_scope(output, target, predicate)
            committed = True
            current = spark.table(quoted_table(target)).where(predicate)
            checked = current.agg(F.count("*").alias("rows"), F.countDistinct("route_id", "stop_id").alias("ids"),
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
