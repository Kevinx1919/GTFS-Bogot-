"""Días activos derivados de Silver dentro de un horizonte explícito y acotado."""
from __future__ import annotations

from datetime import date
import json
from typing import TYPE_CHECKING, Mapping

from .calendars_spark import WEEKDAYS
from .models import DerivedSnapshotSpec, PreparedSnapshot

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

RULE_VERSION = "service_dates_v1"


def _validated_source(frame: "DataFrame", entity: str, spec: DerivedSnapshotSpec):
    from pyspark.sql import functions as F
    from pyspark.sql.types import DateType, IntegerType, StringType
    types = {"service_id": StringType, "source_feed_version": StringType,
             "source_sha256": StringType, "silver_rule_version": StringType}
    types.update({day: IntegerType for day in WEEKDAYS} if entity == "calendar" else {"exception_type": IntegerType})
    types.update({"start_date": DateType, "end_date": DateType} if entity == "calendar" else {"date": DateType})
    schema = {f.name: f.dataType for f in frame.schema.fields}
    if any(name not in schema or not isinstance(schema[name], target) for name, target in types.items()):
        raise ValueError(f"La fuente {entity} no tiene el esquema Silver requerido.")
    scoped = frame.filter((F.col("source_feed_version") == spec.feed_version) & (F.col("source_sha256") == spec.sha256))
    invalid = (F.col("service_id").isNull() | F.col("service_id").rlike(r"(?U)^\s*$|^\s|\s$|[\p{Cc}]")
               | ~F.col("silver_rule_version").eqNullSafe(F.lit(entity + "_v1")))
    if entity == "calendar":
        for day in WEEKDAYS:
            invalid = invalid | F.col(day).isNull() | ~F.col(day).isin(0, 1)
        invalid = invalid | F.col("start_date").isNull() | F.col("end_date").isNull() | (F.col("start_date") > F.col("end_date")) | (F.year("start_date") < 1) | (F.year("end_date") < 1)
        keys = ("service_id",)
        temporal = F.col("end_date") > F.add_months(F.col("start_date"), 120)
    else:
        invalid = invalid | F.col("date").isNull() | F.col("exception_type").isNull() | ~F.col("exception_type").isin(1, 2) | (F.year("date") < 1)
        keys = ("service_id", "date")
        temporal = F.year("date") != int(spec.feed_version[:4])
    metrics = scoped.agg(F.count("*").alias("rows"), F.countDistinct(*keys).alias("keys"),
                         F.sum(F.when(invalid, 1).otherwise(0)).alias("invalid"),
                         F.max(F.when(temporal, 1).otherwise(0)).alias("temporal_warning")).first()
    if not metrics["rows"] or metrics["rows"] != metrics["keys"] or metrics["invalid"]:
        raise ValueError(f"Publica primero {entity}_v1 del mismo snapshot, con filas válidas y claves únicas.")
    return scoped, int(metrics["rows"]), bool(metrics["temporal_warning"])


def derive_service_dates(
    spark, spec: DerivedSnapshotSpec, calendar_df: "DataFrame | None",
    exceptions_df: "DataFrame | None", reference_versions: Mapping[str, str],
) -> PreparedSnapshot:
    """Aplica patrón union adiciones menos retiradas sin expandir horarios."""
    from pyspark.sql import functions as F
    if spark.conf.get("spark.sql.session.timeZone") != "UTC":
        raise ValueError("Configura spark.sql.session.timeZone=UTC.")
    if calendar_df is None and exceptions_df is None:
        raise ValueError("service_dates requiere al menos una fuente Silver publicada.")
    for entity, frame in (("calendar", calendar_df), ("calendar_dates", exceptions_df)):
        if frame is not None and (not str(reference_versions.get(entity + "_delta_version", "")).isdigit()
                                  or not reference_versions.get(entity + "_table")):
            raise ValueError("Registra la tabla y versión Delta fijada de cada fuente de la derivación.")
    used_references = {key: reference_versions[key]
                       for entity, frame in (("calendar", calendar_df), ("calendar_dates", exceptions_df))
                       if frame is not None for key in (entity + "_table", entity + "_delta_version")}
    start, end = F.lit(spec.window_start).cast("date"), F.lit(spec.window_end).cast("date")
    empty = spark.createDataFrame([], "service_id string, service_date date")
    weekly = empty
    scoped_exceptions = spark.createDataFrame([], "service_id string, date date, exception_type int")
    calendar_rows = exception_rows = 0
    temporal_warning = False
    calendar = None
    if calendar_df is not None:
        calendar, calendar_rows, warning = _validated_source(calendar_df, "calendar", spec)
        temporal_warning |= warning
        first, last = F.greatest(F.col("start_date"), start), F.least(F.col("end_date"), end)
        days = F.when(first <= last, F.sequence(first, last)).otherwise(F.array().cast("array<date>"))
        expanded = calendar.select("service_id", *WEEKDAYS, F.explode(days).alias("service_date"))
        index = F.pmod(F.dayofweek("service_date") + F.lit(5), F.lit(7)) + F.lit(1)
        weekly = expanded.filter(F.element_at(F.array(*[F.col(d) for d in WEEKDAYS]), index) == 1).select("service_id", "service_date")
    if exceptions_df is not None:
        scoped_exceptions, exception_rows, warning = _validated_source(exceptions_df, "calendar_dates", spec)
        temporal_warning |= warning
        if calendar is not None:
            # Las claves semanales ya son únicas: el anti join no multiplica filas.
            if scoped_exceptions.select("service_id").distinct().join(calendar.select("service_id"), "service_id", "left_anti").limit(1).count():
                raise ValueError("Hay excepciones sin servicio en calendar del mismo snapshot.")
    exceptions = scoped_exceptions.filter(F.col("date").between(start, end)).select("service_id", F.col("date").alias("service_date"), "exception_type")
    additions = exceptions.filter(F.col("exception_type") == 1).select("service_id", "service_date")
    keys = ["service_id", "service_date"]
    universe = weekly.unionByName(additions).distinct()
    joined = (universe.join(weekly.withColumn("weekly_pattern_active", F.lit(True)), keys, "left")
              .join(exceptions, keys, "left")
              .withColumn("weekly_pattern_active", F.coalesce("weekly_pattern_active", F.lit(False))))
    active = F.col("exception_type").isNull() | (F.col("exception_type") != 2)
    metrics = (joined.agg(F.sum(F.when(active, 1).otherwise(0)).alias("active_days"),
                          F.sum(F.when((F.col("exception_type") == 1) & ~F.col("weekly_pattern_active"), 1).otherwise(0)).alias("added_new_days"),
                          F.sum(F.when(F.col("exception_type") == 2, 1).otherwise(0)).alias("removed_active_days"))
               .crossJoin(weekly.agg(F.count("*").alias("weekly_service_days")))
               .crossJoin(exceptions.agg(F.count("*").alias("exception_rules_in_window")))
               .first().asDict())
    metrics = {key: int(value or 0) for key, value in metrics.items()}
    count = metrics["active_days"]
    if not count:
        raise ValueError("La ventana no produce días activos. service_dates_v1 no reemplaza Silver con una salida vacía; revisa el alcance.")
    if count != metrics["weekly_service_days"] + metrics["added_new_days"] - metrics["removed_active_days"]:
        raise ValueError("No reconcilia la derivación de días activos.")
    candidates = joined.filter(active).select(
        *keys, F.when(F.col("exception_type") == 1, F.lit("calendar_date_addition")).otherwise(F.lit("weekly_pattern")).alias("activation_source"),
        "weekly_pattern_active", F.lit(spec.feed_version).alias("source_feed_version"), F.lit(spec.sha256).alias("source_sha256"),
        start.alias("analysis_window_start"), end.alias("analysis_window_end"),
        F.lit(temporal_warning).alias("source_temporal_warning"),
        F.lit(json.dumps(used_references, sort_keys=True)).alias("input_versions_json"),
        F.lit(RULE_VERSION).alias("silver_rule_version"))
    rejected = candidates.filter(F.lit(False)).select("service_id", F.col("service_date").cast("string").alias("service_date"),
        "source_feed_version", "source_sha256", F.to_json(F.struct(*candidates.columns)).alias("original_row_json"),
        F.array().cast("array<string>").alias("error_codes"), "silver_rule_version")
    warnings = candidates.filter("source_temporal_warning").select(*keys, F.array(F.lit("SOURCE_TEMPORAL_SCOPE_WARNING")).alias("warning_codes"))
    summary = dict(input_rows=count, candidate_rows=count, rejected_rows=0, identical_copies_consolidated=0,
                   warning_rows=count if temporal_warning else 0, reconciled=True, ready_for_publication=True,
                   rule_version=RULE_VERSION, source_calendar_rows=calendar_rows, source_calendar_dates_rows=exception_rows,
                   exception_rules_outside_window=exception_rows-metrics["exception_rules_in_window"], **metrics)
    return PreparedSnapshot({"candidates": candidates, "rejected": rejected, "warnings": warnings}, summary, used_references)


def check_existing_window(frame: "DataFrame", spec: DerivedSnapshotSpec) -> None:
    """Un snapshot mantiene un horizonte; cambiarlo requiere una migración explícita."""
    from pyspark.sql import functions as F
    if not {"analysis_window_start", "analysis_window_end"}.issubset(frame.columns):
        raise ValueError("El destino service_dates requiere migración de esquema.")
    scoped = frame.filter((F.col("source_feed_version") == spec.feed_version) & (F.col("source_sha256") == spec.sha256))
    mismatch = (~F.col("analysis_window_start").eqNullSafe(F.lit(spec.window_start).cast("date"))
                | ~F.col("analysis_window_end").eqNullSafe(F.lit(spec.window_end).cast("date")))
    if scoped.filter(mismatch).limit(1).count():
        raise ValueError("Este snapshot ya tiene otro horizonte publicado; requiere migración explícita, no un reemplazo silencioso.")
