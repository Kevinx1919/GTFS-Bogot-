"""Stop_times_v1: visitas planificadas, horas de servicio y relaciones por snapshot."""
from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec
from .spark_validation import finish_validation, prepare_source, service_time_seconds

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

BUSINESS_TYPES = {
    "trip_id": "string", "arrival_time": "string", "departure_time": "string",
    "stop_id": "string", "stop_sequence": "int", "timepoint": "int",
    "stop_headsign": "string", "shape_dist_traveled": "double",
}
REQUIRED_FIELDS = frozenset({"trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"})
RULE_VERSION = "stop_times_v1"
KEYS = ("trip_id", "stop_sequence")


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    published = tuple(columns)
    if (not published or any(not isinstance(c, str) or not c.strip() for c in published)
            or len(published) != len(set(published))):
        raise ValueError("Encabezado vacío, inválido o repetido en stop_times.txt.")
    missing = REQUIRED_FIELDS - set(published)
    unknown = set(published) - set(BUSINESS_TYPES)
    if missing or unknown:
        raise ValueError(f"Revisar contrato stop_times: ausentes={sorted(missing)}; nuevas={sorted(unknown)}")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def _blank(field):
    from pyspark.sql import functions as F
    return F.col(field).isNull() | F.col(field).rlike(r"(?U)^\s*$")


def _dependency(frame: "DataFrame", spec: SnapshotSpec, entity: str, key: str) -> "DataFrame":
    """Verifico unicidad antes del join para impedir visitas multiplicadas."""
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType, IntegerType
    schema = {f.name: f.dataType for f in frame.schema.fields}
    names = (key, "source_feed_version", "source_sha256", "silver_rule_version")
    if any(name not in schema or not isinstance(schema[name], StringType) for name in names):
        raise ValueError(f"{entity} Silver requiere claves y procedencia string.")
    if entity == "stops" and not isinstance(schema.get("location_type"), IntegerType):
        raise ValueError("Stops Silver requiere location_type int nullable.")
    scoped = frame.filter((F.col("source_feed_version") == spec.feed_version)
                          & (F.col("source_sha256") == spec.sha256))
    invalid = (_blank(key) | F.col(key).rlike(r"(?U)^\s|\s$|[\p{Cc}\p{Cf}]")
               | ~F.col("silver_rule_version").eqNullSafe(F.lit(entity + "_v1")))
    if entity == "stops":
        invalid = invalid | (F.col("location_type").isNotNull() & ~F.col("location_type").isin(0, 1, 2, 3, 4))
    quality = scoped.agg(F.count("*").alias("rows"), F.countDistinct(key).alias("keys"),
                         F.max(F.when(invalid, 1).otherwise(0)).alias("invalid")).first()
    if not quality.rows or quality.rows != quality.keys or quality.invalid:
        raise ValueError(f"Publica primero {entity}_v1 del mismo snapshot con claves válidas y únicas.")
    return scoped.select(key, *(["location_type"] if entity == "stops" else []))


def _frequency_ids(frame: "DataFrame" | None, spec: SnapshotSpec, trips: "DataFrame") -> "DataFrame":
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType, LongType, IntegerType
    if frame is None:
        return trips.limit(0).select(F.col("trip_id").alias("_frequency_trip"))
    schema = {f.name: f.dataType for f in frame.schema.fields}
    required = {"trip_id": StringType, "source_feed_version": StringType, "source_sha256": StringType,
                "silver_rule_version": StringType, "start_time_seconds": LongType, "exact_times_effective": IntegerType}
    if any(not isinstance(schema.get(k), t) for k, t in required.items()):
        raise ValueError("Frequencies Silver requiere claves y contexto tipados antes de stop_times.")
    scoped = frame.filter((F.col("source_feed_version") == spec.feed_version)
                          & (F.col("source_sha256") == spec.sha256))
    invalid = (_blank("trip_id") | F.col("trip_id").rlike(r"(?U)^\s|\s$|[\p{Cc}\p{Cf}]")
               | ~F.col("silver_rule_version").eqNullSafe(F.lit("frequencies_v1"))
               | F.col("start_time_seconds").isNull() | (F.col("start_time_seconds") < 0)
               | F.col("exact_times_effective").isNull() | ~F.col("exact_times_effective").isin(0, 1))
    quality = scoped.agg(F.count("*").alias("rows"), F.countDistinct("trip_id", "start_time_seconds").alias("keys"),
                         F.max(F.when(invalid, 1).otherwise(0)).alias("invalid")).first()
    if not quality.rows or quality.rows != quality.keys or quality.invalid:
        raise ValueError("Publica primero frequencies_v1 del mismo snapshot con ventanas válidas y únicas.")
    grouped = scoped.groupBy("trip_id").agg(F.min("exact_times_effective").alias("_min_mode"),
                                             F.max("exact_times_effective").alias("_max_mode"))
    if grouped.filter(F.col("_min_mode") != F.col("_max_mode")).limit(1).count():
        raise ValueError("Frequencies Silver contiene modalidades incompatibles para un viaje.")
    if grouped.join(trips, "trip_id", "left_anti").limit(1).count():
        raise ValueError("Frequencies Silver contiene viajes ajenos a trips del mismo snapshot.")
    return grouped.select(F.col("trip_id").alias("_frequency_trip"))


def read_and_validate(
    bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec,
    trips_df: "DataFrame", stops_df: "DataFrame", frequencies_df: "DataFrame" | None = None,
    *, persist_result: bool = False,
) -> PreparedSnapshot:
    from pyspark.sql import functions as F, Window
    if spec.entity != "stop_times":
        raise ValueError("El contrato stop_times requiere un SnapshotSpec de stop_times.")
    columns = validate_header(published_columns)
    selected = prepare_source(bronze_df, columns, BUSINESS_TYPES, KEYS, spec, track_variants=False)
    trips = _dependency(trips_df, spec, "trips", "trip_id")
    stops = _dependency(stops_df, spec, "stops", "stop_id")
    frequencies = _frequency_ids(frequencies_df, spec, trips)
    # Recupero un escalar, no visitas. La ausencia total tiene una semántica GTFS distinta.
    has_timepoint = selected.agg(F.max(F.when(~_blank("timepoint"), 1).otherwise(0)).alias("present")).first().present
    missing_visits = trips.join(selected.select("trip_id").distinct(), "trip_id", "left_anti").count()
    selected = (selected.withColumn("_sequence", F.when(F.col("stop_sequence").rlike(r"^[0-9]+$"),
                                                       F.col("stop_sequence").try_cast("int")))
                .withColumn("arrival_time_seconds", service_time_seconds("arrival_time"))
                .withColumn("departure_time_seconds", service_time_seconds("departure_time"))
                .withColumn("_timepoint", F.when(F.col("timepoint").rlike(r"^[01]$"), F.col("timepoint").try_cast("int")))
                .withColumn("timepoint_effective", F.lit(1) if not has_timepoint else F.col("_timepoint"))
                .withColumn("_distance", F.when(~_blank("shape_dist_traveled"), F.col("shape_dist_traveled").try_cast("double"))))
    finite = F.col("_distance").isNotNull() & ~F.isnan("_distance") & (F.abs(F.col("_distance")) != F.lit(float("inf")))
    selected = selected.withColumn("_valid_distance", F.when(finite & (F.col("_distance") >= 0), F.col("_distance")))
    # Agrupo una vez por clave convertida: las copias no alteran orden ni cantidad de visitas.
    visits = selected.filter(F.col("_sequence").isNotNull()).groupBy("trip_id", "_sequence").agg(
        F.min("_business_json").alias("_canonical_min"), F.max("_business_json").alias("_canonical_max"),
        F.min(F.least("arrival_time_seconds", "departure_time_seconds")).alias("_time_min"),
        F.max(F.greatest("arrival_time_seconds", "departure_time_seconds")).alias("_time_max"),
        F.min("_valid_distance").alias("_distance_min"), F.max("_valid_distance").alias("_distance_max"))
    by_trip = Window.partitionBy("trip_id")
    ordered = by_trip.orderBy("_sequence")
    preceding = ordered.rowsBetween(Window.unboundedPreceding, -1)
    visits = (visits.withColumn("_first", F.min("_sequence").over(by_trip))
              .withColumn("_last", F.max("_sequence").over(by_trip))
              .withColumn("_visits", F.count("*").over(by_trip))
              .withColumn("_prior_time", F.max("_time_max").over(preceding))
              .withColumn("_prior_distance", F.max("_distance_max").over(preceding)))
    selected = (selected.join(visits, ["trip_id", "_sequence"], "left")
                .join(trips.select(F.col("trip_id").alias("_matched_trip")), F.col("trip_id") == F.col("_matched_trip"), "left")
                .join(stops.select(F.col("stop_id").alias("_matched_stop"), "location_type"), F.col("stop_id") == F.col("_matched_stop"), "left")
                .join(frequencies, F.col("trip_id") == F.col("_frequency_trip"), "left")
                .withColumn("is_frequency_template", F.col("_frequency_trip").isNotNull()))
    errors, warnings = [], []

    def issue(condition, code, *, warning=False):
        (warnings if warning else errors).append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        issue(F.col(field).rlike(r"[\p{Cc}\p{Cf}]"), f"{field.upper()}_CONTROL_CHARACTER")
        issue(~_blank(field) & F.col(field).rlike(r"(?U)^\s|\s$"), f"{field.upper()}_EDGE_WHITESPACE")
    for field in ("trip_id", "stop_id", "stop_sequence"):
        issue(_blank(field), f"{field.upper()}_MISSING")
    issue(F.col("_sequence").isNull(), "STOP_SEQUENCE_INVALID")
    issue(F.col("_canonical_min") != F.col("_canonical_max"), "VISIT_KEY_CONFLICT")
    issue(~_blank("timepoint") & F.col("_timepoint").isNull(), "TIMEPOINT_INVALID")
    issue(F.col("_matched_trip").isNull(), "TRIP_ID_NOT_FOUND")
    issue(F.col("_matched_stop").isNull(), "STOP_ID_NOT_FOUND")
    issue(F.col("location_type").isNotNull() & (F.col("location_type") != 0), "STOP_LOCATION_TYPE_INVALID")
    endpoint = (F.col("_sequence") == F.col("_first")) | (F.col("_sequence") == F.col("_last"))
    for field in ("arrival_time", "departure_time"):
        issue(~_blank(field) & F.col(field + "_seconds").isNull(), field.upper() + "_INVALID")
        required = (F.col("timepoint_effective") == 1)
        if field == "arrival_time":
            required = required | endpoint
        issue(required & _blank(field), field.upper() + "_REQUIRED")
    issue(F.col("is_frequency_template") & (F.col("_sequence") == F.col("_first"))
          & F.col("departure_time_seconds").isNull(), "FREQUENCY_BASE_DEPARTURE_MISSING")
    issue(F.lit(bool(has_timepoint)) & _blank("timepoint")
          & (_blank("arrival_time") | _blank("departure_time")), "TIMEPOINT_AMBIGUOUS_MISSING_TIMES")
    issue(F.lit(bool(has_timepoint)) & _blank("timepoint"), "TIMEPOINT_UNSPECIFIED", warning=True)
    issue(_blank("arrival_time") != _blank("departure_time"), "PARTIAL_TIME_PAIR", warning=True)
    issue(F.col("arrival_time_seconds") > F.col("departure_time_seconds"), "ARRIVAL_AFTER_DEPARTURE")
    issue(F.col("_time_min") < F.col("_prior_time"), "VISIT_TIME_BACKWARDS")
    issue(~_blank("shape_dist_traveled") & (~finite | (F.col("_distance") < 0)), "SHAPE_DIST_TRAVELED_INVALID")
    issue(F.col("_distance_min") < F.col("_prior_distance"), "SHAPE_DISTANCE_BACKWARDS")
    issue(F.col("_distance_min") == F.col("_prior_distance"), "SHAPE_DISTANCE_REPEATED", warning=True)
    issue(F.col("_visits") < 2, "TRIP_TOO_FEW_VISITS", warning=True)
    expressions = [F.col("trip_id"),
                   *[F.when(~_blank(n), F.col(n)).alias(n) for n in ("arrival_time", "departure_time")],
                   F.col("stop_id"), F.col("_sequence").alias("stop_sequence"), F.col("_timepoint").alias("timepoint"),
                   F.when(~_blank("stop_headsign"), F.col("stop_headsign")).alias("stop_headsign"),
                   F.col("_distance").alias("shape_dist_traveled"), F.col("arrival_time_seconds"),
                   F.col("departure_time_seconds"), F.col("timepoint_effective"), F.col("is_frequency_template")]
    result = finish_validation(selected, columns, spec, KEYS, RULE_VERSION, errors, warnings, expressions,
                               persist_result=persist_result)
    # El resumen ya probó que no hay rechazos; evito reevaluar millones de filas para una cuarentena vacía.
    if result.summary["rejected_rows"] == 0:
        result.frames["rejected"] = result.frames["rejected"].limit(0)
    result.summary["trips_without_visits"] = missing_visits
    result.reference_versions["diagnostic_trips_without_visits"] = str(missing_visits)
    return result
