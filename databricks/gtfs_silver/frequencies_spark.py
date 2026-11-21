"""Frequencies_v1: ventanas de servicio sin expandir salidas ni cambiar unidades."""
from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec
from .spark_validation import finish_validation, prepare_source, service_time_seconds as _service_seconds

if TYPE_CHECKING:
    from pyspark.sql import Column, DataFrame

BUSINESS_TYPES = {"trip_id": "string", "start_time": "string", "end_time": "string",
                  "headway_secs": "int", "exact_times": "int"}
REQUIRED_FIELDS = frozenset({"trip_id", "start_time", "end_time", "headway_secs"})
RULE_VERSION = "frequencies_v1"
KEYS = ("trip_id", "start_time_seconds")


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    published = tuple(columns)
    if (not published or any(not isinstance(c, str) or not c.strip() for c in published)
            or len(published) != len(set(published))):
        raise ValueError("Encabezado vacío, inválido o repetido en frequencies.txt.")
    missing = REQUIRED_FIELDS - set(published)
    unknown = set(published) - set(BUSINESS_TYPES)
    if missing or unknown:
        raise ValueError(f"Revisar contrato frequencies: ausentes={sorted(missing)}; nuevas={sorted(unknown)}")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def _trip_ids(frame: "DataFrame", spec: SnapshotSpec) -> "DataFrame":
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType

    required = ("trip_id", "source_feed_version", "source_sha256", "silver_rule_version")
    schema = {f.name: f.dataType for f in frame.schema.fields}
    if any(name not in schema or not isinstance(schema[name], StringType) for name in required):
        raise ValueError("Trips Silver requiere claves y procedencia string antes de frequencies.")
    scoped = frame.filter((F.col("source_feed_version") == spec.feed_version)
                          & (F.col("source_sha256") == spec.sha256))
    invalid = (F.col("trip_id").isNull() | F.col("trip_id").rlike(r"(?U)^\s*$|^\s|\s$|[\p{Cc}\p{Cf}]")
               | ~F.col("silver_rule_version").eqNullSafe(F.lit("trips_v1")))
    # Solo recupero un resumen de la dependencia; no traigo viajes al driver.
    quality = scoped.agg(F.count("*").alias("rows"), F.countDistinct("trip_id").alias("keys"),
                         F.max(F.when(invalid, 1).otherwise(0)).alias("invalid")).first()
    if not quality.rows or quality.rows != quality.keys or quality.invalid:
        raise ValueError("Publica primero trips_v1 del mismo snapshot con claves válidas y únicas.")
    return scoped.select(F.col("trip_id").alias("_matched_trip"))


def read_and_validate(
    bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec, trips_df: "DataFrame",
) -> PreparedSnapshot:
    from pyspark.sql import functions as F, Window

    if spec.entity != "frequencies":
        raise ValueError("El contrato frequencies requiere un SnapshotSpec de frequencies.")
    columns = validate_header(published_columns)
    selected = prepare_source(bronze_df, columns, BUSINESS_TYPES, ("trip_id", "start_time"), spec)
    selected = (selected.withColumn("start_time_seconds", _service_seconds("start_time"))
                .withColumn("end_time_seconds", _service_seconds("end_time"))
                .withColumn("_headway", F.when(F.col("headway_secs").rlike(r"^[0-9]+$"),
                                               F.col("headway_secs").try_cast("int"))))
    blank_exact = F.col("exact_times").isNull() | F.col("exact_times").rlike(r"(?U)^\s*$")
    selected = selected.withColumn("_exact", F.when(~blank_exact & F.col("exact_times").rlike(r"^[01]$"),
                                                   F.col("exact_times").try_cast("int")))
    selected = selected.withColumn("_effective", F.when(blank_exact, F.lit(0)).otherwise(F.col("_exact")))
    canonical = Window.partitionBy(*KEYS)
    by_trip = Window.partitionBy("trip_id")
    selected = (selected.withColumn("_canonical_min", F.min("_business_json").over(canonical))
                .withColumn("_canonical_max", F.max("_business_json").over(canonical))
                .withColumn("_mode_min", F.min("_effective").over(by_trip))
                .withColumn("_mode_max", F.max("_effective").over(by_trip)))

    # Una clave por inicio evita falsas superposiciones causadas por copias idénticas.
    # Los conflictos de atributos se rechazan aparte; no elijo una variante para publicar.
    windows = (selected.filter(F.col("start_time_seconds").isNotNull()
                               & (F.col("end_time_seconds") > F.col("start_time_seconds")))
               .groupBy(*KEYS).agg(F.max("end_time_seconds").alias("_window_end")))
    ordered = Window.partitionBy("trip_id").orderBy("start_time_seconds")
    windows = (windows.withColumn("_prior_end", F.max("_window_end").over(
                   ordered.rowsBetween(Window.unboundedPreceding, -1)))
               .withColumn("_next_start", F.lead("start_time_seconds").over(ordered))
               .withColumn("_overlap", (F.col("start_time_seconds") < F.col("_prior_end"))
                           | (F.col("_window_end") > F.col("_next_start")))
               .select(*KEYS, "_overlap"))
    selected = selected.join(windows, list(KEYS), "left")
    trips = _trip_ids(trips_df, spec)
    selected = selected.join(trips, selected.trip_id == trips._matched_trip, "left")
    errors, warnings = [], []

    def issue(condition, code, *, warning=False):
        (warnings if warning else errors).append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        blank = F.col(field).isNull() | F.col(field).rlike(r"(?U)^\s*$")
        issue(F.col(field).rlike(r"[\p{Cc}\p{Cf}]"), f"{field.upper()}_CONTROL_CHARACTER")
        if field in REQUIRED_FIELDS:
            issue(blank, f"{field.upper()}_MISSING")
        issue(~blank & F.col(field).rlike(r"(?U)^\s|\s$"), f"{field.upper()}_EDGE_WHITESPACE")
    issue(F.col("start_time_seconds").isNull(), "START_TIME_INVALID")
    issue(F.col("end_time_seconds").isNull(), "END_TIME_INVALID")
    issue(F.col("_headway").isNull() | (F.col("_headway") <= 0), "HEADWAY_SECS_INVALID")
    issue(~blank_exact & F.col("_exact").isNull(), "EXACT_TIMES_INVALID")
    issue(F.col("_mode_min") != F.col("_mode_max"), "EXACT_TIMES_INCONSISTENT")
    duration = F.col("end_time_seconds") - F.col("start_time_seconds")
    issue(duration <= 0, "WINDOW_NOT_INCREASING")
    issue(F.col("_variant_min") != F.col("_variant_max"), "FREQUENCY_KEY_CONFLICT")
    issue(F.col("start_time_seconds").isNotNull()
          & (F.col("_canonical_min") != F.col("_canonical_max")), "FREQUENCY_CANONICAL_KEY_CONFLICT")
    issue(F.col("_overlap"), "FREQUENCY_WINDOWS_OVERLAP")
    issue(F.col("_matched_trip").isNull(), "TRIP_ID_NOT_FOUND")
    # exact_times=1 exige un fin posterior a la última salida y anterior al siguiente intervalo.
    # Evito módulo por cero incluso cuando un intervalo ya tenga otro motivo de rechazo.
    divisor = F.when(F.col("_headway") > 0, F.col("_headway"))
    issue((F.col("_effective") == 1) & (duration > 0)
          & (F.pmod(duration, divisor) == 0), "EXACT_TIMES_END_BOUNDARY_INVALID")
    issue((duration > 0) & (F.col("_headway") > duration), "HEADWAY_LONGER_THAN_WINDOW", warning=True)
    expressions = [F.col("trip_id"), F.col("start_time"), F.col("end_time"),
                   F.col("_headway").alias("headway_secs"), F.col("_exact").alias("exact_times"),
                   F.col("start_time_seconds"), F.col("end_time_seconds"),
                   F.col("_effective").alias("exact_times_effective")]
    return finish_validation(selected, columns, spec, KEYS, RULE_VERSION, errors, warnings, expressions)
