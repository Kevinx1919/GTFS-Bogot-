"""Shape_points_v1: puntos tipados y advertencias geométricas con Spark nativo."""
from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Sequence

from .models import PreparedSnapshot, SnapshotSpec
from .spark_validation import finish_validation, prepare_source

if TYPE_CHECKING:
    from pyspark.sql import DataFrame

BUSINESS_TYPES = {
    "shape_id": "string", "shape_pt_sequence": "int",
    "shape_pt_lat": "double", "shape_pt_lon": "double", "shape_dist_traveled": "double",
}
KEYS = ("shape_id", "shape_pt_sequence")
RULE_VERSION = "shape_points_v1"
NUMERIC = r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"


def validate_header(columns: Sequence[str]) -> tuple[str, ...]:
    published = tuple(columns)
    if (not published or any(not isinstance(c, str) or not c.strip() for c in published)
            or len(published) != len(set(published))):
        raise ValueError("Encabezado vacío, inválido o repetido en shapes.txt.")
    missing = set(KEYS + ("shape_pt_lat", "shape_pt_lon")) - set(published)
    unknown = set(published) - set(BUSINESS_TYPES)
    if missing or unknown:
        raise ValueError(f"Revisar contrato shapes: ausentes={sorted(missing)}; nuevas={sorted(unknown)}")
    return published


def read_source_header(path: str) -> tuple[str, ...]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return validate_header(next(csv.reader(handle), ()))


def read_and_validate(
    bronze_df: "DataFrame", published_columns: Sequence[str], spec: SnapshotSpec,
) -> PreparedSnapshot:
    """Conserva puntos y contexto; nunca usa coordenadas como clave de deduplicación."""
    from pyspark.sql import functions as F, Window

    if spec.entity != "shape_points":
        raise ValueError("El contrato requiere shape_points con archivo fuente shapes.txt.")
    columns = validate_header(published_columns)
    selected = prepare_source(bronze_df, columns, BUSINESS_TYPES, KEYS, spec)
    for name, target in BUSINESS_TYPES.items():
        if target != "string":
            selected = selected.withColumn("_" + name, F.expr(f"try_cast(`{name}` as {target})"))

    def blank(name):
        return F.col(name).isNull() | F.col(name).rlike(r"(?U)^\s*$")

    errors, warnings = [], []

    def issue(condition, code, *, warning=False):
        (warnings if warning else errors).append(F.when(F.coalesce(condition, F.lit(False)), F.lit(code)))

    # Compruebo procedencia antes de usar una fila en las ventanas geométricas.
    for field, expected in (("source_feed_version", spec.feed_version), ("source_sha256", spec.sha256),
                            ("source_file_path", spec.source_path)):
        issue(~F.col(field).eqNullSafe(F.lit(expected)), f"{field.upper()}_MISMATCH")
    issue(F.col("bronze_loaded_at_utc").isNull(), "BRONZE_TIMESTAMP_INVALID")
    for field in columns:
        issue(F.col(field).rlike(r"[\p{Cc}]"), f"{field.upper()}_CONTROL_CHARACTER")
        if field != "shape_dist_traveled":
            issue(blank(field), f"{field.upper()}_MISSING")
    issue(~blank("shape_id") & F.col("shape_id").rlike(r"(?U)^\s|\s$"), "SHAPE_ID_EDGE_WHITESPACE")
    issue(F.col("_variant_min") != F.col("_variant_max"), "SHAPE_POINT_KEY_CONFLICT")
    issue(~blank("shape_pt_sequence") & (~F.col("shape_pt_sequence").rlike(r"^[0-9]+$")
          | F.col("_shape_pt_sequence").isNull() | (F.col("_shape_pt_sequence") < 0)),
          "SHAPE_PT_SEQUENCE_INVALID")
    for field, bound in (("shape_pt_lat", 90), ("shape_pt_lon", 180), ("shape_dist_traveled", None)):
        value = F.col("_" + field)
        invalid = ~F.col(field).rlike(NUMERIC) | value.isNull() | F.isnan(value)
        invalid = invalid | (~value.between(-bound, bound) if bound is not None else
                             ((value < 0) | (F.abs(value) == F.lit(float("inf")))))
        issue(~blank(field) & invalid, f"{field.upper()}_INVALID")

    # Detecto colisiones de la secuencia tipada, incluso entre representaciones 01 y 1.
    typed_key = Window.partitionBy("shape_id", "_shape_pt_sequence")
    selected = (selected.withColumn("_raw_sequence_min", F.min("shape_pt_sequence").over(typed_key))
                .withColumn("_raw_sequence_max", F.max("shape_pt_sequence").over(typed_key)))
    issue(F.col("_raw_sequence_min") != F.col("_raw_sequence_max"), "SHAPE_SEQUENCE_CAST_COLLISION")

    # Las copias válidas forman un solo punto de contexto y nunca multiplican el join.
    valid = F.size(F.filter(F.array(*errors), lambda code: code.isNotNull())) == 0
    points = selected.filter(valid).select(
        "shape_id", "_shape_pt_sequence", "_shape_pt_lat", "_shape_pt_lon", "_shape_dist_traveled",
    ).distinct()
    order = Window.partitionBy("shape_id").orderBy("_shape_pt_sequence")
    previous = order.rowsBetween(Window.unboundedPreceding, -1)
    positions = points.groupBy("shape_id").agg(
        F.countDistinct(F.struct("_shape_pt_lat", "_shape_pt_lon")).alias("_distinct_positions"))
    context = (points.withColumn("_previous_lat", F.lag("_shape_pt_lat").over(order))
               .withColumn("_previous_lon", F.lag("_shape_pt_lon").over(order))
               .withColumn("_previous_distance", F.last("_shape_dist_traveled", ignorenulls=True).over(previous))
               .join(positions, "shape_id", "left")
               .select(F.col("shape_id").alias("_context_id"),
                       F.col("_shape_pt_sequence").alias("_context_sequence"),
                       ((F.col("_previous_lat") == F.col("_shape_pt_lat"))
                        & (F.col("_previous_lon") == F.col("_shape_pt_lon"))).alias("_zero_segment"),
                       (F.col("_distinct_positions") < 2).alias("_degenerate_shape"),
                       (F.col("_shape_dist_traveled") <= F.col("_previous_distance"))
                        .alias("_distance_not_increasing")))
    selected = selected.join(context, (selected.shape_id == context._context_id)
                             & (selected._shape_pt_sequence == context._context_sequence), "left")
    issue(F.col("_distance_not_increasing"), "SHAPE_DISTANCE_NOT_INCREASING")
    issue(F.col("_zero_segment"), "CONSECUTIVE_POSITION_REPEATED", warning=True)
    issue(F.col("_degenerate_shape"), "SHAPE_WITH_FEWER_THAN_TWO_POSITIONS", warning=True)
    zero_pair = (F.col("_shape_pt_lat") == 0) & (F.col("_shape_pt_lon") == 0)
    issue(zero_pair, "COORDINATES_ZERO_PAIR", warning=True)
    expressions = [F.when(blank(field), F.lit(None)).otherwise(
        F.col(field) if target == "string" else F.col("_" + field)).cast(target).alias(field)
        for field, target in BUSINESS_TYPES.items()]
    return finish_validation(
        selected, columns, spec, KEYS, RULE_VERSION, errors, warnings, expressions,
        extra_metrics={"consecutive_position_repeated_rows": F.col("_zero_segment"),
                       "degenerate_shape_rows": F.col("_degenerate_shape"), "zero_coordinate_pair_rows": zero_pair},
    )
