"""Trips_v1: identidad y referencias del snapshot sin expandir fechas ni puntos."""
from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec
from .spark_validation import finish_validation, prepare_source

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

BUSINESS_TYPES = {name: "string" for name in ("trip_id", "route_id", "service_id", "shape_id", "trip_headsign")}
REQUIRED_FIELDS = frozenset({"trip_id", "route_id", "service_id"})
RULE_VERSION = "trips_v1"
SCOPE_FILES = frozenset({"routes.txt", "stop_times.txt", "calendar.txt", "calendar_dates.txt", "shapes.txt"})


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    published = tuple(columns)
    if (not published or any(not isinstance(c, str) or not c.strip() for c in published)
            or len(published) != len(set(published))):
        raise ValueError("Encabezado vacío, inválido o repetido en trips.txt.")
    missing = REQUIRED_FIELDS - set(published)
    unknown = set(published) - set(BUSINESS_TYPES)
    if missing or unknown:
        raise ValueError(f"Revisar contrato trips: ausentes={sorted(missing)}; nuevas={sorted(unknown)}")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def validate_scope_headers(observations: Sequence[tuple[str, str]]) -> set[str]:
    """Comprueba metadata pequeña antes de aceptar shape_id opcional."""
    files = set()
    for filename, encoded in observations:
        if filename not in SCOPE_FILES or filename in files:
            raise ValueError("La auditoría de encabezados está incompleta o es ambigua; revisa Bronze 07.")
        try:
            columns = json.loads(encoded)
        except (TypeError, ValueError) as error:
            raise ValueError("La auditoría requiere encabezados JSON válidos; revisa Bronze 07.") from error
        if (not isinstance(columns, list) or not columns
                or any(not isinstance(c, str) or not c.strip() for c in columns)
                or len(columns) != len(set(columns))):
            raise ValueError("La auditoría contiene un encabezado inválido; revisa Bronze 07.")
        if filename in {"routes.txt", "stop_times.txt"} and {"continuous_pickup", "continuous_drop_off"} & set(columns):
            raise ValueError("Trips_v1 requiere revisar el contrato ante columnas de servicio continuo.")
        files.add(filename)
    if not {"routes.txt", "stop_times.txt"} <= files or not {"calendar.txt", "calendar_dates.txt"} & files:
        raise ValueError("Faltan encabezados de rutas, horarios o calendarios en auditoría; revisa Bronze 07.")
    return files


def _reference(frame: "DataFrame", key: str, rule: str, spec: SnapshotSpec, *, secondary: str | None = None):
    from pyspark.sql import functions as F
    from pyspark.sql.types import DateType, IntegerType, StringType

    required = {key, "source_feed_version", "source_sha256", "silver_rule_version"}
    if secondary:
        required.add(secondary)
    schema = {f.name: f.dataType for f in frame.schema.fields}
    if not required <= set(schema) or any(not isinstance(schema[name], StringType) for name in required - {secondary}):
        raise ValueError(f"La dependencia {rule} requiere claves y procedencia string.")
    if secondary and not isinstance(schema[secondary], DateType if secondary == "date" else IntegerType):
        raise ValueError(f"La dependencia {rule} tiene un tipo de clave incorrecto.")
    scoped = frame.filter((F.col("source_feed_version") == spec.feed_version) & (F.col("source_sha256") == spec.sha256))
    invalid = (F.col(key).isNull() | F.col(key).rlike(r"(?U)^\s*$|^\s|\s$|[\p{Cc}]")
               | ~F.col("silver_rule_version").eqNullSafe(F.lit(rule)))
    keys = [key]
    if secondary:
        keys.append(secondary)
        invalid = invalid | F.col(secondary).isNull()
        invalid = invalid | ((F.year(secondary) < 1) if secondary == "date" else (F.col(secondary) < 0))
    checks = scoped.agg(F.count("*").alias("rows"), F.countDistinct(*keys).alias("keys"),
                        F.max(F.when(invalid, 1).otherwise(0)).alias("invalid")).withColumn("dependency", F.lit(rule))
    return scoped.select(key).distinct(), checks


def read_and_validate(
    bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec, routes_df: "DataFrame",
    *, calendar_df: "DataFrame | None" = None, calendar_dates_df: "DataFrame | None" = None,
    shape_points_df: "DataFrame | None" = None,
) -> PreparedSnapshot:
    """Comprueba catálogos únicos; las ausencias opcionales no inventan contenido."""
    from pyspark.sql import functions as F

    if spec.entity != "trips":
        raise ValueError("El contrato trips requiere un SnapshotSpec de trips.")
    columns = validate_header(published_columns)
    selected = prepare_source(bronze_df, columns, BUSINESS_TYPES, "trip_id", spec)
    if calendar_df is None and calendar_dates_df is None:
        raise ValueError("Publica al menos un calendario Silver del mismo snapshot antes de trips.")

    # Una sola acción recupera como máximo cuatro resúmenes de dependencias.
    route_ids, checks = _reference(routes_df, "route_id", "routes_v1", spec)
    calendars = []
    for frame, rule, secondary in ((calendar_df, "calendar_v1", None), (calendar_dates_df, "calendar_dates_v1", "date")):
        if frame is not None:
            ids, quality = _reference(frame, "service_id", rule, spec, secondary=secondary)
            calendars.append(ids)
            checks = checks.unionByName(quality)
    shape_ids = bronze_df.sparkSession.createDataFrame([], "shape_id string")
    if shape_points_df is not None:
        shape_ids, quality = _reference(shape_points_df, "shape_id", "shape_points_v1", spec, secondary="shape_pt_sequence")
        checks = checks.unionByName(quality)
    for item in checks.collect():
        if not item.rows or item.rows != item.keys or item.invalid:
            raise ValueError(f"Publica primero {item.dependency} del mismo snapshot, con claves válidas y únicas.")
    service_ids = calendars[0]
    if len(calendars) == 2:
        service_ids = service_ids.unionByName(calendars[1]).distinct()
    selected = (selected.join(route_ids.withColumnRenamed("route_id", "_matched_route"),
                              selected.route_id == F.col("_matched_route"), "left")
                .join(service_ids.withColumnRenamed("service_id", "_matched_service"),
                      F.col("service_id") == F.col("_matched_service"), "left")
                .join(shape_ids.withColumnRenamed("shape_id", "_matched_shape"),
                      F.col("shape_id") == F.col("_matched_shape"), "left"))

    def blank(field):
        return F.col(field).isNull() | F.col(field).rlike(r"(?U)^\s*$")

    errors = []

    def issue(condition, code):
        errors.append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        issue(F.col(field).rlike(r"[\p{Cc}]"), f"{field.upper()}_CONTROL_CHARACTER")
        if field in REQUIRED_FIELDS:
            issue(blank(field), f"{field.upper()}_MISSING")
        if field != "trip_headsign":
            issue(~blank(field) & F.col(field).rlike(r"(?U)^\s|\s$"), f"{field.upper()}_EDGE_WHITESPACE")
    issue(F.col("_variant_min") != F.col("_variant_max"), "TRIP_ID_CONFLICT")
    for field, matched in (("route_id", "_matched_route"), ("service_id", "_matched_service"), ("shape_id", "_matched_shape")):
        issue(~blank(field) & F.col(matched).isNull(), f"{field.upper()}_NOT_FOUND")
    expressions = [F.when(blank(field), F.lit(None)).otherwise(F.col(field)).cast("string").alias(field) for field in BUSINESS_TYPES]
    return finish_validation(selected, columns, spec, "trip_id", RULE_VERSION, errors, [], expressions)
