"""Oferta declarada por ruta y día; agrega por servicio antes de aplicar fechas."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from typing import Any
from uuid import uuid4

from gtfs_bronze.contracts import quoted_table
from gtfs_bronze.runtime import immutable_insert, pinned_table
from gtfs_silver.publication import _overwrite_scope
from .trip_coverage import AUDIT_DDL, SOURCE_RULES, _identity

RULE_VERSION = "route_service_day_v1"
KEYS = ["source_feed_version", "source_sha256"]
COUNTS = ["declared_trip_count", "trips_without_frequency_count", "frequency_template_count",
          "frequency_window_count", "trips_without_visits_count", "trips_with_one_visit_count",
          "trips_with_multiple_visits_count"]


def analysis_window(start: str, end: str) -> tuple[date, date]:
    """Exige un horizonte explícito y acotado; no deduce fechas desde la versión."""
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError) as error:
        raise ValueError("window_start y window_end deben ser fechas ISO YYYY-MM-DD.") from error
    if first.isoformat() != start or last.isoformat() != end or not 1 <= (last - first).days + 1 <= 366:
        raise ValueError("El horizonte debe ser ISO, ordenado y contener entre 1 y 366 días.")
    return first, last


def aggregate_days(coverage: Any, service_dates: Any) -> Any:
    """Transformación distribuida: una fila por identidad, ruta y fecha activa."""
    from pyspark.sql import functions as F
    by_service = coverage.groupBy(*KEYS, "route_id", "service_id").agg(
        F.count("*").alias("declared_trip_count"),
        F.sum(F.when(F.col("frequency_window_count") == 0, 1).otherwise(0)).alias("trips_without_frequency_count"),
        F.sum(F.when(F.col("frequency_window_count") > 0, 1).otherwise(0)).alias("frequency_template_count"),
        F.sum("frequency_window_count").alias("frequency_window_count"),
        *[F.sum(F.when(F.col("coverage_status") == value, 1).otherwise(0)).alias(name)
          for value, name in [("sin_visitas", "trips_without_visits_count"), ("una_visita", "trips_with_one_visit_count"),
                              ("varias_visitas", "trips_with_multiple_visits_count")]])
    active = by_service.join(service_dates.select(*KEYS, "service_id", "service_date", "source_temporal_warning"),
                             [*KEYS, "service_id"], "inner")
    return active.groupBy(*KEYS, "route_id", "service_date").agg(
        *[F.sum(name).cast("long").alias(name) for name in COUNTS],
        F.count("*").alias("active_service_count"),
        F.max(F.col("source_temporal_warning").cast("int")).cast("boolean").alias("source_temporal_warning"))


def _latest_silver(audits: Any, entity: str, table: str, rule: str, run: str | None = None) -> dict:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    rows = (audits.filter(F.col("entity") == entity)
            .withColumn("_rank", F.dense_rank().over(Window.orderBy(F.col("started_at_utc").desc())))
            .filter(F.col("_rank") == 1).limit(2).collect())
    if len(rows) != 1:
        raise ValueError(f"Necesito una publicación Silver vigente y única para {entity}.")
    row = rows[0].asDict()
    if (row["status"] != "SUCCEEDED" or row["silver_committed"] is not True
            or row["silver_rule_version"] != rule or row["target_table"] != table
            or not row["silver_run_id"] or (run is not None and row["silver_run_id"] != run)
            or not isinstance(row["candidate_rows"], int) or row["candidate_rows"] < 1):
        raise ValueError(f"La última publicación de {entity} no está disponible o cobertura quedó desactualizada.")
    return row


def _load_sources(spark: Any, catalog: str, schema: str, version: str, sha: str) -> tuple[Any, Any, dict]:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    prefix = f"{catalog}.{schema}"
    names = {"silver_audit": f"{prefix}.audit_gtfs_silver_runs", "gold_audit": f"{prefix}.audit_gtfs_gold_runs",
             "trip_coverage": f"{prefix}.gold_gtfs_trip_coverage", "service_dates": f"{prefix}.silver_gtfs_service_dates"}
    frames, versions = {}, {}
    for name, table in names.items():
        if not spark.catalog.tableExists(quoted_table(table)):
            raise ValueError(f"Falta {table}; no sustituyo una fuente ausente por cero.")
        frame, versions[name] = pinned_table(spark, table)
        frames[name] = frame.filter((F.col("source_feed_version") == version) & (F.col("source_sha256") == sha))
    latest = (frames["gold_audit"].filter(F.col("entity") == "trip_coverage")
              .withColumn("_rank", F.dense_rank().over(Window.orderBy(F.col("started_at_utc").desc())))
              .filter(F.col("_rank") == 1).limit(3).collect())
    closed = [r.asDict() for r in latest if r["event_type"] == "CLOSED"]
    if (len(latest) != 2 or len({r["gold_run_id"] for r in latest}) != 1 or len(closed) != 1
            or {r["event_type"] for r in latest} != {"STARTED", "CLOSED"}):
        raise ValueError("La última ejecución de cobertura Gold no tiene un cierre único; revisa su auditoría.")
    closure = closed[0]
    if (closure["status"] != "SUCCEEDED" or closure["gold_committed"] is not True
            or closure["gold_rule_version"] != "trip_coverage_v1" or not closure["candidate_rows"]):
        raise ValueError("La última publicación de cobertura Gold no está disponible.")
    try:
        upstream_runs = json.loads(closure["source_runs_json"])
    except (TypeError, ValueError) as error:
        raise ValueError("La auditoría de cobertura no conserva sus ejecuciones Silver.") from error
    for entity, rule in SOURCE_RULES.items():
        if not isinstance(upstream_runs, dict) or not upstream_runs.get(entity):
            raise ValueError("El linaje de cobertura está incompleto.")
        _latest_silver(frames["silver_audit"], entity, f"{prefix}.silver_gtfs_{entity}", rule, upstream_runs[entity])
    dates_audit = _latest_silver(frames["silver_audit"], "service_dates", names["service_dates"], "service_dates_v1")
    for name, run, rule, count, run_column, rule_column in [
        ("trip_coverage", closure["gold_run_id"], "trip_coverage_v1", closure["candidate_rows"], "gold_run_id", "gold_rule_version"),
        ("service_dates", dates_audit["silver_run_id"], "service_dates_v1", dates_audit["candidate_rows"], "silver_run_id", "silver_rule_version")]:
        bad = F.coalesce((F.col(run_column) != run) | (F.col(rule_column) != rule), F.lit(True))
        stats = frames[name].agg(F.count("*").alias("rows"), F.max(bad.cast("int")).alias("bad")).first()
        if stats["rows"] != count or stats["bad"] != 0:
            raise ValueError(f"{name} no coincide con su publicación auditada.")
    return frames["trip_coverage"], frames["service_dates"], {
        "versions": versions, "runs": {"trip_coverage": closure["gold_run_id"], "service_dates": dates_audit["silver_run_id"]}}


def prepare_route_service_day(spark: Any, *, catalog: str, schema: str, feed_version: str,
                              sha256: str, window_start: str, window_end: str) -> tuple[Any, dict, dict]:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    first, last = analysis_window(window_start, window_end)
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    coverage, dates, references = _load_sources(spark, catalog, schema, feed_version, sha256)
    # Validación de claves y horizonte antes de cualquier join que pueda multiplicar filas.
    invalid_coverage = (F.col("trip_id").isNull() | (F.trim("trip_id") == "") | F.col("route_id").isNull()
                        | (F.trim("route_id") == "") | F.col("service_id").isNull() | (F.trim("service_id") == "")
                        | F.col("frequency_window_count").isNull() | (F.col("frequency_window_count") < 0)
                        | F.col("coverage_status").isNull() | ~F.col("coverage_status").isin("sin_visitas", "una_visita", "varias_visitas"))
    stats = coverage.agg(F.count("*").alias("rows"), F.countDistinct("trip_id").alias("ids"),
                         F.max(invalid_coverage.cast("int")).alias("bad")).first()
    if stats["rows"] != stats["ids"] or stats["bad"] != 0:
        raise ValueError("Cobertura Gold contiene claves o categorías inválidas.")
    invalid_dates = (F.col("service_id").isNull() | (F.trim("service_id") == "") | F.col("service_date").isNull()
                     | ~F.col("service_date").between(first, last)
                     | ~F.col("analysis_window_start").eqNullSafe(F.lit(first))
                     | ~F.col("analysis_window_end").eqNullSafe(F.lit(last))
                     | F.col("source_temporal_warning").isNull())
    calendar = dates.agg(F.count("*").alias("rows"), F.countDistinct("service_id", "service_date").alias("ids"),
                         F.max(invalid_dates.cast("int")).alias("bad")).first()
    if calendar["rows"] != calendar["ids"] or calendar["bad"] != 0:
        raise ValueError("Fechas activas duplicadas, inválidas o de otro horizonte; no recorto la fuente.")
    output = (aggregate_days(coverage, dates)
              .withColumn("analysis_window_start", F.lit(first)).withColumn("analysis_window_end", F.lit(last)))
    # Reconciliación independiente por servicio: viajes × número de días activos, sin expandir visitas.
    service_totals = coverage.groupBy(*KEYS, "service_id").agg(F.count("*").alias("trips"))
    day_totals = dates.groupBy(*KEYS, "service_id").agg(F.count("*").alias("days"))
    expected = service_totals.join(day_totals, [*KEYS, "service_id"], "left").agg(
        F.sum(F.col("trips") * F.coalesce("days", F.lit(0))).alias("trip_days"),
        F.sum(F.when(F.col("days").isNull(), F.col("trips")).otherwise(0)).alias("inactive_trips")).first()
    bad = ((F.col("declared_trip_count") != F.col("trips_without_frequency_count") + F.col("frequency_template_count"))
           | (F.col("declared_trip_count") != F.col("trips_without_visits_count") + F.col("trips_with_one_visit_count") + F.col("trips_with_multiple_visits_count")))
    totals = output.agg(F.count("*").alias("candidate_rows"), F.countDistinct("route_id", "service_date").alias("distinct_keys"),
                        F.countDistinct("route_id").alias("routes_with_programming"),
                        F.sum("declared_trip_count").alias("trip_service_days"),
                        F.max(bad.cast("int")).alias("invalid_rows")).first().asDict()
    if (not totals["candidate_rows"] or totals["candidate_rows"] != totals["distinct_keys"]
            or totals["trip_service_days"] != expected["trip_days"] or totals["invalid_rows"] != 0):
        raise ValueError("La oferta diaria no reconcilia o está vacía; no publico Gold.")
    return output, {**totals, "inactive_trip_count": expected["inactive_trips"], "reconciled": True,
                    "window_start": window_start, "window_end": window_end, "rule_version": RULE_VERSION}, references


def run_route_service_day(spark: Any, *, catalog: str, schema: str, feed_version: str, sha256: str,
                          window_start: str, window_end: str, mode: str = "validate") -> dict:
    from pyspark.sql import functions as F
    _identity(catalog, schema, feed_version, sha256)
    analysis_window(window_start, window_end)
    if mode not in {"validate", "publish"}:
        raise ValueError("mode debe ser validate o publish.")
    target, audit = f"{catalog}.{schema}.gold_gtfs_route_service_day", f"{catalog}.{schema}.audit_gtfs_gold_runs"
    run_id, started, committed = str(uuid4()), datetime.now(timezone.utc), False
    result, refs = {}, {"versions": {}, "runs": {}}
    predicate = f"source_feed_version = '{feed_version}' and source_sha256 = '{sha256}'"

    def record(event: str, status: str, error: str | None = None) -> None:
        row = {"gold_run_id": run_id, "event_type": event, "entity": "route_service_day", "source_feed_version": feed_version,
               "source_sha256": sha256, "gold_rule_version": RULE_VERSION, "status": status, "gold_committed": committed,
               "started_at_utc": started, "finished_at_utc": None if event == "STARTED" else datetime.now(timezone.utc),
               "candidate_rows": result.get("candidate_rows"), "source_versions_json": json.dumps(refs["versions"], sort_keys=True),
               "source_runs_json": json.dumps(refs["runs"], sort_keys=True), "error_message": error}
        immutable_insert(spark, spark.createDataFrame([row], AUDIT_DDL), audit, ["gold_run_id", "event_type"])

    if mode == "publish":
        record("STARTED", "RUNNING")
    try:
        frame, result, refs = prepare_route_service_day(spark, catalog=catalog, schema=schema, feed_version=feed_version,
                                                      sha256=sha256, window_start=window_start, window_end=window_end)
        if mode == "publish":
            if spark.catalog.tableExists(quoted_table(target)):
                old = spark.table(quoted_table(target)).where(predicate)
                mismatch = (~F.col("analysis_window_start").eqNullSafe(F.to_date(F.lit(window_start)))
                            | ~F.col("analysis_window_end").eqNullSafe(F.to_date(F.lit(window_end))))
                if old.filter(mismatch).limit(1).count():
                    raise ValueError("El destino tiene otro horizonte; requiere migración explícita.")
            output = (frame.withColumn("gold_run_id", F.lit(run_id)).withColumn("gold_rule_version", F.lit(RULE_VERSION))
                      .withColumn("gold_loaded_at_utc", F.lit(started).cast("timestamp")))
            _overwrite_scope(output, target, predicate)
            committed = True
            checked = spark.table(quoted_table(target)).where(predicate).agg(
                F.count("*").alias("rows"), F.countDistinct("route_id", "service_date").alias("ids"),
                F.countDistinct("gold_run_id").alias("runs"), F.min("gold_run_id").alias("run_id")).first()
            if checked["rows"] != result["candidate_rows"] or checked["ids"] != checked["rows"] or checked["runs"] != 1 or checked["run_id"] != run_id:
                raise RuntimeError("No confirmé la publicación diaria; revisa la auditoría Gold.")
            record("CLOSED", "SUCCEEDED")
        return {"status": "SUCCEEDED" if committed else "VALIDATED", "persisted": committed,
                "gold_run_id": run_id, "table": target, **result, "source_references": refs}
    except Exception as error:
        if mode == "publish":
            record("CLOSED", "FAILED", str(error)[:2000])
        raise
