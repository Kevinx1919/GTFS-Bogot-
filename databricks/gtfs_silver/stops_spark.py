"""Contrato stops_v1: ubicaciones y jerarquía del mismo snapshot, con Spark nativo."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec
from .spark_validation import prepare_source, finish_validation

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

BUSINESS_TYPES = {
    "stop_id": "string", "stop_code": "string", "stop_name": "string",
    "stop_lat": "double", "stop_lon": "double", "location_type": "int",
    "parent_station": "string", "zone_id": "string", "wheelchair_boarding": "int",
}
RULE_VERSION = "stops_v1"


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    published = tuple(columns)
    if not published or any(not isinstance(c, str) or not c.strip() for c in published):
        raise ValueError("Encabezado vacío o inválido en stops.txt.")
    if len(published) != len(set(published)):
        raise ValueError("El encabezado de stops tiene columnas duplicadas.")
    missing = {"stop_id"} - set(published)
    unknown = set(published) - set(BUSINESS_TYPES)
    if missing or unknown:
        raise ValueError(f"Revisar contrato stops: requeridas ausentes={sorted(missing)}; nuevas={sorted(unknown)}")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def read_and_validate(
    bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec,
) -> PreparedSnapshot:
    """Valida sin UDFs ni collect; la relación de padres nunca multiplica hijos."""
    from pyspark.sql import functions as F

    if spec.entity != "stops":
        raise ValueError("El contrato stops requiere un SnapshotSpec de stops.")
    columns = validate_header(published_columns)
    selected = prepare_source(bronze_df, columns, BUSINESS_TYPES, "stop_id", spec)

    def blank(name):
        return F.col(name).isNull() | F.col(name).rlike(r"(?U)^\s*$")

    def edge(name):
        return ~blank(name) & F.col(name).rlike(r"(?U)^\s|\s$")

    # El default GTFS solo sirve para validar; no rellena la columna publicada.
    selected = (selected.withColumn("_location_type_effective", F.when(blank("location_type"), F.lit(0))
                .otherwise(F.expr("try_cast(location_type as int)")))
                .withColumn("_latitude", F.expr("try_cast(stop_lat as double)"))
                .withColumn("_longitude", F.expr("try_cast(stop_lon as double)"))
                .withColumn("_normalized_name", F.regexp_replace("stop_name", r"(?U)^\s+|\s+$", "")))
    valid_origin = (F.col("source_feed_version").eqNullSafe(F.lit(spec.feed_version))
                    & F.col("source_file_path").eqNullSafe(F.lit(spec.source_path))
                    & F.col("bronze_loaded_at_utc").isNotNull())
    # Agrupar padres antes del join evita multiplicación por copias o IDs conflictivos.
    parents = (selected.filter(valid_origin & ~blank("stop_id") & ~edge("stop_id")
                               & ~F.col("stop_id").rlike(r"[\p{Cc}]"))
               .groupBy(F.col("stop_id").alias("_parent_id"))
               .agg(F.min("_location_type_effective").alias("_parent_type"),
                    F.min("_variant_min").alias("_parent_min"),
                    F.max("_variant_max").alias("_parent_max")))
    references = (selected.filter(valid_origin & ~blank("parent_station"))
                  .select(F.col("parent_station").alias("_referenced_id")).distinct())
    selected = (selected.join(parents, selected.parent_station == parents._parent_id, "left")
                .join(references, F.col("stop_id") == references._referenced_id, "left"))
    errors, warnings = [], []

    def issue(condition, code, *, warning=False):
        (warnings if warning else errors).append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        issue(F.col(field).rlike(r"[\p{Cc}]"), f"{field.upper()}_CONTROL_CHARACTER")
        issue(edge(field), f"{field.upper()}_EDGE_WHITESPACE",
              warning=field not in {"stop_id", "parent_station", "zone_id"})
    issue(blank("stop_id"), "STOP_ID_MISSING")
    issue(F.col("_variant_min") != F.col("_variant_max"), "STOP_ID_CONFLICT")

    for field, allowed in (("location_type", (0, 1, 2, 3, 4)), ("wheelchair_boarding", (0, 1, 2))):
        parsed = F.expr(f"try_cast(`{field}` as int)")
        invalid = ~F.col(field).rlike(r"^[0-9]+$") | parsed.isNull() | ~parsed.isin(*allowed)
        issue(~blank(field) & invalid, f"{field.upper()}_INVALID")
    needs_location = F.col("_location_type_effective").isin(0, 1, 2)
    issue(needs_location & blank("stop_name"), "STOP_NAME_MISSING")
    numeric = r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"
    for field, parsed_name, bound in (("stop_lat", "_latitude", 90), ("stop_lon", "_longitude", 180)):
        parsed = F.col(parsed_name)
        issue(needs_location & blank(field), f"{field.upper()}_MISSING")
        invalid = (~F.col(field).rlike(numeric) | parsed.isNull() | F.isnan(parsed)
                   | ~parsed.between(-bound, bound))
        issue(~blank(field) & invalid, f"{field.upper()}_INVALID")
    issue((F.col("_latitude") == 0) & (F.col("_longitude") == 0), "COORDINATES_ZERO_PAIR", warning=True)

    has_parent = ~blank("parent_station")
    issue(has_parent & (F.col("parent_station") == F.col("stop_id")), "PARENT_STATION_SELF_REFERENCE")
    issue(has_parent & F.col("_parent_id").isNull(), "PARENT_STATION_NOT_FOUND")
    issue(has_parent & (F.col("_parent_min") != F.col("_parent_max")), "PARENT_STATION_CONFLICT")
    issue((F.col("_location_type_effective") == 1) & has_parent, "PARENT_STATION_FORBIDDEN")
    issue(F.col("_location_type_effective").isin(2, 3, 4) & ~has_parent, "PARENT_STATION_MISSING")
    wrong_type = ((F.col("_location_type_effective").isin(0, 2, 3)
                   & ~F.col("_parent_type").eqNullSafe(F.lit(1)))
                  | ((F.col("_location_type_effective") == 4)
                     & ~F.col("_parent_type").eqNullSafe(F.lit(0))))
    issue(has_parent & F.col("_parent_id").isNotNull() & wrong_type, "PARENT_STATION_TYPE_INVALID")
    no_children = (F.col("_location_type_effective") == 1) & F.col("_referenced_id").isNull()
    issue(no_children, "STATION_WITHOUT_CHILDREN", warning=True)

    expressions = []
    for field, target_type in BUSINESS_TYPES.items():
        value = F.col("_normalized_name") if field == "stop_name" else (
            F.expr(f"try_cast(`{field}` as {target_type})") if target_type != "string" else F.col(field))
        expressions.append(F.when(blank(field), F.lit(None)).otherwise(value).cast(target_type).alias(field))
    return finish_validation(
        selected, columns, spec, "stop_id", RULE_VERSION, errors, warnings, expressions,
        extra_metrics={"name_trimmed_rows": edge("stop_name"), "stations_without_children": no_children},
    )
